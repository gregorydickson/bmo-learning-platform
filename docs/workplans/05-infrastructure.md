# Phase 5: Infrastructure & Deployment

**Duration**: 8-10 days
**Goal**: Production-ready AWS infrastructure with Terraform, multi-environment setup, and comprehensive monitoring

## Overview
This phase implements infrastructure as code for deploying the learning platform to AWS. We prioritize:
1. **Infrastructure as Code** (Terraform modules for all resources)
2. **Multi-Environment** (dev, staging, production with environment parity)
3. **Scalability** (Auto-scaling, load balancing, container orchestration)
4. **Observability** (CloudWatch, distributed tracing, alerting)
5. **Security** (VPC isolation, secrets management, IAM least privilege)
6. **Cost Optimization** (Right-sized instances, spot instances where appropriate)

## Prerequisites
- [ ] Phases 1-4 complete (all services containerized and tested)
- [ ] AWS account with admin access
- [ ] Terraform 1.6+ installed locally
- [ ] AWS CLI configured
- [ ] Domain name registered (optional, for production)
- [ ] Understanding of AWS services (VPC, ECS, RDS, S3)

## 1. Terraform Project Structure

### 1.1 Create Infrastructure Directory
- [ ] Create Terraform project structure
  ```bash
  mkdir -p infrastructure/{modules,environments}/{networking,compute,storage,messaging,monitoring,security}
  cd infrastructure
  ```

- [ ] Directory structure
  ```
  infrastructure/
  ├── modules/
  │   ├── networking/        # VPC, subnets, security groups
  │   ├── compute/           # ECS clusters, task definitions
  │   ├── storage/           # RDS, S3, ElastiCache
  │   ├── messaging/         # SQS, SNS
  │   ├── monitoring/        # CloudWatch, alarms
  │   └── security/          # IAM, Secrets Manager
  ├── environments/
  │   ├── dev/
  │   ├── staging/
  │   └── production/
  ├── backend.tf             # S3 backend for state
  └── versions.tf            # Provider versions
  ```

### 1.2 Terraform Backend Configuration
- [ ] Create `infrastructure/backend.tf`
  ```hcl
  terraform {
    backend "s3" {
      bucket         = "bmo-learning-terraform-state"
      key            = "terraform.tfstate"
      region         = "us-east-1"
      encrypt        = true
      dynamodb_table = "terraform-state-lock"
    }
  }
  ```

- [ ] Create S3 bucket and DynamoDB table for state locking
  ```bash
  aws s3 mb s3://bmo-learning-terraform-state --region us-east-1
  aws s3api put-bucket-versioning \
    --bucket bmo-learning-terraform-state \
    --versioning-configuration Status=Enabled

  aws dynamodb create-table \
    --table-name terraform-state-lock \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
  ```

### 1.3 Provider Configuration
- [ ] Create `infrastructure/versions.tf`
  ```hcl
  terraform {
    required_version = ">= 1.9.0"

    required_providers {
      aws = {
        source  = "hashicorp/aws"
        version = "~> 5.0"
      }
      random = {
        source  = "hashicorp/random"
        version = "~> 3.5"
      }
    }
  }

  provider "aws" {
    region = var.aws_region

    default_tags {
      tags = {
        Project     = "BMO Learning Platform"
        Environment = var.environment
        ManagedBy   = "Terraform"
      }
    }
  }
  ```

**Validation**: `terraform init` succeeds

## 2. Networking Module

