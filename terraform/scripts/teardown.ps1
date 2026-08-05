<#
.SYNOPSIS
    End-of-session teardown for RAGdoll's billable AWS resources.

.DESCRIPTION
    Runs `terraform destroy` against the ROOT config only (terraform/) —
    VPC, security groups, ALB, ECS Fargate. Deliberately never touches
    terraform/bootstrap/ (the S3 state bucket) or the AWS Budget alert,
    neither of which cost anything to leave running.

.PARAMETER AutoApprove
    Skip terraform's interactive "yes" confirmation. Off by default —
    review the destroy plan before confirming.
#>
param(
    [switch]$AutoApprove
)

$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $PSScriptRoot
Set-Location $rootDir

Write-Host "Destroying root config resources (VPC, SG, ALB, ECS) in $rootDir" -ForegroundColor Yellow
Write-Host "Bootstrap state bucket and Budget alert are NOT touched by this script." -ForegroundColor Yellow

if ($AutoApprove) {
    terraform destroy -auto-approve
} else {
    terraform destroy
}
