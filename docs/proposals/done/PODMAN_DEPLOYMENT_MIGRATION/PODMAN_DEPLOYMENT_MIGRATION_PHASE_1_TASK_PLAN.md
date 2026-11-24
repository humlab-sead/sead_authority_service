# Phase 1 Task Plan: Prepare the Podman Deployment Bundle

## Phase Summary

**Goal:** Provide a documented rootless Podman bundle that preserves the current image tags and runtime settings.

**Readiness:** Validated. Phase 1 is ready in the [phase plan](./PODMAN_DEPLOYMENT_MIGRATION_PHASE_PLAN.md). Repository targets and validation methods are verified. The build helper and README define the selected GitHub ref as the image source; the Dockerfile's later local copies conflict with that documented behavior, so the new Containerfile follows the documented contract and omits the overlay.

**Source documents:** [proposal](./PODMAN_DEPLOYMENT_MIGRATION.md), [phase plan](./PODMAN_DEPLOYMENT_MIGRATION_PHASE_PLAN.md).

**Constraints:** Keep image publishing manual and the GitHub Actions image workflow disabled. Keep runtime credentials out of tracked files. Do not run or compare Docker and Podman deployments.

### Phase Acceptance Criteria

1. `PH1-AC-1` (from `P-AC-1`): The bundle documents rootless setup and image build/pull and lifecycle steps.
2. `PH1-AC-2` (from `P-AC-2`): The Podman definition preserves the image tag convention, environment inputs, mounts, and default port.
3. `PH1-AC-3` (from `P-AC-3`): Tracked environment templates contain no deployment credentials.
4. `PH1-AC-4` (from `P-AC-5`): Bundle validation uses Podman only and needs no crossover checks.
5. `PH1-AC-5` (from `P-AC-6`): This phase does not enable an Actions image workflow; any later workflow change must use free runner options, publish directly to GHCR, and stay within free storage limits.

## Repository Findings

**Repository basis:** Branch `sims-identity-allocation-phase-1`, commit `d329f8e9db8dcc0d16d770b88387733776d061cf`, planning date 2026-10-11. Uncommitted changes were considered: the source proposal and phase plan are untracked; `docs/proposals/README.md` is modified, three `SIMS_TARGET_ID_CONTRACT` documents are deleted, and a `SIMS_TARGET_ID_CONTRACT/` directory is untracked. Those unrelated changes were left untouched. No implementation files were changed.

| Evidence | Verified finding | Planning implication |
|---|---|---|
| `former Dockerfile` | Builds a Python 3.13 slim image, installs the app as non-root, exposes port 8000, and checks `/is_alive`. It clones when `FROM_GITHUB=true`, then unconditionally copies `pyproject.toml`, `README.md`, `src/`, and `main.py` from the local build context. | The new `Containerfile` must build the selected source ref without allowing local copies to replace it. Preserve the runtime user, port, and health endpoint. |
| `former build helper`, `former deployment guide` | The manual build interface selects a Git ref and deployment environment, derives the existing GHCR tags, builds `linux/amd64`, and can push. Its documentation says the selected GitHub ref is the image source. | Keep the options and tag mapping, replace Docker build/push with Podman, and follow the documented GitHub-ref source behavior. |
| `former Compose file`, `.gitignore` | The local Compose file exists but is ignored by Git (`former Compose file`). It uses the GHCR image, `.env`, read-only `config/`, writable `logs/`, host port 8024 to container port 8000, and `restart: always`. | Use the verified settings for the new tracked Podman file. Do not stage or remove the ignored Docker file in Phase 1. |
| `former environment template`, `former config templates` | These tracked templates use placeholders or environment-variable references. `.gitignore` ignores `**/.env.*` and only exempts `former environment template`. | Copy the sanitized templates to the new bundle and add an exception for `deployment/container/.env.example`; keep `.env` ignored. |
| `.github/workflows/docker-build.yml` | At initial inspection, both jobs had `if: ${{ false }}` and the dormant Docker build used the GitHub Actions cache. The workflow remains disabled; its build job now uses the Podman helper and has no image-layer cache. | Leave the workflow disabled. The new operator documentation must state the currently checked free-runner and storage limits before any future reactivation. |
| `src/api/router.py::is_alive`, `tests/api/test_router.py::test_is_alive` | The endpoint returns `{"status": "alive"}` and an existing test covers it. No deployment-specific test files were found. | Reuse the existing endpoint test; use Podman configuration/build checks for deployment files. Do not add a Docker/Podman comparison test. |
| Local toolchain | `podman` 5.7.0, `podman-compose` 1.5.0, `make`, `systemd-analyze`, and `curl` are available. | The planned local validation commands can run in this environment once the new files exist. |

