provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ragdoll"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
