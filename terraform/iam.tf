data "aws_caller_identity" "current" {}

resource "aws_iam_role" "ecs_execution" {
  name = "${var.project_name}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Standard ECS execution role: ECR image pull + CloudWatch Logs write.
# Not app logic — this is what ECS itself needs to start the container.
resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# The execution role (not the task role) is what resolves `secrets` in the
# container definition at task startup — scoped to the one SSM parameter the
# task definition actually references, plus KMS decrypt on the SecureString's
# key (the default AWS-managed "alias/aws/ssm" key, since no custom CMK was
# specified on the parameter).
resource "aws_iam_role_policy" "ssm_read" {
  name = "${var.project_name}-ssm-read"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "GetQdrantUrlParameter"
        Effect   = "Allow"
        Action   = "ssm:GetParameters"
        Resource = aws_ssm_parameter.qdrant_url.arn
      },
      {
        Sid      = "DecryptSsmDefaultKey"
        Effect   = "Allow"
        Action   = "kms:Decrypt"
        Resource = "arn:aws:kms:${var.aws_region}:${data.aws_caller_identity.current.account_id}:alias/aws/ssm"
      }
    ]
  })
}

resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Least-privilege: scoped to the two specific models the app actually calls
# (dense_embedding.py, llm_client.py), not "bedrock:*" or a foundation-model
# wildcard.
resource "aws_iam_role_policy" "bedrock_invoke" {
  name = "${var.project_name}-bedrock-invoke"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "InvokeTitanEmbeddings"
        Effect   = "Allow"
        Action   = "bedrock:InvokeModel"
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v2:0"
      },
      {
        # Cross-region inference profile: the profile ARN is what the app
        # calls directly (llm_client.py's INFERENCE_PROFILE_ID).
        Sid      = "InvokeClaudeHaikuInferenceProfile"
        Effect   = "Allow"
        Action   = "bedrock:InvokeModel"
        Resource = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/eu.anthropic.claude-haiku-4-5-20251001-v1:0"
      },
      {
        # AWS requires InvokeModel on the underlying foundation-model ARN too,
        # not just the profile — the profile can route the request to any EU
        # region, so the region segment must stay a wildcard here (it isn't
        # scope creep, it's how cross-region inference profiles work).
        Sid      = "InvokeClaudeHaikuUnderlyingModel"
        Effect   = "Allow"
        Action   = "bedrock:InvokeModel"
        Resource = "arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0"
      }
    ]
  })
}
