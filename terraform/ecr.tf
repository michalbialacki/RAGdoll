resource "aws_ecr_repository" "app" {
  name                 = "${var.project_name}-app"
  image_tag_mutability = "MUTABLE"

  # Dev/portfolio choice, not a prod default: lets `terraform destroy` remove
  # the repo even with images still in it, so the end-of-session teardown
  # doesn't need a manual "empty the repo first" step.
  force_delete = true

  image_scanning_configuration {
    scan_on_push = true
  }
}