## Scope

**In scope:** Add the Podman image and Compose definitions, manual GHCR build/push helper, sanitized runtime templates, a small Makefile and systemd user unit, operator instructions, and the `.gitignore` exception needed to track the example environment file.

**Out of scope:** Install or cut over the target host, test boot startup after a real host reboot, remove the Docker files, re-enable GitHub Actions publishing, or compare the two runtimes. Phase 2 owns the target-host cutover.

## Work Breakdown

### Area 1: Build and describe the Podman container

**Objective:** Build the selected Git ref into the existing GHCR image/tag format and define a rootless Podman service with the current runtime settings.

**Affected code:** `former Dockerfile`, `former build helper`, `former Compose file`; new `deployment/container/Containerfile`, `deployment/container/podman-compose.yml`, and `deployment/container/scripts/build.sh`.

**Dependencies:** Use the selected GitHub ref as the image source, as specified by the helper and README; avoid the existing Dockerfile's local-source overlay. Use the current target deployment user's UID/GID for rootless writable mounts, following the `keep-id` pattern used by Shape Shifter.

**Tasks:**

* [x] `T1.1` **Change:** Add a Podman-compatible Containerfile that builds the selected GitHub ref and preserves the Authority Service runtime.
  * **Target:** `deployment/container/Containerfile` (NEW); reference `former Dockerfile`.
  * **Current → required:** The existing image runs Python 3.13, uses a non-root `appuser`, serves on port 8000, and checks `/is_alive`; its unconditional local `COPY` instructions currently override the cloned ref. The new build must use the selected ref as documented and must not overlay it with local source.
  * **Implementation:** Keep the runtime dependencies, command, port, non-root user, and health check. Pass build-time UID/GID for the deployment user so rootless `keep-id` mounts can write logs. Use only build syntax supported by Podman 5.7/Buildah.
  * **Constraints:** Do not change application code, Python dependencies, endpoint behavior, or the selected-ref and GHCR tag contract. Do not add local-build mode unless separately requested.
  * **Validation:** `V-3`, `V-6`.
  * **Completion evidence:** A rootless Podman build completes from the selected Git ref and the resulting image retains the expected port, user, command, and health check.

* [x] `T1.2` **Change:** Add the Podman Compose service definition.
  * **Target:** `deployment/container/podman-compose.yml` (NEW); reference the ignored local `former Compose file` for current values.
  * **Current → required:** The service uses `.env`, mounts `config/` read-only and `logs/` read-write, maps `SEAD_AUTHORITY_PORT` (default 8024) to container port 8000, and restarts automatically. The new Compose definition must retain those settings and work rootless.
  * **Implementation:** Keep the GHCR image and `SEAD_AUTHORITY_IMAGE_TAG` selection. Use `userns_mode: keep-id` with matching build-time UID/GID. Keep the file limited to this service and its required mounts.
  * **Constraints:** Do not add a network topology, reverse proxy, multi-environment layout, or crossover setup.
  * **Validation:** `V-2`.
  * **Completion evidence:** The Compose provider renders the service with the expected image, env file, mounts, port mapping, and restart policy.

