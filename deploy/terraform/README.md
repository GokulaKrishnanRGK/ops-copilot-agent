# Terraform Infrastructure Scaffold

This directory defines the Infrastructure-as-Code baseline for cloud deployment.

## Layout

- Root module:
  - `versions.tf`: Terraform and provider version constraints.
  - `providers.tf`: provider configuration.
  - `variables.tf`: shared input variables.
  - `locals.tf`: shared naming and tags.
  - `main.tf`: module composition.
  - `outputs.tf`: normalized outputs for deployment consumers.
- Child modules:
  - `modules/network`
  - `modules/eks`
  - `modules/rds`
  - `modules/opensearch`
  - `modules/artifacts`
  - `modules/controllers`

## Implementation Plan

- Provider constraints and module composition are defined in the root module.
- Network, database, search, and artifact concerns are separated into child modules.
- EKS cluster + managed node group + IRSA OIDC provider are managed via `modules/eks`.
- Optional controller IRSA roles (AWS Load Balancer Controller and ExternalDNS) are managed via `modules/controllers` using OIDC outputs from `modules/eks`.
- Outputs are normalized for downstream deployment tooling consumption.
- Apply/destroy orchestration is expected to be wired via project Make targets/scripts.

## Current State

Module interfaces are defined and wired. Resource bodies are intentionally minimal and should be implemented incrementally.

## Cost-Minimized Defaults

The current defaults are tuned for low-cost test usage:

- CodeArtifact package registry creation is disabled by default (`artifacts_create_python_package_registry = false`).
- ECR image scan on push is disabled by default (`artifacts_ecr_scan_on_push = false`).
- RDS uses low baseline settings (single-AZ, `db.t3.micro`, 20 GiB storage, 1-day backup retention).

Use `deploy/terraform/environments/dev.tfvars.example` as the baseline and enable only what is needed.
