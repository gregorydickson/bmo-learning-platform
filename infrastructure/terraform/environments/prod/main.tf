terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket         = "bmo-learning-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-2"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "BMO-Learning"
      Environment = "production"
      ManagedBy   = "Terraform"
    }
  }
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-east-2a", "us-east-2b", "us-east-2c"]
}

variable "ecs_cluster_name" {
  description = "ECS cluster name"
  type        = string
  default     = "bmo-learning-prod"
}

variable "ai_service_cpu" {
  description = "CPU units for AI service"
  type        = number
  default     = 1024
}

variable "ai_service_memory" {
  description = "Memory (MB) for AI service"
  type        = number
  default     = 2048
}

variable "rails_api_cpu" {
  description = "CPU units for Rails API"
  type        = number
  default     = 512
}

variable "rails_api_memory" {
  description = "Memory (MB) for Rails API"
  type        = number
  default     = 1024
}

# Aurora Serverless v2 uses ACU (Aurora Capacity Units) instead of instance classes
# Scaling configuration is set directly in the aurora module call

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.small"
}

variable "ai_service_image" {
  description = "Docker image for AI service (e.g., <account-id>.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/ai-service:latest)"
  type        = string
  default     = "PLACEHOLDER_AI_SERVICE_IMAGE" # Must be updated after ECR push
}

variable "rails_api_image" {
  description = "Docker image for Rails API (e.g., <account-id>.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/rails-api:latest)"
  type        = string
  default     = "PLACEHOLDER_RAILS_API_IMAGE" # Must be updated after ECR push
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for HTTPS (optional)"
  type        = string
  default     = null
}

variable "ai_service_api_key" {
  description = "API Key for AI Service"
  type        = string
  sensitive   = true
  default     = "change_me_in_prod"
}

# VPC Module
module "vpc" {
  source = "../../modules/vpc"

  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
}

# Security Groups Module
module "security_groups" {
  source = "../../modules/security_groups"

  environment = var.environment
  vpc_id      = module.vpc.vpc_id
  vpc_cidr    = module.vpc.vpc_cidr
}

# IAM Roles Module
module "iam" {
  source = "../../modules/iam"

  environment = var.environment
  # Pass secret ARNs after they're created
  secrets_arns = module.secrets.all_secret_arns

  depends_on = [module.secrets]
}

# Aurora Serverless v2 Module (cost-optimized replacement for RDS)
module "aurora" {
  source = "../../modules/aurora_serverless"

  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  security_group_id  = module.security_groups.rds_security_group_id
  min_capacity       = 0.5 # Minimum ACU (scales down when idle)
  max_capacity       = 2   # Maximum ACU (scales up under load)
}

# ElastiCache Redis Module
module "elasticache" {
  source = "../../modules/elasticache"

  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  security_group_id  = module.security_groups.redis_security_group_id
  node_type          = var.redis_node_type
  num_cache_nodes    = 1 # Set to 2+ for Multi-AZ
}

# Secrets Manager Module
module "secrets" {
  source = "../../modules/secrets"

  environment  = var.environment
  database_url = module.aurora.database_url
  redis_url    = module.elasticache.redis_url
  db_password  = module.aurora.db_password

  depends_on = [module.aurora, module.elasticache]
}

# ECR Module
module "ecr" {
  source = "../../modules/ecr"

  environment = var.environment
}

# S3 Module
module "s3" {
  source = "../../modules/s3"

  environment = var.environment
}

# Application Load Balancer Module
module "alb" {
  source = "../../modules/alb"

  environment       = var.environment
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  security_group_id = module.security_groups.alb_security_group_id
  certificate_arn   = var.acm_certificate_arn
}

# ECS Cluster Module
module "ecs" {
  source = "../../modules/ecs"

  cluster_name       = var.ecs_cluster_name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
}

# ECS Services Module
module "ecs_services" {
  source = "../../modules/ecs_services"

  environment             = var.environment
  cluster_id              = module.ecs.cluster_id
  cluster_name            = module.ecs.cluster_name
  vpc_id                  = module.vpc.vpc_id
  public_subnet_ids       = module.vpc.public_subnet_ids # Changed from private for cost optimization
  security_group_id       = module.security_groups.ecs_tasks_security_group_id
  task_execution_role_arn = module.iam.ecs_task_execution_role_arn
  task_role_arn           = module.iam.ecs_task_role_arn

  # Docker images (must be updated after pushing to ECR)
  ai_service_image = var.ai_service_image
  rails_api_image  = var.rails_api_image

  # Load balancer target groups
  ai_service_target_group_arn = module.alb.ai_service_target_group_arn
  rails_api_target_group_arn  = module.alb.rails_api_target_group_arn

  # Secrets
  secret_arns = {
    anthropic_api_key     = module.secrets.anthropic_api_key_arn
    openai_api_key        = module.secrets.openai_api_key_arn
    database_url          = module.secrets.database_url_arn
    redis_url             = module.secrets.redis_url_arn
    rails_secret_key_base = module.secrets.rails_secret_key_base_arn
    twilio_account_sid    = module.secrets.twilio_account_sid_arn
    twilio_auth_token     = module.secrets.twilio_auth_token_arn
    slack_bot_token       = module.secrets.slack_bot_token_arn
  }

  # Resource sizing
  ai_service_cpu    = var.ai_service_cpu
  ai_service_memory = var.ai_service_memory
  rails_api_cpu     = var.rails_api_cpu
  rails_api_memory  = var.rails_api_memory

  # Service Communication
  ai_service_url     = "http://${module.alb.alb_dns_name}"
  ai_service_api_key = var.ai_service_api_key

  depends_on = [module.alb, module.secrets]
}

# Outputs
output "vpc_id" {
  description = "Production VPC ID"
  value       = module.vpc.vpc_id
}

output "ecs_cluster_name" {
  description = "Production ECS cluster name"
  value       = module.ecs.cluster_name
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = module.alb.alb_dns_name
}

output "aurora_endpoint" {
  description = "Aurora cluster endpoint (writer)"
  value       = module.aurora.cluster_endpoint
}

output "aurora_reader_endpoint" {
  description = "Aurora cluster reader endpoint"
  value       = module.aurora.cluster_reader_endpoint
}

output "redis_endpoint" {
  description = "Redis primary endpoint"
  value       = module.elasticache.redis_primary_endpoint
}

output "ecr_ai_service_repository_url" {
  description = "ECR repository URL for AI service"
  value       = module.ecr.ai_service_repository_url
}

output "ecr_rails_api_repository_url" {
  description = "ECR repository URL for Rails API"
  value       = module.ecr.rails_api_repository_url
}

output "documents_bucket" {
  description = "S3 bucket for documents"
  value       = module.s3.documents_bucket_id
}

output "backups_bucket" {
  description = "S3 bucket for backups"
  value       = module.s3.backups_bucket_id
}

# Sensitive outputs (for automation only)
output "database_url" {
  description = "Full database connection URL"
  value       = module.aurora.database_url
  sensitive   = true
}

output "redis_url" {
  description = "Full Redis connection URL"
  value       = module.elasticache.redis_url
  sensitive   = true
}
