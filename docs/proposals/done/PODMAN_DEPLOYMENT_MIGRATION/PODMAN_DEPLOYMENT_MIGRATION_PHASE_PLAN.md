# Podman Deployment Migration Phase Plan

## Summary

This plan sequences the [Podman deployment proposal](./PODMAN_DEPLOYMENT_MIGRATION.md) in two phases: prepare and validate a small Podman bundle, then deploy it on the target host for the first time. Two phases keep bundle work separate from host deployment and validation.

## Problem

The repository had Docker build and Compose assets, but Authority Service had never been deployed on the target host. The first deployment must preserve the service's image tags, environment, mounts, port, and boot behavior while validating the Podman runtime without Docker/Podman crossover checks.

## Scope

This plan covers the Podman deployment bundle and its first deployment on the target host. It excludes cutover from an existing target deployment, Docker backup or rollback, running both runtimes together, Docker comparison testing, Shape Shifter's host release-management setup, and enabling a GitHub Actions image workflow.

## Current Position

- The former Compose file ran the GHCR image, read .env, mounted config/ read-only and logs/ read-write, and published port 8024 to container port 8000 by default.
- The former build helper built and could publish GHCR images with the existing environment tag rules.
- .github/workflows/docker-build.yml is disabled. Re-enabling it is not part of this plan.
- The operator designated the gitignored secrets/config/, secrets/.env, secrets/.pgpass, and secrets/deployment-secrets.yml as the deployment inputs. Do not use tmp/legacy_deploy.
- The operator has aligned the runtime environment and deployment record to production. The database password was mapped from the unique matching .pgpass entry into the ignored runtime .env. The operator says the empty OPENAI_API_KEY is intentional because the OpenAI feature is disabled; no API key is required for this deployment.
- The operator reports that Authority Service has never been deployed on the target host. Phase 2 is an initial deployment, not a Docker cutover.
- On 2026-10-12, the first production start exited with code 3 because appuser UID/GID 999:999 could not read the private config owned by UID 1026 with mode 0600. The operator approved running as UID/GID 1026:1027, and Compose plus the ignored runtime .env now use that mapping. A second start ran as 1026:1027 but exited with code 3 because the image connection factory rejected the config's `pool_min_size` keyword. The operator approved remote `dev` commit `1f459f3ac8896bf76ea303cad2a9a574560944e4`; its image was published under `phase2-20261012-1f459f3` and verified at digest `sha256:21dcbf3c35047dd307139a8693862f7f37a292c23fc7080165be9cd5b8ce0d50`. A third start timed out during pool initialization because the configured DB hostname resolved to this server's LAN address, which was refused from the container. Shape Shifter's deployment guide documents this host-LAN-address failure mode. The source and target Compose files now map `host.docker.internal` to `host-gateway`, and both source and target `.env` files select that DB host alias. The corrected async pool check passed. A manual start initialized the pool and passed `/is_alive`, then exited 143 after its login shell ended while lingering was disabled. The systemd unit was enabled with lingering; the current container is healthy with zero restarts, `/is_alive` returns `alive`, and config-read/log-write checks passed. The operator waived a real reboot test, so post-reboot startup remains unverified.
- Planning assumption: image build and publish remain manual during this migration. Any later Actions workflow must meet P-AC-6 before it is enabled.

## Phase Plan

### Phase 1: Prepare the Podman Deployment Bundle

**Goal**

Provide a documented rootless Podman setup that preserves the current image and runtime settings.

**Focus**

- Adapt the image build and Compose service to the proposed `deployment/container/` bundle.
- Provide concise setup, build/push, lifecycle, log, status, and health-check commands, plus systemd user startup.
- Preserve GHCR image tags, `.env` inputs, config and log mounts, port `8024`, and `/is_alive`.
- Keep runtime credentials out of tracked files. Leave GitHub Actions image publishing disabled; if that changes, apply the current free runner and storage limits linked from the proposal.

**Depends On**

- The proposal's deployment and cost constraints.

**Outputs**