* [x] `T1.3` **Change:** Add a manual Podman image build/push helper with the existing GHCR tag rules.
  * **Target:** `deployment/container/scripts/build.sh` (NEW); reference `former build helper` and `former environment template`.
  * **Current → required:** The current helper accepts `--git-ref`, `--target-env`, `--tag`, `--push`, and `--no-cache`; maps dev to `dev`, staging to `staging`, production `main` to `latest`, production version refs to the version, and other production refs to sanitized branch tags. It uses Docker Buildx.
  * **Implementation:** Preserve the options, defaults, GitHub repository/ref inputs, and tag mapping. Replace Docker Buildx with rootless `podman build` and use `podman push` only when requested. Do not place credentials in the script or add an Actions cache/artifact path.
  * **Constraints:** Do not push to GHCR during local validation. Keep current manual publishing; the Actions workflow remains disabled.
  * **Validation:** `V-3`, `V-4`, `V-7`.
  * **Completion evidence:** `bash -n` passes; a no-push staging build creates the expected local GHCR-tagged image; documented tag cases match the existing mapping.

**Completion evidence:** The new Containerfile builds under rootless Podman, the Compose definition renders, and the manual builder preserves the existing tag rules without publishing unless requested.

### Area 2: Add simple operator setup and safeguards

**Objective:** Let a deployment user configure and operate the Podman bundle without tracking runtime credentials or enabling paid GitHub workflow usage.

**Affected code:** `.gitignore`, `former environment template`, `former config templates`; new `deployment/container/.env.example`, `deployment/container/config/config.yml`, `deployment/container/config/entities.yml`, `deployment/container/config/prompts.yml`, `deployment/container/Makefile`, `deployment/container/service/sead-authority-service.service`, and `deployment/container/README.md`.

**Dependencies:** Area 1's image name, service name, and Compose file. Use `~/container` as the simple deployment-user runtime directory, following Shape Shifter's container layout without its release manager.

**Tasks:**

* [x] `T2.1` **Change:** Add sanitized runtime templates and track the example environment file.
  * **Target:** New `deployment/container/.env.example` and `deployment/container/config/{config.yml,entities.yml,prompts.yml}`; update `.gitignore`.
  * **Current → required:** `former environment template` and `former config templates` provide sanitized values and environment references. The ignore rules currently ignore the proposed `.env.example` path as well as runtime `.env` files.
  * **Implementation:** Copy the existing sanitized templates without changing configuration keys or defaults. Add `!deployment/container/.env.example` to track the new example file. Keep `deployment/container/.env` and logs ignored.
  * **Constraints:** Do not copy values from `tmp/legacy_deploy`; do not add credentials to the tracked templates.
  * **Validation:** `V-5`.
  * **Completion evidence:** Git tracks the new example and config templates, ignores the runtime `.env`, and template review finds no literal deployment credentials.

* [x] `T2.2` **Change:** Add setup, lifecycle, systemd, and operator documentation.
  * **Target:** `deployment/container/Makefile`, `deployment/container/service/sead-authority-service.service`, and `deployment/container/README.md` (all NEW).
  * **Current → required:** Docker instructions currently describe build, Compose startup, logs, and `curl` health checks. The Podman bundle needs a short equivalent setup for one rootless user.
  * **Implementation:** Provide `setup`, `build`, `push`, `pull`, `up`, `down`, `restart`, `logs`, `status`, `healthcheck`, and minimal user-service install/enable targets. Setup creates `~/container/.env` from the example only when absent and creates `logs/`. The user service starts/stops the Compose project from `~/container`; document enabling linger for boot startup. Document `/is_alive`, port 8024, the tag examples, and these current GitHub limits checked on 2026-10-11: standard GitHub-hosted runners are free for public repositories, larger runners are billed, GitHub Free includes 500 MB of artifact storage and 10 GB of cache per repository, and public GHCR packages are free. Publish images directly to GHCR, avoid image artifacts, keep any cache and artifacts within their limits, set retention/cleanup, link the proposal's official billing pages, and recheck before enabling a workflow.
  * **Constraints:** Do not copy a credential from the legacy directory, re-enable `.github/workflows/docker-build.yml`, require Docker, or add Shape Shifter's release-management scripts.
  * **Validation:** `V-2`, `V-5`, `V-6`, `V-7`, `V-8`, `V-9`.
  * **Completion evidence:** A new operator can follow the README to prepare and operate the Podman bundle; the systemd unit passes syntax verification; the Actions image workflow remains disabled.

