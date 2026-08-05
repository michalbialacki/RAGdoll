output "tfstate_bucket" {
  description = "Name of the S3 bucket holding root config remote state — copy into terraform/backend.tf."
  value       = aws_s3_bucket.tfstate.id
}