### 2.1 VPC and Subnets
- [ ] Create `infrastructure/modules/networking/main.tf`
  ```hcl
  # VPC
  resource "aws_vpc" "main" {
    cidr_block           = var.vpc_cidr
    enable_dns_hostnames = true
    enable_dns_support   = true

    tags = {
      Name = "${var.environment}-bmo-learning-vpc"
    }
  }

  # Internet Gateway
  resource "aws_internet_gateway" "main" {
    vpc_id = aws_vpc.main.id

    tags = {
      Name = "${var.environment}-igw"
    }
  }

  # Public Subnets (for ALB)
  resource "aws_subnet" "public" {
    count = length(var.availability_zones)

    vpc_id                  = aws_vpc.main.id
    cidr_block              = cidrsubnet(var.vpc_cidr, 4, count.index)
    availability_zone       = var.availability_zones[count.index]
    map_public_ip_on_launch = true

    tags = {
      Name = "${var.environment}-public-subnet-${count.index + 1}"
      Type = "public"
    }
  }

  # Private Subnets (for ECS tasks, RDS)
  resource "aws_subnet" "private" {
    count = length(var.availability_zones)

    vpc_id            = aws_vpc.main.id
    cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + length(var.availability_zones))
    availability_zone = var.availability_zones[count.index]

    tags = {
      Name = "${var.environment}-private-subnet-${count.index + 1}"
      Type = "private"
    }
  }

  # NAT Gateway (for private subnet internet access)
  resource "aws_eip" "nat" {
    count  = var.enable_nat_gateway ? length(var.availability_zones) : 0
    domain = "vpc"

    tags = {
      Name = "${var.environment}-nat-eip-${count.index + 1}"
    }
  }

  resource "aws_nat_gateway" "main" {
    count = var.enable_nat_gateway ? length(var.availability_zones) : 0

    allocation_id = aws_eip.nat[count.index].id
    subnet_id     = aws_subnet.public[count.index].id

    tags = {
      Name = "${var.environment}-nat-gateway-${count.index + 1}"
    }
  }

  # Route Tables
  resource "aws_route_table" "public" {
    vpc_id = aws_vpc.main.id

    route {
      cidr_block = "0.0.0.0/0"
      gateway_id = aws_internet_gateway.main.id
    }

    tags = {
      Name = "${var.environment}-public-rt"
    }
  }

  resource "aws_route_table" "private" {
    count = length(var.availability_zones)

    vpc_id = aws_vpc.main.id

    dynamic "route" {
      for_each = var.enable_nat_gateway ? [1] : []
      content {
        cidr_block     = "0.0.0.0/0"
        nat_gateway_id = aws_nat_gateway.main[count.index].id
      }
    }

    tags = {
      Name = "${var.environment}-private-rt-${count.index + 1}"
    }
  }

  # Route Table Associations
  resource "aws_route_table_association" "public" {
    count = length(var.availability_zones)

    subnet_id      = aws_subnet.public[count.index].id
    route_table_id = aws_route_table.public.id
  }

  resource "aws_route_table_association" "private" {
    count = length(var.availability_zones)

    subnet_id      = aws_subnet.private[count.index].id
    route_table_id = aws_route_table.private[count.index].id
  }
  ```

- [ ] Create `infrastructure/modules/networking/variables.tf`
  ```hcl
  variable "environment" {
    description = "Environment name"
    type        = string
  }

  variable "vpc_cidr" {
    description = "CIDR block for VPC"
    type        = string
    default     = "10.0.0.0/16"
  }

  variable "availability_zones" {
    description = "List of availability zones"
    type        = list(string)
  }

  variable "enable_nat_gateway" {
    description = "Enable NAT gateway for private subnets"
    type        = bool
    default     = true
  }
  ```

- [ ] Create `infrastructure/modules/networking/outputs.tf`
  ```hcl
  output "vpc_id" {
    value = aws_vpc.main.id
  }

  output "public_subnet_ids" {
    value = aws_subnet.public[*].id
  }

  output "private_subnet_ids" {
    value = aws_subnet.private[*].id
  }

  output "vpc_cidr" {
    value = aws_vpc.main.cidr_block
  }
  ```

### 2.2 Security Groups
- [ ] Create `infrastructure/modules/networking/security_groups.tf`
  ```hcl
  # ALB Security Group
  resource "aws_security_group" "alb" {
    name_prefix = "${var.environment}-alb-sg"
    vpc_id      = aws_vpc.main.id

    ingress {
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }

    ingress {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }

    egress {
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_blocks = ["0.0.0.0/0"]
    }

    tags = {
      Name = "${var.environment}-alb-sg"
    }
  }

  # ECS Tasks Security Group
  resource "aws_security_group" "ecs_tasks" {
    name_prefix = "${var.environment}-ecs-tasks-sg"
    vpc_id      = aws_vpc.main.id

    ingress {
      from_port       = 0
      to_port         = 65535
      protocol        = "tcp"
      security_groups = [aws_security_group.alb.id]
    }

    egress {
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_blocks = ["0.0.0.0/0"]
    }

    tags = {
      Name = "${var.environment}-ecs-tasks-sg"
    }
  }

  # RDS Security Group
  resource "aws_security_group" "rds" {
    name_prefix = "${var.environment}-rds-sg"
    vpc_id      = aws_vpc.main.id

    ingress {
      from_port       = 5432
      to_port         = 5432
      protocol        = "tcp"
      security_groups = [aws_security_group.ecs_tasks.id]
    }

    tags = {
      Name = "${var.environment}-rds-sg"
    }
  }

  # ElastiCache Security Group
  resource "aws_security_group" "elasticache" {
    name_prefix = "${var.environment}-elasticache-sg"
    vpc_id      = aws_vpc.main.id

    ingress {
      from_port       = 6379
      to_port         = 6379
      protocol        = "tcp"
      security_groups = [aws_security_group.ecs_tasks.id]
    }

    tags = {
      Name = "${var.environment}-elasticache-sg"
    }
  }
  ```

**Validation**: `terraform plan` shows networking resources

## 3. Storage Module

