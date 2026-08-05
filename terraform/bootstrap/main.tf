terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Bootstrap state stays local — this config creates the bucket that the
  # root config's remote state depends on, so it can't depend on that same
  # bucket itself (chicken-and-egg). Run once, rarely touched again.
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "ragdoll"
      ManagedBy = "terraform-bootstrap"
    }
  }
}

resource "aws_s3_bucket" "tfstate" {
  bucket = "ragdoll-tfstate-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

data "aws_caller_identity" "current" {}