- A Podman deployment bundle with sanitized templates and operator guidance.
- A local validation result for the Compose configuration and image build.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`) The bundle documents the rootless Podman setup and image build/pull and lifecycle path.
- `PH1-AC-2` (from `P-AC-2`) The Podman definition retains the existing image tag convention, environment inputs, mounts, and default port.
- `PH1-AC-3` (from `P-AC-3`) Tracked environment templates contain no deployment credentials.
- `PH1-AC-4` (from `P-AC-5`) Bundle validation uses Podman only and does not require crossover checks.
- `PH1-AC-5` (from `P-AC-6`) No GitHub Actions image workflow is enabled by this phase; any later workflow change must use currently free runner options, publish directly to GHCR, and stay within free storage allowances.

**Validation Milestones**

- `VM-1` The Podman Compose configuration renders and the image builds with the supported rootless Podman setup; covers `PH1-AC-1`, `PH1-AC-2`, and `PH1-AC-4`.
- `VM-2` Tracked templates are checked for credentials and the container publishing workflow remains disabled; covers `PH1-AC-3` and `PH1-AC-5`.

**Task-Plan Handoff**

- Preserve the proposal's runtime settings and manual image publishing path.
- Use the proposal's linked GitHub billing and limits pages if image publishing is moved to Actions.
- No new deployment design decision is needed for this phase.

**Readiness**

Ready for a task plan.

### Phase 2: Deploy to the Target Host

**Goal**

Run the Authority Service under rootless Podman on the target host for the first time, using the selected application configuration and verified runtime settings, and configure boot startup.

**Focus**

- Confirm the destination host, deployment user, runtime environment, credentials, image tag, port, and mounts before starting the service. Use secrets/config/ and secrets/.env as the operator-designated sources.
- Confirm that no Authority Service deployment or process already occupies the target port; install the Podman bundle and stage the selected config and approved runtime environment. The bundle defaults to image tag latest and port 8024.
- Start the first Podman deployment on port 8024 and configure its systemd user service. If a required check fails, stop and disable this new service and leave the application undeployed.
- Confirm /is_alive, configuration reads, log writes, and that the systemd user unit is enabled and active. The operator waived an actual host reboot test; record post-reboot startup as unverified.

**Depends On**

- Phase 1 bundle and validation results.
- Identification of the target host and deployment user, the selected application-config source, and approved target runtime environment, credentials, image tag, port, and mounts.

**Outputs**

- A first-time Podman deployment on the target host.
- A deployment result showing service health, selected settings, systemd user-unit state, and whether post-reboot startup was tested or waived.

**Acceptance Criteria**

- PH2-AC-1 (from P-AC-1) The target host starts the service using the documented rootless Podman setup.
- PH2-AC-2 (from P-AC-2) The running service uses the approved GHCR tag, environment inputs, config and log mounts, and default port 8024.
- PH2-AC-3 (from P-AC-3) The target uses credentials from the operator-designated secure sources; no credential from tmp/legacy_deploy is assumed valid or committed.
- PH2-AC-4 (from P-AC-4) /is_alive responds and the systemd user service starts the container after host reboot.
- PH2-AC-5 (from P-AC-5) Validation checks the first Podman deployment directly without a side-by-side Docker run or crossover comparison.

**Validation Milestones**

- VM-3 The Podman service responds at /is_alive, reads the target config, and writes logs to the mounted directory; covers PH2-AC-1, PH2-AC-2, and PH2-AC-3.
- VM-4 The systemd user service is enabled and active. The operator waived a real reboot, so post-reboot startup is not demonstrated; covers PH2-AC-4 only in part and PH2-AC-5.

**Task-Plan Handoff**

- Use secrets/config/ for application config and secrets/.env for runtime variables. Both now select production. The database password comes from the unique matching secrets/.pgpass entry and is written only to the ignored runtime .env; do not mount .pgpass.
- The operator says the empty OPENAI_API_KEY is intentional because the feature is disabled. Do not require a key for this deployment.
- Use the bundle's latest image-tag and 8024 port defaults unless an approved override is recorded.
- Confirm the target has no existing Authority Service deployment or process using the service port.
- The operator waived the real reboot test. Check that the systemd user unit is enabled and active, but record post-reboot startup as unverified.
- If a required deployment check fails, disable and stop the new Podman service and leave the application undeployed. There is no previous deployment to restore.
- Keep validation limited to the Podman service and its documented behavior.

**Readiness**

Phase 2's non-waived deployment checks pass. The target identity, access, production inputs, and UID/GID mapping are verified. The approved image from remote `dev` commit `1f459f3ac8896bf76ea303cad2a9a574560944e4` is published and selected under tag `phase2-20261012-1f459f3`. The service's configured DB hostname originally resolved to the target host's LAN address, which containers could not reach. The tested host-gateway mapping and DB-host alias are now applied in the source and target runtime files, and the async pool check passed. The systemd user unit is enabled and active with lingering; the container is healthy with zero restarts, `/is_alive` returns `alive`, and the config/log mounts passed. The operator waived a real host reboot, so post-reboot startup remains unverified. The empty OpenAI-key waiver is recorded.

## Cross-Phase Rules

- Use the proposal's runtime settings as the parity measure; do not broaden the migration into application changes.
- Keep the operator-designated secrets under the gitignored `secrets/` directory, use restrictive permissions, and do not trust credentials copied from `tmp/legacy_deploy`.
- Do not run Docker and Podman together or add crossover validation.
- Treat Phase 2 as a first deployment; do not add target Docker backup, cutover, or restore steps.
- Recheck GitHub's current billing and storage rules before enabling any image workflow in Actions.

## Validation Strategy

Validate the bundle with Podman's Compose provider and image build in Phase 1. Validate service behavior and boot startup on the actual target host in Phase 2. If a Phase 2 check fails, disable and stop the new Podman service and leave the application undeployed. Do not run both runtimes together or require Docker crossover checks.

## Final Recommendation

Deliver the deployment in two phases: validate the Podman bundle first, then deploy it on the identified target host for the first time.