### 3.1 RDS PostgreSQL
- [ ] Create `infrastructure/modules/storage/rds.tf`
  ```hcl
  # DB Subnet Group
  resource "aws_db_subnet_group" "main" {
    name       = "${var.environment}-db-subnet-group"
    subnet_ids = var.private_subnet_ids

    tags = {
      Name = "${var.environment}-db-subnet-group"
    }
  }

  # RDS Parameter Group (pgvector support)
  resource "aws_db_parameter_group" "postgresql" {
    name   = "${var.environment}-postgresql-params"
    family = "postgres16"

    parameter {
      name  = "shared_preload_libraries"
      value = "pg_stat_statements,vector"
      apply_method = "pending-reboot"
    }

    parameter {
      name  = "max_connections"
      value = var.max_connections
    }

    tags = {
      Name = "${var.environment}-postgresql-params"
    }
  }

  # RDS Instance
  resource "aws_db_instance" "postgresql" {
    identifier     = "${var.environment}-bmo-learning-db"
    engine         = "postgres"
    engine_version = "16.6"
    instance_class = var.db_instance_class

    allocated_storage     = var.db_allocated_storage
    max_allocated_storage = var.db_max_allocated_storage
    storage_type          = "gp3"
    storage_encrypted     = true

    db_name  = "bmo_learning_${var.environment}"
    username = "bmo_admin"
    password = random_password.db_password.result

    db_subnet_group_name   = aws_db_subnet_group.main.name
    vpc_security_group_ids = [var.rds_security_group_id]
    parameter_group_name   = aws_db_parameter_group.postgresql.name

    backup_retention_period = var.backup_retention_period
    backup_window           = "03:00-04:00"
    maintenance_window      = "sun:04:00-sun:05:00"

    multi_az               = var.multi_az
    skip_final_snapshot    = var.environment != "production"
    final_snapshot_identifier = var.environment == "production" ? "${var.environment}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

    enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

    tags = {
      Name = "${var.environment}-postgresql"
    }
  }

  # Random password for DB
  resource "random_password" "db_password" {
    length  = 32
    special = true
  }

  # Store password in Secrets Manager
  resource "aws_secretsmanager_secret" "db_password" {
    name = "${var.environment}/bmo-learning/db-password"

    recovery_window_in_days = var.environment == "production" ? 30 : 0
  }

  resource "aws_secretsmanager_secret_version" "db_password" {
    secret_id     = aws_secretsmanager_secret.db_password.id
    secret_string = jsonencode({
      username = aws_db_instance.postgresql.username
      password = random_password.db_password.result
      host     = aws_db_instance.postgresql.address
      port     = aws_db_instance.postgresql.port
      dbname   = aws_db_instance.postgresql.db_name
    })
  }
  ```

### 3.2 ElastiCache Redis
- [ ] Create `infrastructure/modules/storage/elasticache.tf`
  ```hcl
  # ElastiCache Subnet Group
  resource "aws_elasticache_subnet_group" "main" {
    name       = "${var.environment}-redis-subnet-group"
    subnet_ids = var.private_subnet_ids
  }

  # ElastiCache Replication Group
  resource "aws_elasticache_replication_group" "redis" {
    replication_group_id       = "${var.environment}-redis-cluster"
    replication_group_description = "Redis cluster for BMO Learning Platform"

    engine               = "redis"
    engine_version       = "7.0"
    node_type            = var.redis_node_type
    number_cache_clusters = var.redis_num_cache_nodes

    port                       = 6379
    parameter_group_name       = "default.redis7"
    subnet_group_name          = aws_elasticache_subnet_group.main.name
    security_group_ids         = [var.elasticache_security_group_id]

    automatic_failover_enabled = var.redis_num_cache_nodes > 1
    multi_az_enabled           = var.redis_num_cache_nodes > 1

    at_rest_encryption_enabled = true
    transit_encryption_enabled = true
    auth_token                 = random_password.redis_auth_token.result

    snapshot_retention_limit = var.environment == "production" ? 7 : 1
    snapshot_window          = "03:00-05:00"

    tags = {
      Name = "${var.environment}-redis"
    }
  }

  # Random auth token for Redis
  resource "random_password" "redis_auth_token" {
    length  = 32
    special = false
  }

  # Store Redis auth token in Secrets Manager
  resource "aws_secretsmanager_secret" "redis_auth_token" {
    name = "${var.environment}/bmo-learning/redis-auth-token"

    recovery_window_in_days = var.environment == "production" ? 30 : 0
  }

  resource "aws_secretsmanager_secret_version" "redis_auth_token" {
    secret_id     = aws_secretsmanager_secret.redis_auth_token.id
    secret_string = jsonencode({
      auth_token = random_password.redis_auth_token.result
      endpoint   = aws_elasticache_replication_group.redis.primary_endpoint_address
      port       = aws_elasticache_replication_group.redis.port
    })
  }
  ```

