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

variable "cluster_id" {
  description = "ECS cluster ID"
  type        = string
}

variable "cluster_name" {
  description = "ECS cluster name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID for ECS tasks"
  type        = string
}

variable "task_execution_role_arn" {
  description = "ECS task execution role ARN"
  type        = string
}

variable "task_role_arn" {
  description = "ECS task role ARN"
  type        = string
}

variable "ai_service_image" {
  description = "AI service Docker image URL"
  type        = string
}

variable "rails_api_image" {
  description = "Rails API Docker image URL"
  type        = string
}

variable "ai_service_target_group_arn" {
  description = "Target group ARN for AI service"
  type        = string
}

variable "rails_api_target_group_arn" {
  description = "Target group ARN for Rails API"
  type        = string
}

variable "secret_arns" {
  description = "Map of secret ARNs"
  type = object({
    openai_api_key        = string
    database_url          = string
    redis_url             = string
    rails_secret_key_base = string
    twilio_account_sid    = string
    twilio_auth_token     = string
    slack_bot_token       = string
  })
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

variable "sidekiq_cpu" {
  description = "CPU units for Sidekiq"
  type        = number
  default     = 512
}

variable "sidekiq_memory" {
  description = "Memory (MB) for Sidekiq"
  type        = number
  default     = 1024
}

variable "ai_service_url" {
  description = "URL for AI Service"
  type        = string
}

variable "ai_service_api_key" {
  description = "API Key for AI Service"
  type        = string
  sensitive   = true
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "ai_service" {
  name              = "/ecs/bmo-learning-${var.environment}/ai-service"
  retention_in_days = 30

  tags = {
    Name        = "bmo-learning-${var.environment}-ai-service"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "rails_api" {
  name              = "/ecs/bmo-learning-${var.environment}/rails-api"
  retention_in_days = 30

  tags = {
    Name        = "bmo-learning-${var.environment}-rails-api"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "sidekiq" {
  name              = "/ecs/bmo-learning-${var.environment}/sidekiq"
  retention_in_days = 30

  tags = {
    Name        = "bmo-learning-${var.environment}-sidekiq"
    Environment = var.environment
  }
}

# AI Service Task Definition
resource "aws_ecs_task_definition" "ai_service" {
  family                   = "bmo-learning-${var.environment}-ai-service"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ai_service_cpu
  memory                   = var.ai_service_memory
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name  = "ai-service"
      image = var.ai_service_image

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "PYTHON_ENV"
          value = "production"
        },
        {
          name  = "LOG_LEVEL"
          value = "INFO"
        },
        {
          name  = "AWS_REGION"
          value = "us-east-2"
        },
        {
          name  = "OPENAI_MODEL"
          value = "gpt-4-turbo-preview"
        },
        {
          name  = "AI_SERVICE_API_KEY"
          value = var.ai_service_api_key
        }
      ]

      secrets = [
        {
          name      = "OPENAI_API_KEY"
          valueFrom = var.secret_arns.openai_api_key
        },
        {
          name      = "DATABASE_URL"
          valueFrom = var.secret_arns.database_url
        },
        {
          name      = "REDIS_URL"
          valueFrom = var.secret_arns.redis_url
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ai_service.name
          "awslogs-region"        = "us-east-2"
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import httpx; httpx.get('http://localhost:8000/health')\" || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }

      essential = true
    }
  ])

  tags = {
    Name        = "bmo-learning-${var.environment}-ai-service"
    Environment = var.environment
  }
}

# Rails API Task Definition
resource "aws_ecs_task_definition" "rails_api" {
  family                   = "bmo-learning-${var.environment}-rails-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.rails_api_cpu
  memory                   = var.rails_api_memory
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name  = "rails-api"
      image = var.rails_api_image

      portMappings = [
        {
          containerPort = 3000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "RAILS_ENV"
          value = "production"
        },
        {
          name  = "LOG_LEVEL"
          value = "INFO"
        },
        {
          name  = "AWS_REGION"
          value = "us-east-2"
        },
        {
          name  = "AI_SERVICE_URL"
          value = var.ai_service_url
        },
        {
          name  = "AI_SERVICE_API_KEY"
          value = var.ai_service_api_key
        }
      ]

      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = var.secret_arns.database_url
        },
        {
          name      = "REDIS_URL"
          valueFrom = var.secret_arns.redis_url
        },
        {
          name      = "SECRET_KEY_BASE"
          valueFrom = var.secret_arns.rails_secret_key_base
        },
        {
          name      = "TWILIO_ACCOUNT_SID"
          valueFrom = var.secret_arns.twilio_account_sid
        },
        {
          name      = "TWILIO_AUTH_TOKEN"
          valueFrom = var.secret_arns.twilio_auth_token
        },
        {
          name      = "SLACK_BOT_TOKEN"
          valueFrom = var.secret_arns.slack_bot_token
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.rails_api.name
          "awslogs-region"        = "us-east-2"
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:3000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }

      essential = true
    }
  ])

  tags = {
    Name        = "bmo-learning-${var.environment}-rails-api"
    Environment = var.environment
  }
}

