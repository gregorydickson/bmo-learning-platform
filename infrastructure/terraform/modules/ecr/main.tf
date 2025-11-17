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

variable "repositories" {
  description = "List of ECR repository names to create"
  type        = list(string)
  default     = ["ai-service", "rails-api"]
}

# ECR Repositories
resource "aws_ecr_repository" "main" {
  for_each = toset(var.repositories)

  name                 = "bmo-learning/${each.key}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name        = "bmo-learning-${each.key}"
    Environment = var.environment
  }
}

# Lifecycle policy to remove old images
resource "aws_ecr_lifecycle_policy" "main" {
  for_each   = toset(var.repositories)
  repository = aws_ecr_repository.main[each.key].name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 tagged images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep last 5 untagged images"
        selection = {
          tagStatus   = "untagged"
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 3
        description  = "Expire images older than 30 days"
        selection = {
          tagStatus   = "any"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 30
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# Repository policy to allow ECS task execution role to pull images
resource "aws_ecr_repository_policy" "main" {
  for_each   = toset(var.repositories)
  repository = aws_ecr_repository.main[each.key].name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowPullFromECS"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
      }
    ]
  })
}

# Outputs
output "repository_urls" {
  description = "Map of repository names to URLs"
  value = {
    for k, v in aws_ecr_repository.main : k => v.repository_url
  }
}

output "repository_arns" {
  description = "Map of repository names to ARNs"
  value = {
    for k, v in aws_ecr_repository.main : k => v.arn
  }
}

output "ai_service_repository_url" {
  description = "AI Service repository URL"
  value       = aws_ecr_repository.main["ai-service"].repository_url
}

output "rails_api_repository_url" {
  description = "Rails API repository URL"
  value       = aws_ecr_repository.main["rails-api"].repository_url
}