### 3.3 S3 Buckets
- [ ] Create `infrastructure/modules/storage/s3.tf`
  ```hcl
  # Document Storage Bucket
  resource "aws_s3_bucket" "documents" {
    bucket = "${var.environment}-bmo-learning-documents"

    tags = {
      Name = "${var.environment}-documents"
    }
  }

  resource "aws_s3_bucket_versioning" "documents" {
    bucket = aws_s3_bucket.documents.id

    versioning_configuration {
      status = "Enabled"
    }
  }

  resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
    bucket = aws_s3_bucket.documents.id

    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  resource "aws_s3_bucket_public_access_block" "documents" {
    bucket = aws_s3_bucket.documents.id

    block_public_acls       = true
    block_public_policy     = true
    ignore_public_acls      = true
    restrict_public_buckets = true
  }

  # Lifecycle policy for cost optimization
  resource "aws_s3_bucket_lifecycle_configuration" "documents" {
    bucket = aws_s3_bucket.documents.id

    rule {
      id     = "transition-to-ia"
      status = "Enabled"

      transition {
        days          = 90
        storage_class = "STANDARD_IA"
      }

      transition {
        days          = 180
        storage_class = "GLACIER"
      }
    }
  }

  # ML Models Bucket
  resource "aws_s3_bucket" "ml_models" {
    bucket = "${var.environment}-bmo-learning-ml-models"

    tags = {
      Name = "${var.environment}-ml-models"
    }
  }

  resource "aws_s3_bucket_versioning" "ml_models" {
    bucket = aws_s3_bucket.ml_models.id

    versioning_configuration {
      status = "Enabled"
    }
  }
  ```

**Validation**: `terraform plan` shows storage resources

## 4. Compute Module (ECS Fargate)

### 4.1 ECS Cluster
- [ ] Create `infrastructure/modules/compute/ecs_cluster.tf`
  ```hcl
  # ECS Cluster
  resource "aws_ecs_cluster" "main" {
    name = "${var.environment}-bmo-learning-cluster"

    setting {
      name  = "containerInsights"
      value = "enabled"
    }

    tags = {
      Name = "${var.environment}-ecs-cluster"
    }
  }

  # CloudWatch Log Group
  resource "aws_cloudwatch_log_group" "ecs" {
    name              = "/ecs/${var.environment}-bmo-learning"
    retention_in_days = var.log_retention_days

    tags = {
      Name = "${var.environment}-ecs-logs"
    }
  }
  ```

### 4.2 Application Load Balancer
- [ ] Create `infrastructure/modules/compute/alb.tf`
  ```hcl
  # Application Load Balancer
  resource "aws_lb" "main" {
    name               = "${var.environment}-bmo-learning-alb"
    internal           = false
    load_balancer_type = "application"
    security_groups    = [var.alb_security_group_id]
    subnets            = var.public_subnet_ids

    enable_deletion_protection = var.environment == "production"

    tags = {
      Name = "${var.environment}-alb"
    }
  }

  # Target Group - Rails API
  resource "aws_lb_target_group" "rails_api" {
    name        = "${var.environment}-rails-api-tg"
    port        = 3001
    protocol    = "HTTP"
    vpc_id      = var.vpc_id
    target_type = "ip"

    health_check {
      enabled             = true
      path                = "/health"
      healthy_threshold   = 2
      unhealthy_threshold = 10
      timeout             = 30
      interval            = 60
      matcher             = "200"
    }

    deregistration_delay = 30
  }

  # Target Group - Python AI Service
  resource "aws_lb_target_group" "ai_service" {
    name        = "${var.environment}-ai-service-tg"
    port        = 8000
    protocol    = "HTTP"
    vpc_id      = var.vpc_id
    target_type = "ip"

    health_check {
      enabled             = true
      path                = "/health"
      healthy_threshold   = 2
      unhealthy_threshold = 10
      timeout             = 30
      interval            = 60
      matcher             = "200"
    }

    deregistration_delay = 30
  }

  # ALB Listener (HTTP)
  resource "aws_lb_listener" "http" {
    load_balancer_arn = aws_lb.main.arn
    port              = "80"
    protocol          = "HTTP"

    default_action {
      type = "redirect"

      redirect {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }

  # ALB Listener (HTTPS) - requires ACM certificate
  resource "aws_lb_listener" "https" {
    count = var.certificate_arn != "" ? 1 : 0

    load_balancer_arn = aws_lb.main.arn
    port              = "443"
    protocol          = "HTTPS"
    ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
    certificate_arn   = var.certificate_arn

    default_action {
      type             = "forward"
      target_group_arn = aws_lb_target_group.rails_api.arn
    }
  }

  # Listener Rules
  resource "aws_lb_listener_rule" "ai_service" {
    count = var.certificate_arn != "" ? 1 : 0

    listener_arn = aws_lb_listener.https[0].arn
    priority     = 100

    action {
      type             = "forward"
      target_group_arn = aws_lb_target_group.ai_service.arn
    }

    condition {
      path_pattern {
        values = ["/api/ai/*"]
      }
    }
  }
  ```

