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
  description = "List of public subnet IDs for NLB"
  type        = list(string)
}

variable "certificate_arn" {
  description = "ACM certificate ARN for TLS (optional)"
  type        = string
  default     = null
}

# Network Load Balancer
# Cost: $18.40/month vs $25/month for ALB (28% cheaper)
resource "aws_lb" "main" {
  name               = "bmo-learning-${var.environment}-nlb"
  internal           = false
  load_balancer_type = "network"
  subnets            = var.public_subnet_ids

  enable_deletion_protection       = false # Set to true for production
  enable_cross_zone_load_balancing = true

  tags = {
    Name        = "bmo-learning-${var.environment}-nlb"
    Environment = var.environment
  }
}

# Target Group for Rails API (Port 3000)
# NLB uses TCP protocol, health checks use HTTP
resource "aws_lb_target_group" "rails_api" {
  name        = "bmo-learning-${var.environment}-rails"
  port        = 3000
  protocol    = "TCP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    interval            = 30
    protocol            = "HTTP"
    path                = "/health"
    port                = "3000"
  }

  deregistration_delay = 30

  tags = {
    Name        = "bmo-learning-${var.environment}-rails"
    Environment = var.environment
  }
}

# Target Group for AI Service (Port 8000)
# Only used for internal health checks - not exposed through NLB
resource "aws_lb_target_group" "ai_service" {
  name        = "bmo-learning-${var.environment}-ai"
  port        = 8000
  protocol    = "TCP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    interval            = 30
    protocol            = "HTTP"
    path                = "/health"
    port                = "8000"
  }

  deregistration_delay = 30

  tags = {
    Name        = "bmo-learning-${var.environment}-ai"
    Environment = var.environment
  }
}

# HTTP Listener (Port 80) - Forwards to Rails API
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.rails_api.arn
  }
}

# TLS Listener (Port 443) - Optional, if certificate provided
resource "aws_lb_listener" "tls" {
  count = var.certificate_arn != null ? 1 : 0

  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "TLS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.rails_api.arn
  }
}

# Outputs
output "nlb_id" {
  description = "NLB ID"
  value       = aws_lb.main.id
}

output "nlb_arn" {
  description = "NLB ARN"
  value       = aws_lb.main.arn
}

output "nlb_dns_name" {
  description = "NLB DNS name"
  value       = aws_lb.main.dns_name
}

output "nlb_zone_id" {
  description = "NLB zone ID for Route53 alias"
  value       = aws_lb.main.zone_id
}

output "ai_service_target_group_arn" {
  description = "AI Service target group ARN (for health checks only)"
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

output "tls_listener_arn" {
  description = "TLS listener ARN (if exists)"
  value       = var.certificate_arn != null ? aws_lb_listener.tls[0].arn : null
}
