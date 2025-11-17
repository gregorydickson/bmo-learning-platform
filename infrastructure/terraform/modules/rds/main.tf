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
  description = "List of private subnet IDs for RDS"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID for RDS"
  type        = string
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 100
}

variable "max_allocated_storage" {
  description = "Maximum storage for autoscaling in GB"
  type        = number
  default     = 500
}

variable "engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "16.3"
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

variable "multi_az" {
  description = "Enable Multi-AZ deployment"
  type        = bool
  default     = true
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
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
  name       = "bmo-learning-${var.environment}-db-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name        = "bmo-learning-${var.environment}-db-subnet-group"
    Environment = var.environment
  }
}

# DB Parameter Group for PostgreSQL with pgvector
resource "aws_db_parameter_group" "main" {
  name   = "bmo-learning-${var.environment}-pg16"
  family = "postgres16"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements,pgvector"
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
    Name        = "bmo-learning-${var.environment}-pg16"
    Environment = var.environment
  }
}

# RDS Instance
resource "aws_db_instance" "main" {
  identifier = "bmo-learning-${var.environment}"

  # Engine
  engine         = "postgres"
  engine_version = var.engine_version

  # Instance
  instance_class        = var.instance_class
  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  # Database
  db_name  = var.database_name
  username = var.master_username
  password = random_password.db_password.result
  port     = 5432

  # Network
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.security_group_id]
  publicly_accessible    = false
  multi_az               = var.multi_az

  # Backups
  backup_retention_period = var.backup_retention_period
  backup_window           = "03:00-04:00" # UTC
  maintenance_window      = "mon:04:00-mon:05:00"
  skip_final_snapshot     = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "bmo-learning-${var.environment}-final-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  # Performance Insights
  performance_insights_enabled = true
  performance_insights_retention_period = 7

  # Enhanced Monitoring
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  monitoring_interval             = 60
  monitoring_role_arn             = aws_iam_role.rds_monitoring.arn

  # Parameters
  parameter_group_name = aws_db_parameter_group.main.name

  # Protection
  deletion_protection = var.deletion_protection
  copy_tags_to_snapshot = true

  # Auto minor version upgrade
  auto_minor_version_upgrade = true

  tags = {
    Name        = "bmo-learning-${var.environment}"
    Environment = var.environment
  }

  lifecycle {
    ignore_changes = [
      # Ignore password changes to prevent recreation
      password,
      # Ignore final snapshot identifier timestamp
      final_snapshot_identifier
    ]
  }
}

# IAM Role for Enhanced Monitoring
resource "aws_iam_role" "rds_monitoring" {
  name = "bmo-learning-${var.environment}-rds-monitoring"

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
    Name        = "bmo-learning-${var.environment}-rds-monitoring"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# Outputs
output "db_instance_id" {
  description = "RDS instance ID"
  value       = aws_db_instance.main.id
}

output "db_instance_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
}

output "db_instance_address" {
  description = "RDS instance address"
  value       = aws_db_instance.main.address
}

output "db_instance_arn" {
  description = "RDS instance ARN"
  value       = aws_db_instance.main.arn
}

output "db_name" {
  description = "Database name"
  value       = aws_db_instance.main.db_name
}

output "db_username" {
  description = "Database master username"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "db_password" {
  description = "Database master password"
  value       = random_password.db_password.result
  sensitive   = true
}

output "db_port" {
  description = "Database port"
  value       = aws_db_instance.main.port
}

output "database_url" {
  description = "Full database connection URL"
  value       = "postgresql://${aws_db_instance.main.username}:${random_password.db_password.result}@${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}"
  sensitive   = true
}