# Sidekiq Task Definition
resource "aws_ecs_task_definition" "sidekiq" {
  family                   = "bmo-learning-${var.environment}-sidekiq"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.sidekiq_cpu
  memory                   = var.sidekiq_memory
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name    = "sidekiq"
      image   = var.rails_api_image
      command = ["bundle", "exec", "sidekiq", "-C", "config/sidekiq.yml"]

      environment = [
        {
          name  = "RAILS_ENV"
          value = "production"
        },
        {
          name  = "LOG_LEVEL"
          value = "INFO"
        },
        {
          name  = "AWS_REGION"
          value = "us-east-2"
        }
      ]

      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = var.secret_arns.database_url
        },
        {
          name      = "REDIS_URL"
          valueFrom = var.secret_arns.redis_url
        },
        {
          name      = "SECRET_KEY_BASE"
          valueFrom = var.secret_arns.rails_secret_key_base
        },
        {
          name      = "TWILIO_ACCOUNT_SID"
          valueFrom = var.secret_arns.twilio_account_sid
        },
        {
          name      = "TWILIO_AUTH_TOKEN"
          valueFrom = var.secret_arns.twilio_auth_token
        },
        {
          name      = "SLACK_BOT_TOKEN"
          valueFrom = var.secret_arns.slack_bot_token
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.sidekiq.name
          "awslogs-region"        = "us-east-2"
          "awslogs-stream-prefix" = "ecs"
        }
      }

      essential = true
    }
  ])

  tags = {
    Name        = "bmo-learning-${var.environment}-sidekiq"
    Environment = var.environment
  }
}

# AI Service ECS Service
resource "aws_ecs_service" "ai_service" {
  name            = "bmo-learning-${var.environment}-ai-service"
  cluster         = var.cluster_id
  task_definition = aws_ecs_task_definition.ai_service.arn
  desired_count   = var.environment == "prod" ? 2 : 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.ai_service_target_group_arn
    container_name   = "ai-service"
    container_port   = 8000
  }

  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
  }

  enable_execute_command = true

  tags = {
    Name        = "bmo-learning-${var.environment}-ai-service"
    Environment = var.environment
  }

  depends_on = [var.ai_service_target_group_arn]
}

# Rails API ECS Service
resource "aws_ecs_service" "rails_api" {
  name            = "bmo-learning-${var.environment}-rails-api"
  cluster         = var.cluster_id
  task_definition = aws_ecs_task_definition.rails_api.arn
  desired_count   = var.environment == "prod" ? 2 : 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.rails_api_target_group_arn
    container_name   = "rails-api"
    container_port   = 3000
  }

  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
  }

  enable_execute_command = true

  tags = {
    Name        = "bmo-learning-${var.environment}-rails-api"
    Environment = var.environment
  }

  depends_on = [var.rails_api_target_group_arn]
}

# Sidekiq ECS Service
resource "aws_ecs_service" "sidekiq" {
  name            = "bmo-learning-${var.environment}-sidekiq"
  cluster         = var.cluster_id
  task_definition = aws_ecs_task_definition.sidekiq.arn
  desired_count   = var.environment == "prod" ? 2 : 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = false
  }

  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 50
  }

  enable_execute_command = true

  tags = {
    Name        = "bmo-learning-${var.environment}-sidekiq"
    Environment = var.environment
  }
}

# Auto Scaling for AI Service
resource "aws_appautoscaling_target" "ai_service" {
  max_capacity       = 10
  min_capacity       = var.environment == "prod" ? 2 : 1
  resource_id        = "service/${var.cluster_name}/${aws_ecs_service.ai_service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ai_service_cpu" {
  name               = "bmo-learning-${var.environment}-ai-service-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ai_service.resource_id
  scalable_dimension = aws_appautoscaling_target.ai_service.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ai_service.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

# Auto Scaling for Rails API
resource "aws_appautoscaling_target" "rails_api" {
  max_capacity       = 10
  min_capacity       = var.environment == "prod" ? 2 : 1
  resource_id        = "service/${var.cluster_name}/${aws_ecs_service.rails_api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "rails_api_cpu" {
  name               = "bmo-learning-${var.environment}-rails-api-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.rails_api.resource_id
  scalable_dimension = aws_appautoscaling_target.rails_api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.rails_api.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

# Outputs
output "ai_service_task_definition_arn" {
  value = aws_ecs_task_definition.ai_service.arn
}

output "rails_api_task_definition_arn" {
  value = aws_ecs_task_definition.rails_api.arn
}

output "sidekiq_task_definition_arn" {
  value = aws_ecs_task_definition.sidekiq.arn
}

output "ai_service_service_name" {
  value = aws_ecs_service.ai_service.name
}

output "rails_api_service_name" {
  value = aws_ecs_service.rails_api.name
}

output "sidekiq_service_name" {
  value = aws_ecs_service.sidekiq.name
}