### 4.3 ECS Task Definitions
- [ ] Create `infrastructure/modules/compute/task_definitions.tf`
  ```hcl
  # IAM Role for ECS Task Execution
  resource "aws_iam_role" "ecs_task_execution" {
    name = "${var.environment}-ecs-task-execution-role"

    assume_role_policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Action = "sts:AssumeRole"
          Effect = "Allow"
          Principal = {
            Service = "ecs-tasks.amazonaws.com"
          }
        }
      ]
    })
  }

  resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
    role       = aws_iam_role.ecs_task_execution.name
    policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
  }

  # Additional policy for Secrets Manager access
  resource "aws_iam_role_policy" "secrets_access" {
    name = "${var.environment}-secrets-access"
    role = aws_iam_role.ecs_task_execution.id

    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Effect = "Allow"
          Action = [
            "secretsmanager:GetSecretValue"
          ]
          Resource = [
            var.db_secret_arn,
            var.redis_secret_arn
          ]
        }
      ]
    })
  }

  # Task Definition - Rails API
  resource "aws_ecs_task_definition" "rails_api" {
    family                   = "${var.environment}-rails-api"
    network_mode             = "awsvpc"
    requires_compatibilities = ["FARGATE"]
    cpu                      = var.rails_api_cpu
    memory                   = var.rails_api_memory
    execution_role_arn       = aws_iam_role.ecs_task_execution.arn
    task_role_arn            = aws_iam_role.ecs_task_execution.arn

    container_definitions = jsonencode([
      {
        name      = "rails-api"
        image     = "${var.ecr_repository_url}/rails-api:${var.image_tag}"
        essential = true

        portMappings = [
          {
            containerPort = 3001
            protocol      = "tcp"
          }
        ]

        environment = [
          {
            name  = "RAILS_ENV"
            value = var.environment
          },
          {
            name  = "RAILS_LOG_TO_STDOUT"
            value = "true"
          }
        ]

        secrets = [
          {
            name      = "DB_USERNAME"
            valueFrom = "${var.db_secret_arn}:username::"
          },
          {
            name      = "DB_PASSWORD"
            valueFrom = "${var.db_secret_arn}:password::"
          },
          {
            name      = "DB_HOST"
            valueFrom = "${var.db_secret_arn}:host::"
          },
          {
            name      = "DB_NAME"
            valueFrom = "${var.db_secret_arn}:dbname::"
          },
          {
            name      = "REDIS_AUTH_TOKEN"
            valueFrom = "${var.redis_secret_arn}:auth_token::"
          },
          {
            name      = "REDIS_ENDPOINT"
            valueFrom = "${var.redis_secret_arn}:endpoint::"
          }
        ]

        environment = [
          {
            name  = "DATABASE_URL"
            value = "postgresql://$(DB_USERNAME):$(DB_PASSWORD)@$(DB_HOST):5432/$(DB_NAME)"
          },
          {
            name  = "REDIS_URL"
            value = "rediss://:$(REDIS_AUTH_TOKEN)@$(REDIS_ENDPOINT):6379"
          }
        ]

        logConfiguration = {
          logDriver = "awslogs"
          options = {
            "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
            "awslogs-region"        = var.aws_region
            "awslogs-stream-prefix" = "rails-api"
          }
        }

        healthCheck = {
          command     = ["CMD-SHELL", "curl -f http://localhost:3001/health || exit 1"]
          interval    = 30
          timeout     = 5
          retries     = 3
          startPeriod = 60
        }
      }
    ])
  }

  # Task Definition - Python AI Service
  resource "aws_ecs_task_definition" "ai_service" {
    family                   = "${var.environment}-ai-service"
    network_mode             = "awsvpc"
    requires_compatibilities = ["FARGATE"]
    cpu                      = var.ai_service_cpu
    memory                   = var.ai_service_memory
    execution_role_arn       = aws_iam_role.ecs_task_execution.arn
    task_role_arn            = aws_iam_role.ecs_task_execution.arn

    container_definitions = jsonencode([
      {
        name      = "ai-service"
        image     = "${var.ecr_repository_url}/ai-service:${var.image_tag}"
        essential = true

        portMappings = [
          {
            containerPort = 8000
            protocol      = "tcp"
          }
        ]

        environment = [
          {
            name  = "ENVIRONMENT"
            value = var.environment
          }
        ]

        secrets = [
          {
            name      = "OPENAI_API_KEY"
            valueFrom = "${var.openai_secret_arn}:api_key::"
          },
          {
            name      = "DB_USERNAME"
            valueFrom = "${var.db_secret_arn}:username::"
          },
          {
            name      = "DB_PASSWORD"
            valueFrom = "${var.db_secret_arn}:password::"
          },
          {
            name      = "DB_HOST"
            valueFrom = "${var.db_secret_arn}:host::"
          },
          {
            name      = "DB_NAME"
            valueFrom = "${var.db_secret_arn}:dbname::"
          }
        ]

        environment = [
          {
            name  = "DATABASE_URL"
            value = "postgresql://$(DB_USERNAME):$(DB_PASSWORD)@$(DB_HOST):5432/$(DB_NAME)"
          }
        ]

        logConfiguration = {
          logDriver = "awslogs"
          options = {
            "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
            "awslogs-region"        = var.aws_region
            "awslogs-stream-prefix" = "ai-service"
          }
        }

        healthCheck = {
          command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
          interval    = 30
          timeout     = 5
          retries     = 3
          startPeriod = 60
        }
      }
    ])
  }
  ```

