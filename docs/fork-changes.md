# ACR fork changes — 19 November 2026

This fork preserves the local working changes from the ACR deployment and troubleshooting sessions.

- **Validation reruns:** the validation detail page offers **Run again** after completion, cancellation or failure, opening the existing configuration dialog with a fresh run selected.
- **Failed model calls:** a text validation for which every model call fails raises a run error rather than producing a completed report from those errors.
- **PDF validation:** whole-document image selection limits the base64 image payload to 2,000,000 bytes, including legend images, while respecting the 20-image cap. Anthropic thinking parameters are only enabled for Anthropic Claude model IDs. The existing PDF test suite includes a payload-budget regression test.
- **Deployment:** the CodeBuild buildspec and Terraform adaptations use the existing account roles rather than recreating their IAM policies. Transaction Search provisioning was removed from this deployment copy. Several stage model defaults are set explicitly in Terraform. Task-definition overrides made directly in AWS are separate from these source defaults.
- **Power control:** `ops/power/` contains the separate staged controller, its Terraform overlay, guard tests and preparation results. Execution remains disabled. Read its README for preparation gaps and recovery requirements before use.

## Deployment assumptions

The root Terraform changes rely on the previously provisioned IAM roles and permissions. They are an environment-specific deployment copy, not a complete fresh-account bootstrap. Account-specific Terraform variables, state, plans, local environment files and restore journals are excluded. Supply the target deployment variables locally before planning or deploying.

The power overlay is deliberately kept separate from normal infrastructure. Its `moved` blocks and conditional resources must be reviewed together with any future root infrastructure changes. Committing these files does not deploy them or change running services.

## Checks when saving the fork

- Five power-control guard tests passed.
- Changed Python modules parsed successfully; the Git diff passed whitespace checks.
- The backend regression suite and frontend build were not run in this save operation: the local checkout has no pytest or installed frontend dependencies.