**Completion evidence:** The new templates are trackable and sanitized, runtime `.env` stays ignored, and the README and Makefile describe the same rootless Podman workflow.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
|---|---|---|---|
| `PH1-AC-1` (from `P-AC-1`) | `T1.1`, `T1.2`, `T1.3`, `T2.2` | `V-2`, `V-3`, `V-6`, `V-8`, `V-9` | Documented setup/build/pull/lifecycle path; Compose renders and image builds. |
| `PH1-AC-2` (from `P-AC-2`) | `T1.1`, `T1.2`, `T1.3`, `T2.1` | `V-2`, `V-3`, `V-4` | Existing image tags, env inputs, mounts, and port are preserved. |
| `PH1-AC-3` (from `P-AC-3`) | `T2.1` | `V-5` | Runtime `.env` is ignored; tracked templates contain placeholders/references only. |
| `PH1-AC-4` (from `P-AC-5`) | `T1.2`, `T2.2` | `V-2`, `V-6`, `V-8` | Phase 1 validation uses Podman and existing app tests only; no Docker/Podman comparison is added. |
| `PH1-AC-5` (from `P-AC-6`) | `T1.3`, `T2.2` | `V-7` | Actions image publishing remains disabled; documented limits govern any later workflow change. |

## Validation And Testing

No application or deployment tests were run while authoring this task plan. The new deployment files do not exist yet. The current Docker Compose file was not passed through Podman because crossover validation is out of scope.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
|---|---|---|---|---|---|
| `V-1` | Local Podman toolchain | `podman --version`; `podman-compose --version` | `PH1-AC-1`, `PH1-AC-4` | Podman and Compose provider are available. | Pass: Podman 5.7.0 and podman-compose 1.5.0 are installed. |
| `V-2` | Compose configuration | Run `make -C deployment/container setup`, then from `deployment/container` run `podman-compose -f podman-compose.yml config`. | `PH1-AC-1`, `PH1-AC-2`, `PH1-AC-4` | Configuration renders with GHCR tag, env file, expected mounts, port 8024, and restart policy. | Not run: the new Makefile and Compose file do not exist. |
| `V-3` | Rootless image build and representative tag | Run `make -C deployment/container setup` and `make -C deployment/container build` using the example `main`/`staging` settings; then run `podman image exists ghcr.io/humlab-sead/sead_authority_service:staging`. Do not push. | `PH1-AC-1`, `PH1-AC-2` | Build succeeds from the selected Git ref and the local staging tag exists. | Not run: the new Containerfile and helper do not exist. |
| `V-4` | Build helper syntax and tag mapping | Run `bash -n deployment/container/scripts/build.sh`. Review the helper against the existing cases: `dev/dev → dev`, `main/staging → staging`, `main/production → latest`, and `v1.2.0/production → v1.2.0`; verify branch sanitization and explicit `--tag` handling. | `PH1-AC-2` | Script syntax passes and all documented output tags match the existing mapping. | Not run: the new helper does not exist. |
| `V-5` | Environment tracking and secret handling | From the repository root run `git check-ignore -q deployment/container/.env && ! git check-ignore -q deployment/container/.env.example`; manually review the new `.env.example` and config templates for literal credentials. | `PH1-AC-3` | Runtime `.env` is ignored; example and config templates are trackable and contain no credentials. | Fail for the proposed example path: current `**/.env.*` rule ignores it. Runtime `.env` is ignored as intended. |
| `V-6` | Containerfile and systemd unit syntax | Run `systemd-analyze verify deployment/container/service/sead-authority-service.service`; confirm the Containerfile builds in `V-3`. | `PH1-AC-1`, `PH1-AC-4` | Unit syntax is valid and the image health check targets `/is_alive` on port 8000. | Not run: the new unit and Containerfile do not exist. |
| `V-7` | GitHub Actions cost constraint | Inspect `.github/workflows/docker-build.yml`; confirm both image workflow jobs remain guarded by `if: ${{ false }}`. Review the new README against the linked official pages for standard runners only, no image artifacts, direct GHCR publishing, 500 MB GitHub Free artifact storage, 10 GB/repository cache, retention/cleanup, and a recheck before reactivation. | `PH1-AC-5` | This phase enables no image workflow; any later workflow is documented against the current free limits and rechecked before activation. | Pass: the initial image workflow was disabled and used Actions cache; it remains disabled and was adapted on 2026-10-12 to use the Podman helper, direct Podman push, and digest-based attestation, with no Actions image cache. The updated YAML parses; the workflow was not executed. Current limit values were verified in GitHub's official billing and limits documentation on 2026-10-11. |
| `V-8` | Existing application health test | `uv run pytest tests/api/test_router.py -k test_is_alive` | `PH1-AC-1`, `PH1-AC-4` | Existing health endpoint test passes with HTTP 200 and `{"status": "alive"}`. | Not run: plan authoring only; the test and application endpoint are unchanged. |
| `V-9` | Operator guide steps and command coverage | Manually follow the new README from rootless setup through `.env` setup, image build or pull, lifecycle commands, health check, and systemd user startup. Confirm each documented Make target exists and matches the described command. | `PH1-AC-1` | Instructions cover setup, build/pull, lifecycle, health check, and boot startup, and use available targets in order. | Not run: the new README and Makefile do not exist. |