### 4.4 ECS Services with Auto-Scaling
- [ ] Create `infrastructure/modules/compute/ecs_services.tf`
  ```hcl
  # ECS Service - Rails API
  resource "aws_ecs_service" "rails_api" {
    name            = "${var.environment}-rails-api"
    cluster         = aws_ecs_cluster.main.id
    task_definition = aws_ecs_task_definition.rails_api.arn
    desired_count   = var.rails_api_desired_count
    launch_type     = "FARGATE"

    network_configuration {
      subnets          = var.private_subnet_ids
      security_groups  = [var.ecs_security_group_id]
      assign_public_ip = false
    }

    load_balancer {
      target_group_arn = aws_lb_target_group.rails_api.arn
      container_name   = "rails-api"
      container_port   = 3001
    }

    depends_on = [aws_lb_listener.http]

    deployment_configuration {
      maximum_percent         = 200
      minimum_healthy_percent = 100
    }
  }

  # Auto Scaling Target - Rails API
  resource "aws_appautoscaling_target" "rails_api" {
    max_capacity       = var.rails_api_max_count
    min_capacity       = var.rails_api_min_count
    resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.rails_api.name}"
    scalable_dimension = "ecs:service:DesiredCount"
    service_namespace  = "ecs"
  }

  # Auto Scaling Policy - CPU Based
  resource "aws_appautoscaling_policy" "rails_api_cpu" {
    name               = "${var.environment}-rails-api-cpu-scaling"
    policy_type        = "TargetTrackingScaling"
    resource_id        = aws_appautoscaling_target.rails_api.resource_id
    scalable_dimension = aws_appautoscaling_target.rails_api.scalable_dimension
    service_namespace  = aws_appautoscaling_target.rails_api.service_namespace

    target_tracking_scaling_policy_configuration {
      target_value       = 70.0
      scale_in_cooldown  = 300
      scale_out_cooldown = 60

      predefined_metric_specification {
        predefined_metric_type = "ECSServiceAverageCPUUtilization"
      }
    }
  }

  # Similar configuration for AI Service
  resource "aws_ecs_service" "ai_service" {
    name            = "${var.environment}-ai-service"
    cluster         = aws_ecs_cluster.main.id
    task_definition = aws_ecs_task_definition.ai_service.arn
    desired_count   = var.ai_service_desired_count
    launch_type     = "FARGATE"

    network_configuration {
      subnets          = var.private_subnet_ids
      security_groups  = [var.ecs_security_group_id]
      assign_public_ip = false
    }

    load_balancer {
      target_group_arn = aws_lb_target_group.ai_service.arn
      container_name   = "ai-service"
      container_port   = 8000
    }
  }
  ```

**Validation**: `terraform plan` shows compute resources

## 5. Monitoring Module

