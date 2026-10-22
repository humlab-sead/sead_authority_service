# Proposal: Move Authority Service Deployment from Docker to Podman

## Status

- Proposed change
- Scope: single-host container deployment
- Goal: run the Authority Service with rootless Podman while preserving its current runtime configuration and access.

## Summary

Replace the Docker deployment assets with a small Podman deployment bundle modeled on Shape Shifter's container setup. Keep the existing GHCR image names and tags, deployment environment variables, configuration and log mounts, and service port.

## Problem

The current deployment uses Docker-specific build and Compose commands. Hosts moving to Podman need equivalent image build, start, stop, and health-check steps without changing the service's runtime configuration.

## Scope

- Replace the Docker image build and Compose setup with a Podman `Containerfile` and `podman-compose` definition.
- Provide concise setup and lifecycle commands for a rootless deployment user, including service startup on host boot.
- Preserve the existing GHCR repository and tag convention, `.env` settings, read-only `config` mount, writable `logs` mount, default host port `8024`, and `/is_alive` endpoint.
- Keep any GitHub Actions image build or publish workflow within GitHub's current free runner and storage allowances.
- Use `tmp/legacy_deploy` as a reference for the existing directory and environment layout. Keep host-specific credentials out of tracked files.

## Non-Goals

- Running or comparing Docker and Podman deployments side by side, or adding Docker-to-Podman crossover validation.
- Recreating Shape Shifter's release management, multi-environment host tooling, or unrelated application setup.
- Changing application behavior, configuration keys, or image registry and tag policy.

## Current Behavior

The former Docker image and Compose assets defined a service that read `.env`, mounted `config/` read-only and `logs/` read-write, and published container port `8000` on host port `8024` by default. The image used `/is_alive` as its health endpoint. Image releases were handled manually through GHCR.

The files under `tmp/legacy_deploy` are a copy from another server. Their credentials and host-specific settings are not authoritative for the target host.

## Proposed Design

Place the deployment bundle under `deployment/container/`, following Shape Shifter's container-level layout without its larger host release-management layer. Adapt the former image definition to a Podman `Containerfile`, and define the runtime service in `podman-compose.yml`.

Provide a short Makefile for setup, image build and push, start, stop, logs, status, and health check. Use one rootless deployment user and a small systemd user unit with lingering enabled so the service starts on boot. Keep the runtime `.env`, `config/`, and `logs/` alongside the deployed environment, outside version control except for a sanitized `.env.example` and config templates.

Use the target host's current environment values when moving to Podman. Do not copy credentials from `tmp/legacy_deploy` into the repository or assume they are valid for the target host.

If GitHub Actions is used to build or publish images, use standard GitHub-hosted runners for the public repository and do not use paid larger runners. Publish images directly to GHCR instead of storing image archives as Actions artifacts. Keep any required Actions artifacts and caches within the current Free plan allowances, and set retention or cleanup to prevent storage overages. GitHub currently lists standard runners for public repositories as free, Actions storage allowances as plan-limited, and Container Registry image storage and bandwidth as free. Recheck the current rules before enabling or changing the workflow: [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), [Actions limits](https://docs.github.com/en/actions/reference/limits), and [GitHub Packages billing](https://docs.github.com/en/billing/concepts/product-billing/github-packages).

## Risks And Tradeoffs

Rootless Podman needs a deployment user and a systemd user service for boot startup. This adds a small host setup step. The target host's Podman and Compose provider must support the selected Containerfile and Compose settings.

## Testing And Validation

Validate the Podman Compose configuration, build or pull the intended GHCR image, start the service, confirm `/is_alive` responds, and confirm the service reads its configuration and writes logs through the expected mounts. Check the systemd user service starts the container after reboot. Do not require Docker comparisons or crossover checks.

## Acceptance Criteria

- `P-AC-1`: A documented rootless Podman setup can build or pull and start the Authority Service on the target Linux host.
- `P-AC-2`: The deployment retains the existing GHCR image and tag convention, `.env` inputs, config and log mounts, and default port `8024`.
- `P-AC-3`: Runtime credentials are supplied by the target host and are absent from tracked deployment files.
- `P-AC-4`: The deployed service responds at `/is_alive` and starts on host boot through its systemd user service.
- `P-AC-5`: Validation covers the Podman deployment only; Docker/Podman crossover is not required.
- `P-AC-6`: Any GitHub Actions workflow used to build or publish the image uses only currently free runner options, publishes images directly to GHCR, and keeps artifacts and caches within current free storage allowances.

## Final Recommendation

Adopt a minimal rootless Podman deployment bundle, preserve the current service settings and GHCR tags, and validate the new deployment directly on its target host.
