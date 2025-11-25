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
  description = "List of private subnet IDs for Aurora"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID for Aurora"
  type        = string
}

variable "database_name" {
  description = "Database name"
  type        = string
  default     = "bmo_learning_prod"
}

variable "master_username" {
  description = "Master username"
  type        = string
  default     = "postgres"
}

variable "backup_retention_period" {
  description = "Backup retention period in days"
  type        = number
  default     = 7
}

variable "min_capacity" {
  description = "Minimum Aurora Capacity Units (ACUs)"
  type        = number
  default     = 0.5
}

variable "max_capacity" {
  description = "Maximum Aurora Capacity Units (ACUs)"
  type        = number
  default     = 2
}

# Random password for database
resource "random_password" "db_password" {
  length  = 32
  special = true
  # Avoid characters that might cause issues in connection strings
  override_special = "!#$%^&*()-_=+[]{}:?"
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "bmo-learning-${var.environment}-aurora-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name        = "bmo-learning-${var.environment}-aurora-subnet-group"
    Environment = var.environment
  }
}

# DB Cluster Parameter Group for PostgreSQL 16 with pgvector
resource "aws_rds_cluster_parameter_group" "main" {
  name        = "bmo-learning-${var.environment}-aurora-pg16"
  family      = "aurora-postgresql16"
  description = "Aurora PostgreSQL 16 cluster parameter group with pgvector"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  parameter {
    name  = "log_statement"
    value = "all"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000" # Log queries taking longer than 1s
  }

  tags = {
    Name        = "bmo-learning-${var.environment}-aurora-pg16"
    Environment = var.environment
  }
}

# Aurora Serverless v2 Cluster
resource "aws_rds_cluster" "main" {
  cluster_identifier = "bmo-learning-${var.environment}-aurora"

  # Engine
  engine         = "aurora-postgresql"
  engine_mode    = "provisioned" # Serverless v2 uses "provisioned" mode
  engine_version = "16.3"        # PostgreSQL 16.3

  # Database
  database_name   = var.database_name
  master_username = var.master_username
  master_password = random_password.db_password.result
  port            = 5432

  # Network
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.security_group_id]

  # Serverless v2 Scaling Configuration
  serverlessv2_scaling_configuration {
    min_capacity = var.min_capacity
    max_capacity = var.max_capacity
  }

  # Backups
  backup_retention_period      = var.backup_retention_period
  preferred_backup_window      = "03:00-04:00" # UTC
  preferred_maintenance_window = "mon:04:00-mon:05:00"
  skip_final_snapshot          = var.environment != "prod"
  final_snapshot_identifier    = var.environment == "prod" ? "bmo-learning-${var.environment}-aurora-final-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  # Encryption
  storage_encrypted = true

  # Enhanced Monitoring
  enabled_cloudwatch_logs_exports = ["postgresql"]

  # Parameters
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.main.name

  # Protection
  deletion_protection   = var.environment == "prod"
  copy_tags_to_snapshot = true

  tags = {
    Name        = "bmo-learning-${var.environment}-aurora"
    Environment = var.environment
  }

  lifecycle {
    ignore_changes = [
      # Ignore password changes to prevent recreation
      master_password,
      # Ignore final snapshot identifier timestamp
      final_snapshot_identifier
    ]
  }
}

# Aurora Serverless v2 Instance (required for Serverless v2)
resource "aws_rds_cluster_instance" "main" {
  identifier         = "bmo-learning-${var.environment}-aurora-instance-1"
  cluster_identifier = aws_rds_cluster.main.id

  # Instance configuration for Serverless v2
  instance_class = "db.serverless"
  engine         = aws_rds_cluster.main.engine
  engine_version = aws_rds_cluster.main.engine_version

  # Performance Insights
  performance_insights_enabled          = true
  performance_insights_retention_period = 7

  # Monitoring
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn

  # Auto minor version upgrade
  auto_minor_version_upgrade = true

  tags = {
    Name        = "bmo-learning-${var.environment}-aurora-instance-1"
    Environment = var.environment
  }
}

# IAM Role for Enhanced Monitoring
resource "aws_iam_role" "rds_monitoring" {
  name = "bmo-learning-${var.environment}-aurora-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "bmo-learning-${var.environment}-aurora-monitoring"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# Outputs
output "cluster_id" {
  description = "Aurora cluster ID"
  value       = aws_rds_cluster.main.id
}

output "cluster_endpoint" {
  description = "Aurora cluster endpoint (writer)"
  value       = aws_rds_cluster.main.endpoint
}

output "cluster_reader_endpoint" {
  description = "Aurora cluster reader endpoint"
  value       = aws_rds_cluster.main.reader_endpoint
}

output "cluster_arn" {
  description = "Aurora cluster ARN"
  value       = aws_rds_cluster.main.arn
}

output "db_name" {
  description = "Database name"
  value       = aws_rds_cluster.main.database_name
}

output "db_username" {
  description = "Database master username"
  value       = aws_rds_cluster.main.master_username
  sensitive   = true
}

output "db_password" {
  description = "Database master password"
  value       = random_password.db_password.result
  sensitive   = true
}

output "db_port" {
  description = "Database port"
  value       = aws_rds_cluster.main.port
}

output "database_url" {
  description = "Full database connection URL"
  value       = "postgresql://${aws_rds_cluster.main.master_username}:${random_password.db_password.result}@${aws_rds_cluster.main.endpoint}:${aws_rds_cluster.main.port}/${aws_rds_cluster.main.database_name}"
  sensitive   = true
}