### Validation Results (2026-10-11)

| ID | Result | Evidence |
|---|---|---|
| `V-1` | Pass | Podman 5.7.0 and podman-compose 1.5.0 confirmed before implementation. |
| `V-2` | Pass | `make -C deployment/container setup` created `~/container` with `.env`, `config/`, `logs/`, and bundle files; `podman-compose -f podman-compose.yml config` rendered the GHCR image, `./.env`, `./config:/app/config:ro`, `./logs:/app/logs:rw`, port `8024:8000`, `restart: always`, and `userns_mode: keep-id`. |
| `V-3` | Pass | `make -C deployment/container build` (example `main`/`staging`) completed rootless from the cloned GitHub ref; `podman image exists ghcr.io/humlab-sead/sead_authority_service:staging` succeeded. No push. Image config retains `User: appuser`, port 8000, the uvicorn command, and the `/is_alive` health check (built with `--format docker`, since Podman drops `HEALTHCHECK` from the default OCI format). |
| `V-4` | Pass | `bash -n` passes. The tag-mapping block is byte-identical to `former build helper` (`diff` of the mapping block is empty), covering `dev/dev → dev`, `main/staging → staging`, `main/production → latest`, `v1.2.0/production → v1.2.0`, branch sanitization, and `--tag` override. |
| `V-5` | Pass | `git check-ignore -q deployment/container/.env` succeeds and `deployment/container/.env.example` is not ignored. Template review: `.env.example` and `config/` are verbatim copies of the sanitized `former deployment assets` templates (placeholder values and `${ENV_VAR}` references only); no literal credentials. |
| `V-6` | Pass | `systemd-analyze verify deployment/container/service/sead-authority-service.service` exits 0. The `V-3` image retains the `/is_alive` health check on port 8000. |
| `V-7` | Pass | Both jobs in `.github/workflows/docker-build.yml` remain guarded by `if: ${{ false }}`. The disabled workflow was adapted to use the Podman build helper, Podman push, and digest-based attestation; it no longer uses Docker Buildx or an Actions image cache. The README documents direct GHCR publishing, no image artifacts, the 500 MB artifact / 10 GB cache Free limits, retention, and a recheck before reactivation, with links to the official pages. |
| `V-8` | Pass | `uv run pytest tests/api/test_router.py -k test_is_alive` → 1 passed, 23 deselected. |
| `V-9` | Pass | README walkthrough followed during validation: setup, build, pull, lifecycle, health check, and systemd targets all exist in the Makefile and were exercised in order (`setup`, `build`, `config`). Boot startup after a real reboot is Phase 2 scope. |