### 5.1 CloudWatch Alarms
- [ ] Create `infrastructure/modules/monitoring/alarms.tf`
  ```hcl
  # SNS Topic for Alarms
  resource "aws_sns_topic" "alarms" {
    name = "${var.environment}-bmo-learning-alarms"
  }

  resource "aws_sns_topic_subscription" "alarms_email" {
    topic_arn = aws_sns_topic.alarms.arn
    protocol  = "email"
    endpoint  = var.alarm_email
  }

  # RDS CPU Utilization Alarm
  resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
    alarm_name          = "${var.environment}-rds-high-cpu"
    comparison_operator = "GreaterThanThreshold"
    evaluation_periods  = 2
    metric_name         = "CPUUtilization"
    namespace           = "AWS/RDS"
    period              = 300
    statistic           = "Average"
    threshold           = 80
    alarm_description   = "RDS CPU utilization is too high"
    alarm_actions       = [aws_sns_topic.alarms.arn]

    dimensions = {
      DBInstanceIdentifier = var.db_instance_id
    }
  }

  # RDS Storage Space Alarm
  resource "aws_cloudwatch_metric_alarm" "rds_storage" {
    alarm_name          = "${var.environment}-rds-low-storage"
    comparison_operator = "LessThanThreshold"
    evaluation_periods  = 1
    metric_name         = "FreeStorageSpace"
    namespace           = "AWS/RDS"
    period              = 300
    statistic           = "Average"
    threshold           = 10737418240  # 10 GB in bytes
    alarm_description   = "RDS free storage space is low"
    alarm_actions       = [aws_sns_topic.alarms.arn]

    dimensions = {
      DBInstanceIdentifier = var.db_instance_id
    }
  }

  # ECS Service CPU Alarm
  resource "aws_cloudwatch_metric_alarm" "ecs_cpu" {
    alarm_name          = "${var.environment}-ecs-high-cpu"
    comparison_operator = "GreaterThanThreshold"
    evaluation_periods  = 2
    metric_name         = "CPUUtilization"
    namespace           = "AWS/ECS"
    period              = 300
    statistic           = "Average"
    threshold           = 85
    alarm_description   = "ECS service CPU utilization is too high"
    alarm_actions       = [aws_sns_topic.alarms.arn]

    dimensions = {
      ClusterName = var.cluster_name
      ServiceName = var.service_name
    }
  }

  # ALB 5XX Errors Alarm
  resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
    alarm_name          = "${var.environment}-alb-high-5xx-errors"
    comparison_operator = "GreaterThanThreshold"
    evaluation_periods  = 1
    metric_name         = "HTTPCode_Target_5XX_Count"
    namespace           = "AWS/ApplicationELB"
    period              = 300
    statistic           = "Sum"
    threshold           = 10
    alarm_description   = "ALB is receiving too many 5XX errors"
    alarm_actions       = [aws_sns_topic.alarms.arn]

    dimensions = {
      LoadBalancer = var.alb_arn_suffix
    }
  }
  ```

### 5.2 CloudWatch Dashboard
- [ ] Create `infrastructure/modules/monitoring/dashboard.tf`
  ```hcl
  resource "aws_cloudwatch_dashboard" "main" {
    dashboard_name = "${var.environment}-bmo-learning-dashboard"

    dashboard_body = jsonencode({
      widgets = [
        {
          type = "metric"
          properties = {
            metrics = [
              ["AWS/ECS", "CPUUtilization", { stat = "Average", label = "ECS CPU" }],
              ["AWS/RDS", "CPUUtilization", { stat = "Average", label = "RDS CPU" }],
            ]
            period = 300
            stat   = "Average"
            region = var.aws_region
            title  = "CPU Utilization"
          }
        },
        {
          type = "metric"
          properties = {
            metrics = [
              ["AWS/ApplicationELB", "RequestCount", { stat = "Sum" }],
              [".", "TargetResponseTime", { stat = "Average" }],
            ]
            period = 300
            region = var.aws_region
            title  = "ALB Metrics"
          }
        },
        {
          type = "log"
          properties = {
            query   = "SOURCE '/ecs/${var.environment}-bmo-learning' | fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20"
            region  = var.aws_region
            title   = "Recent Errors"
          }
        }
      ]
    })
  }
  ```

**Validation**: CloudWatch dashboard visible in AWS console

## 6. Environment Configurations

### 6.1 Development Environment
- [ ] Create `infrastructure/environments/dev/main.tf`
  ```hcl
  module "networking" {
    source = "../../modules/networking"

    environment        = "dev"
    vpc_cidr           = "10.0.0.0/16"
    availability_zones = ["us-east-1a", "us-east-1b"]
    enable_nat_gateway = false  # Cost savings for dev
  }

  module "storage" {
    source = "../../modules/storage"

    environment             = "dev"
    private_subnet_ids      = module.networking.private_subnet_ids
    rds_security_group_id   = module.networking.rds_sg_id
    elasticache_security_group_id = module.networking.elasticache_sg_id

    db_instance_class       = "db.t4g.micro"
    db_allocated_storage    = 20
    multi_az                = false
    backup_retention_period = 1

    redis_node_type         = "cache.t4g.micro"
    redis_num_cache_nodes   = 1
  }

  module "compute" {
    source = "../../modules/compute"

    environment            = "dev"
    vpc_id                 = module.networking.vpc_id
    public_subnet_ids      = module.networking.public_subnet_ids
    private_subnet_ids     = module.networking.private_subnet_ids
    alb_security_group_id  = module.networking.alb_sg_id
    ecs_security_group_id  = module.networking.ecs_tasks_sg_id

    rails_api_cpu          = 256
    rails_api_memory       = 512
    rails_api_desired_count = 1
    rails_api_min_count    = 1
    rails_api_max_count    = 2

    ai_service_cpu         = 512
    ai_service_memory      = 1024
    ai_service_desired_count = 1

    db_secret_arn          = module.storage.db_secret_arn
    redis_secret_arn       = module.storage.redis_secret_arn
  }
  ```

