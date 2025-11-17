terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for ElastiCache"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID for ElastiCache"
  type        = string
}

variable "node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.small"
}

variable "num_cache_nodes" {
  description = "Number of cache nodes (1 for non-clustered)"
  type        = number
  default     = 1
}

variable "engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.1"
}

variable "parameter_group_family" {
  description = "Redis parameter group family"
  type        = string
  default     = "redis7"
}

# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  name       = "bmo-learning-${var.environment}-redis-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name        = "bmo-learning-${var.environment}-redis-subnet-group"
    Environment = var.environment
  }
}

# ElastiCache Parameter Group
resource "aws_elasticache_parameter_group" "main" {
  name   = "bmo-learning-${var.environment}-redis7"
  family = var.parameter_group_family

  # Enable timeout for idle connections
  parameter {
    name  = "timeout"
    value = "300"
  }

  # Max memory policy
  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  tags = {
    Name        = "bmo-learning-${var.environment}-redis7"
    Environment = var.environment
  }
}

# ElastiCache Replication Group (Redis)
resource "aws_elasticache_replication_group" "main" {
  replication_group_id = "bmo-learning-${var.environment}"
  description          = "Redis cluster for BMO Learning Platform ${var.environment}"

  # Engine
  engine               = "redis"
  engine_version       = var.engine_version
  node_type            = var.node_type
  num_cache_clusters   = var.num_cache_nodes
  parameter_group_name = aws_elasticache_parameter_group.main.name
  port                 = 6379

  # Network
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [var.security_group_id]

  # High Availability (for production)
  automatic_failover_enabled = var.num_cache_nodes > 1
  multi_az_enabled           = var.num_cache_nodes > 1

  # Backup
  snapshot_retention_limit = var.environment == "prod" ? 7 : 1
  snapshot_window          = "03:00-05:00" # UTC
  maintenance_window       = "mon:05:00-mon:07:00"

  # Auto minor version upgrade
  auto_minor_version_upgrade = true

  # Encryption
  at_rest_encryption_enabled = true
  transit_encryption_enabled = false # Set to true if you need encryption in transit
  # auth_token                 = var.transit_encryption_enabled ? random_password.redis_auth.result : null

  # Logs
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_engine_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "engine-log"
  }

  # Notifications
  notification_topic_arn = var.environment == "prod" ? aws_sns_topic.redis_notifications[0].arn : null

  tags = {
    Name        = "bmo-learning-${var.environment}-redis"
    Environment = var.environment
  }
}

# CloudWatch Log Groups for Redis logs
resource "aws_cloudwatch_log_group" "redis_slow_log" {
  name              = "/aws/elasticache/bmo-learning-${var.environment}/redis-slow-log"
  retention_in_days = 7

  tags = {
    Name        = "bmo-learning-${var.environment}-redis-slow-log"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "redis_engine_log" {
  name              = "/aws/elasticache/bmo-learning-${var.environment}/redis-engine-log"
  retention_in_days = 7

  tags = {
    Name        = "bmo-learning-${var.environment}-redis-engine-log"
    Environment = var.environment
  }
}

# SNS Topic for Redis notifications (production only)
resource "aws_sns_topic" "redis_notifications" {
  count = var.environment == "prod" ? 1 : 0
  name  = "bmo-learning-${var.environment}-redis-notifications"

  tags = {
    Name        = "bmo-learning-${var.environment}-redis-notifications"
    Environment = var.environment
  }
}

# Outputs
output "redis_replication_group_id" {
  description = "ElastiCache replication group ID"
  value       = aws_elasticache_replication_group.main.id
}

output "redis_primary_endpoint" {
  description = "Primary endpoint for Redis"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "redis_reader_endpoint" {
  description = "Reader endpoint for Redis (if Multi-AZ)"
  value       = aws_elasticache_replication_group.main.reader_endpoint_address
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_replication_group.main.port
}

output "redis_url" {
  description = "Full Redis connection URL"
  value       = "redis://${aws_elasticache_replication_group.main.primary_endpoint_address}:${aws_elasticache_replication_group.main.port}/0"
}
