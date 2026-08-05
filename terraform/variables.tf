variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "eu-central-1"
}

variable "environment" {
  description = "Deployment environment name, used in tags and resource naming."
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Short project identifier, used as a prefix for resource names."
  type        = string
  default     = "ragdoll"
}

variable "qdrant_url" {
  description = "Qdrant endpoint URL (Qdrant Cloud or self-hosted) — external SaaS, not managed by this Terraform config. No default: the app cannot function without a real value."
  type        = string
}

variable "collection_name" {
  description = "Qdrant collection name, must match src/ragdoll/api/config.py default."
  type        = string
  default     = "ragdoll_chunks"
}

variable "desired_count" {
  description = "Number of ECS Fargate tasks to run. Keep at 0 until an image has been pushed to ECR (Phase 06 CI/CD) — otherwise ECS retries a failing image pull indefinitely, burning Fargate minutes for nothing."
  type        = number
  default     = 0
}

variable "budget_monthly_limit_usd" {
  description = "Monthly AWS cost budget in USD. Writeup section 6 estimates ~5-10 PLN/month for the low-cost scenario; this is a safety ceiling above that, not the expected spend."
  type        = number
  default     = 15
}

variable "budget_alert_email" {
  description = "Email address for AWS Budget threshold notifications. Set via terraform.tfvars (gitignored) — no default, this isn't something to commit."
  type        = string
}