### 6.2 Production Environment
- [ ] Create `infrastructure/environments/production/main.tf`
  ```hcl
  module "networking" {
    source = "../../modules/networking"

    environment        = "production"
    vpc_cidr           = "10.1.0.0/16"
    availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]
    enable_nat_gateway = true
  }

  module "storage" {
    source = "../../modules/storage"

    environment             = "production"
    private_subnet_ids      = module.networking.private_subnet_ids
    rds_security_group_id   = module.networking.rds_sg_id
    elasticache_security_group_id = module.networking.elasticache_sg_id

    db_instance_class       = "db.r6g.xlarge"
    db_allocated_storage    = 100
    db_max_allocated_storage = 500
    multi_az                = true
    backup_retention_period = 30

    redis_node_type         = "cache.r6g.large"
    redis_num_cache_nodes   = 3
  }

  module "compute" {
    source = "../../modules/compute"

    environment            = "production"
    vpc_id                 = module.networking.vpc_id
    public_subnet_ids      = module.networking.public_subnet_ids
    private_subnet_ids     = module.networking.private_subnet_ids
    alb_security_group_id  = module.networking.alb_sg_id
    ecs_security_group_id  = module.networking.ecs_tasks_sg_id

    rails_api_cpu          = 1024
    rails_api_memory       = 2048
    rails_api_desired_count = 3
    rails_api_min_count    = 2
    rails_api_max_count    = 10

    ai_service_cpu         = 2048
    ai_service_memory      = 4096
    ai_service_desired_count = 2
    ai_service_min_count   = 2
    ai_service_max_count   = 10

    db_secret_arn          = module.storage.db_secret_arn
    redis_secret_arn       = module.storage.redis_secret_arn
  }

  module "monitoring" {
    source = "../../modules/monitoring"

    environment    = "production"
    cluster_name   = module.compute.cluster_name
    alb_arn_suffix = module.compute.alb_arn_suffix
    db_instance_id = module.storage.db_instance_id
    alarm_email    = "ops-team@bmo.com"
  }
  ```

**Validation**: `terraform plan` for each environment

## Phase 5 Checklist Summary

### Terraform Setup
- [ ] S3 backend for state management
- [ ] DynamoDB table for state locking
- [ ] Provider configuration with default tags
- [ ] Module structure organized

### Networking
- [ ] VPC with public and private subnets (multi-AZ)
- [ ] Internet Gateway and NAT Gateways
- [ ] Route tables configured
- [ ] Security groups (ALB, ECS, RDS, ElastiCache)

### Storage
- [ ] RDS PostgreSQL with pgvector support
- [ ] Multi-AZ for production
- [ ] Automated backups configured
- [ ] ElastiCache Redis cluster
- [ ] S3 buckets for documents and ML models
- [ ] Lifecycle policies for cost optimization
- [ ] Secrets Manager integration

### Compute
- [ ] ECS Fargate cluster with Container Insights
- [ ] Application Load Balancer with HTTPS
- [ ] Task definitions for Rails and Python services
- [ ] ECS services with health checks
- [ ] Auto-scaling policies (CPU-based)
- [ ] CloudWatch log groups

### Monitoring
- [ ] CloudWatch alarms (CPU, storage, errors)
- [ ] SNS topic for notifications
- [ ] CloudWatch dashboard
- [ ] Log aggregation

### Environments
- [ ] Dev environment (cost-optimized)
- [ ] Staging environment (production-like)
- [ ] Production environment (HA, multi-AZ)
- [ ] Environment-specific variables

### Security
- [ ] VPC isolation
- [ ] Security group least privilege
- [ ] Secrets in AWS Secrets Manager
- [ ] Encryption at rest and in transit
- [ ] IAM roles with minimal permissions

## Deployment Instructions

### Initial Deployment
```bash
# Navigate to environment
cd infrastructure/environments/dev

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -out=tfplan

# Apply (after review)
terraform apply tfplan
```

### Updating Infrastructure
```bash
# After code changes
terraform plan -out=tfplan
terraform apply tfplan
```

### Destroying Infrastructure
```bash
# Dev/Staging only (be careful!)
terraform destroy
```

## Handoff Criteria
- [ ] All Terraform modules validate successfully
- [ ] Dev environment deployed and functional
- [ ] Staging environment deployed
- [ ] Production environment planned (ready to apply)
- [ ] CloudWatch alarms configured and tested
- [ ] Secrets stored in Secrets Manager
- [ ] Auto-scaling tested under load
- [ ] Backup and recovery tested
- [ ] Cost estimation documented

## Next Phase
Proceed to **[Phase 6: Security & Compliance](./06-security-compliance.md)** for security hardening.

---

**Estimated Time**: 8-10 days
**Complexity**: High
**Key Learning**: Terraform, AWS ECS, Infrastructure as Code, Multi-Environment Setup
**Dependencies**: Phases 1-4 (all services containerized)
