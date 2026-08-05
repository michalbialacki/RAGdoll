resource "aws_ssm_parameter" "qdrant_url" {
  name  = "/${var.project_name}/qdrant_url"
  type  = "SecureString"
  value = var.qdrant_url

  tags = {
    Name = "${var.project_name}-qdrant-url"
  }
}
