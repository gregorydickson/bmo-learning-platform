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

variable "public_subnet_ids" {
  description = "List of public subnet IDs for ALB"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID for ALB"
  type        = string
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS (optional)"
  type        = string
  default     = null
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "bmo-learning-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.security_group_id]
  subnets            = var.public_subnet_ids

  enable_deletion_protection = var.environment == "prod"
  enable_http2               = true
  enable_cross_zone_load_balancing = true

  # Access logs (optional - requires S3 bucket)
  # access_logs {
  #   bucket  = aws_s3_bucket.alb_logs.bucket
  #   prefix  = "alb"
  #   enabled = true
  # }

  tags = {
    Name        = "bmo-learning-${var.environment}"
    Environment = var.environment
  }
}

# Target Group for AI Service (Port 8000)
resource "aws_lb_target_group" "ai_service" {
  name        = "bmo-learning-${var.environment}-ai"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
    protocol            = "HTTP"
  }

  deregistration_delay = 30

  tags = {
    Name        = "bmo-learning-${var.environment}-ai"
    Environment = var.environment
  }
}

# Target Group for Rails API (Port 3000)
resource "aws_lb_target_group" "rails_api" {
  name        = "bmo-learning-${var.environment}-rails"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
    protocol            = "HTTP"
  }

  deregistration_delay = 30

  tags = {
    Name        = "bmo-learning-${var.environment}-rails"
    Environment = var.environment
  }
}

# HTTP Listener (redirect to HTTPS if certificate exists, otherwise forward)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = var.certificate_arn != null ? "redirect" : "forward"

    dynamic "redirect" {
      for_each = var.certificate_arn != null ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }

    dynamic "forward" {
      for_each = var.certificate_arn == null ? [1] : []
      content {
        target_group {
          arn    = aws_lb_target_group.rails_api.arn
          weight = 1
        }
      }
    }
  }
}

# HTTPS Listener (if certificate provided)
resource "aws_lb_listener" "https" {
  count = var.certificate_arn != null ? 1 : 0

  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.rails_api.arn
  }
}

# Listener Rules for path-based routing

# Route /api/v1/generate-lesson* to AI Service
resource "aws_lb_listener_rule" "ai_service_generate" {
  listener_arn = var.certificate_arn != null ? aws_lb_listener.https[0].arn : aws_lb_listener.http.arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ai_service.arn
  }

  condition {
    path_pattern {
      values = ["/api/v1/generate-lesson*"]
    }
  }
}

# Route /api/v1/ingest-documents* to AI Service
resource "aws_lb_listener_rule" "ai_service_ingest" {
  listener_arn = var.certificate_arn != null ? aws_lb_listener.https[0].arn : aws_lb_listener.http.arn
  priority     = 11

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ai_service.arn
  }

  condition {
    path_pattern {
      values = ["/api/v1/ingest-documents*"]
    }
  }
}

# Route /api/v1/validate-safety* to AI Service
resource "aws_lb_listener_rule" "ai_service_validate" {
  listener_arn = var.certificate_arn != null ? aws_lb_listener.https[0].arn : aws_lb_listener.http.arn
  priority     = 12

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ai_service.arn
  }

  condition {
    path_pattern {
      values = ["/api/v1/validate-safety*"]
    }
  }
}

# Route /docs* and /openapi.json to AI Service (FastAPI docs)
resource "aws_lb_listener_rule" "ai_service_docs" {
  listener_arn = var.certificate_arn != null ? aws_lb_listener.https[0].arn : aws_lb_listener.http.arn
  priority     = 13

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ai_service.arn
  }

  condition {
    path_pattern {
      values = ["/docs*", "/openapi.json"]
    }
  }
}

# All other /api/* routes go to Rails API (default is already set)

# Outputs
output "alb_id" {
  description = "ALB ID"
  value       = aws_lb.main.id
}

output "alb_arn" {
  description = "ALB ARN"
  value       = aws_lb.main.arn
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "ALB zone ID for Route53 alias"
  value       = aws_lb.main.zone_id
}

output "ai_service_target_group_arn" {
  description = "AI Service target group ARN"
  value       = aws_lb_target_group.ai_service.arn
}

output "rails_api_target_group_arn" {
  description = "Rails API target group ARN"
  value       = aws_lb_target_group.rails_api.arn
}

output "http_listener_arn" {
  description = "HTTP listener ARN"
  value       = aws_lb_listener.http.arn
}

output "https_listener_arn" {
  description = "HTTPS listener ARN (if exists)"
  value       = var.certificate_arn != null ? aws_lb_listener.https[0].arn : null
}
