# Populated incrementally as later steps add VPC, ALB, ECS resources.

output "vpc_id" {
  description = "ID of the main VPC."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets (used by ALB and ECS Fargate)."
  value       = aws_subnet.public[*].id
}

output "alb_dns_name" {
  description = "Public DNS name of the ALB - the app's entry point."
  value       = aws_lb.main.dns_name
}

output "ecr_repository_url" {
  description = "Push images here (Phase 06 CI/CD)."
  value       = aws_ecr_repository.app.repository_url
}
