terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket         = "bmo-learning-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
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

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

module "vpc" {
  source = "../../modules/vpc"

  environment        = "prod"
  vpc_cidr           = "10.0.0.0/16"
  availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

module "ecs" {
  source = "../../modules/ecs"

  cluster_name        = "bmo-learning-prod"
  environment         = "prod"
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
}

output "vpc_id" {
  value       = module.vpc.vpc_id
  description = "Production VPC ID"
}

output "ecs_cluster_name" {
  value       = module.ecs.cluster_name
  description = "Production ECS cluster name"
}
