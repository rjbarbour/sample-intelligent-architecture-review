# ACR selective power control — staged, execution disabled

Prepared for account 551828031976, us-east-1, arch-review-dev. The running services have not been stopped or updated. No schedule has been enabled.

## Package

- `power.py STATUS`: read current ECS service counts.
- `power.py PLAN_OFF`: Terraform validation and a read-only proposed OFF plan; never applies.
- `power.py PLAN_ON`: proposed restoration plan; never applies.
- `OFF --execute` / `ON --execute`: implementation staged but deliberately disabled by `EXECUTION_ENABLED=False` pending permission approval and remaining recovery validation.

The source is a separate copy of the deployed source archive. It is not a replacement for the normal deployment bundle. Do not run an unrestricted `terraform apply` from this copy. The controller uses explicit targets and a resource allowlist; retained resources cannot be deleted by an accepted plan.

## Intended OFF

1. Refuse while a deployment is running; check documents, validations and chat-job records for active/pending work. Stop submitting new work before requesting OFF. This conservative check is not an atomic application maintenance lock.
2. Save live task definitions, image references, model/environment settings, desired counts and autoscaling configuration to a private S3 restore journal. Back up Terraform state.
3. Suspend scaling and set both ECS services to zero. Wait for tasks to stop.
4. Disable deletion protection on the specific ACR ALB, then remove its listeners and ALB, NAT gateway and Elastic IP, OpenSearch collection, index bootstrap and dependent Knowledge Base/data source. Remove the NAT route. Terraform retains ownership of all resource changes.
5. Retain buckets/documents, DynamoDB rules/results, Cognito, ECR, IAM, security groups, target group, cluster/service definitions, VPC/subnets, CloudFront, KMS, logs and state.

## Intended ON

Recreate network/ALB and vector/Knowledge Base dependencies using the same Terraform state. Update the existing CloudFront origin, re-ingest the S3 document corpus, clone the previously running task definitions changing only the recreated Knowledge Base/data-source IDs, restore service counts/scaling, and wait for ECS and ALB health checks. Existing application code/model choices are preserved. Rebuilding vectors incurs embedding charges.

## Activation blockers

Automatic approval review rejected extending the shared deployment role with persistent deletion permissions and trust for a new CodeBuild project. That change did not execute; its trust policy was subsequently checked and remains unchanged. The new project was not created. A safe preparation-only validation build uses the existing project's credentials and an ephemeral buildspec override; it does not change that project's configuration or apply Terraform.

Before activation:

- Approve and provision an isolated, scoped execution role or explicitly approve scoped changes to the existing role. Scope destructive operations to ACR resources; preserve the existing deployer's OpenSearch data-access identity or explicitly authorize the isolated role for the rebuilt index.
- Verify IAM permissions for removal and recreation, including new collection IDs, Bedrock deletion/ingestion, autoscaling, task registration, private restore backups/state locks and CloudFront origin updates. Never start OFF with incomplete permissions.
- Add a cross-operation lock and stale-lock recovery before enabling concurrent manual/scheduled execution. Terraform's per-command lock alone does not serialize the complete off/on cycle.
- Run PLAN_OFF and inspect every action. Validate ON recovery through a controlled off/on cycle when downtime is authorised. ON cannot be proven end to end while the running system must remain untouched.
- Review the updated normal-deployment workflow: it must not run while the environment is off, or it could recreate paid resources. Preserve the power overlay's state-address moves for future infrastructure changes.
- Add a scheduler only if requested. None is installed now.

## Tests

`cd ops/power && python -m unittest -v test_power.py`

Tests cover rejection of retained data/identity deletions, rejection of ECS service replacement, accepted expensive-resource operations, and refusal of OFF/ON without explicit execution. They do not establish live recovery or IAM completeness.

## Completed preparation checks

AWS CodeBuild dry run `arch-review-deploy:adc61a6c-608d-4d3d-a981-4ae30d184190` succeeded. Terraform initialise/validate/PLAN_OFF passed, and the resource-change guard accepted the proposed plan. See validation.json for the exact update/delete addresses. No apply was invoked. Afterwards both application ECS services still had desired=1 and running=1, using app revision 3 and converter revision 1. The five local guard tests passed.

## Repository setup

This folder preserves the separate staged power-control package, including its Terraform overlay. Normal deployment uses the repository-root infrastructure. Create the ignored `infrastructure/tfvars/dev.tfvars` locally for the existing `arch-review` / `dev` deployment before planning; account-specific values were omitted from version control. The example file is a template, not the deployed configuration. The controller still has `EXECUTION_ENABLED=False`.