Implementation notes:
- `scripts/build.sh` reads `SEAD_AUTHORITY_*` keys from the environment, then the caller directory's `.env`, then the bundle `.env`, by key extraction rather than `source`, because the tracked `.env.example` keeps placeholder secrets such as `OPENAI_API_KEY=<your-openai-api-key>` that abort a plain `source`. The derived tags are unchanged.
- `make setup` refreshes the bundle files in `~/container` when they differ and never overwrites an existing `.env` or `config/`.
- The ignored local Compose file was not staged, overwritten, or deleted during Phase 1.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
|---|---|---|---|
| Podman image definition | `deployment/container/Containerfile` (NEW) | `T1.1` | Rootless image build passes and image runs as a non-root user. |
| Podman service definition | `deployment/container/podman-compose.yml` (NEW) | `T1.2` | `V-2` renders expected service settings. |
| Manual image publisher | `deployment/container/scripts/build.sh` (NEW) | `T1.3` | `V-3`, `V-4` pass; publishing remains opt-in. |
| Sanitized deployment templates | `deployment/container/.env.example`, `deployment/container/config/config.yml`, `entities.yml`, `prompts.yml` (NEW) | `T2.1` | `V-5` passes and the templates preserve current environment keys. |
| Runtime ignore rule | `.gitignore` (UPDATE) | `T2.1` | Runtime `.env` is ignored and `.env.example` is trackable. |
| Operator commands and boot unit | `deployment/container/Makefile`, `deployment/container/service/sead-authority-service.service` (NEW) | `T2.2` | Commands operate the Podman service; `V-6` passes. |
| Podman operator guide | `deployment/container/README.md` (NEW) | `T2.2` | `V-9` passes; documents setup, build/pull, runtime settings, health check, and free-tier workflow constraint. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1: Build and describe the Podman container | Done | None | `T1.1`–`T1.3` implemented 2026-10-11; validated by `V-3`, `V-4`, `V-6`. |
| Area 2: Add simple operator setup and safeguards | Done | Area 1 | `T2.1`–`T2.2` implemented 2026-10-11; validated by `V-2`, `V-5`, `V-7`, `V-9`. |

## Definition Of Done

- [x] All five Phase 1 acceptance criteria have task and validation evidence.
- [x] Both work areas and all listed deliverables are complete.
- [x] The image builds rootless from the selected Git ref and retains the documented GHCR tag mapping.
- [x] Compose preserves `.env`, config/log mounts, port 8024, and the restart policy.
- [x] `.env` remains ignored; tracked templates are sanitized and `.env.example` is trackable.
- [x] The systemd user unit and operator instructions agree on the `~/container` runtime path.
- [x] The README documents both image build and pull paths and the lifecycle commands available in the Makefile.
- [x] The GitHub Actions image workflow remains disabled and its current free-runner/storage constraints are documented.
- [x] Required deployment checks pass; no Docker/Podman crossover validation is added.
- [x] The selected Git ref is the image source, matching the existing build helper and README; the local-copy overlay is not carried into the Containerfile.
- [x] Deviations are recorded, and the source proposal and phase plan were not changed as part of the Phase 1 implementation.

Recorded deviations (2026-10-11 implementation):
- `scripts/build.sh` extracts only `SEAD_AUTHORITY_*` keys from `.env` instead of sourcing the file, because the tracked `.env.example` placeholder `OPENAI_API_KEY=<your-openai-api-key>` aborts a plain `source`. Tag derivation is unchanged.
- The build adds `--format docker` because Podman's default OCI format silently drops the Containerfile `HEALTHCHECK`; the resulting image retains the `/is_alive` check.
- `make setup` copies the bundle files into `~/container` (with change guards) so `podman-compose` and the systemd unit run from the deployment directory, matching the Shape Shifter layout the plan requires.

## Risks And Open Questions

- **Image source discrepancy:** `former build helper` and `former deployment guide` say to use the selected GitHub ref, but `former Dockerfile` copies local source after cloning. That changes which source enters the image. Follow the documented build-helper contract in the new Containerfile and do not copy local source over the selected ref.
- **Ignored Phase 1 Compose file:** Phase 1 used the ignored local Compose file settings as a reference and did not stage, overwrite, or delete that file. The current deployment uses the tracked Podman Compose file.
