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
  - `modules/rds`
  - `modules/opensearch`
  - `modules/artifacts`

## Implementation Plan

- Provider constraints and module composition are defined in the root module.
- Network, database, search, and artifact concerns are separated into child modules.
- Outputs are normalized for downstream deployment tooling consumption.
- Apply/destroy orchestration is expected to be wired via project Make targets/scripts.

## Current State

Module interfaces are defined and wired. Resource bodies are intentionally minimal and should be implemented incrementally.
