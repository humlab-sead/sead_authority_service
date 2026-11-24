# Phase 2 Task Plan: First Deployment to the Target Host

## Phase Summary

**Goal:** Deploy Authority Service under rootless Podman on the identified host for the first time, then verify service health, selected settings, mounted config/log behavior, and current systemd user-unit state.

**Readiness:** The host-gateway fix is applied and the service is running under the deployment user's systemd unit. The operator approved remote `dev` commit `1f459f3ac8896bf76ea303cad2a9a574560944e4` and tag `phase2-20261012-1f459f3`. The image was published and pulled; GHCR reports digest `sha256:21dcbf3c35047dd307139a8693862f7f37a292c23fc7080165be9cd5b8ce0d50`, and its revision label matches the approved commit. After earlier config-permission and unsupported `pool_min_size` failures, the third start timed out during pool initialization. The configured database hostname resolved to this server and was refused from the container. Shape Shifter documents this host-LAN-address failure mode. The source and target Compose files now map `host.docker.internal` to `host-gateway`, and both source and target runtime `.env` files set the DB host to `host.docker.internal`. The actual staged Compose async-pool check passed. The systemd-managed service is enabled and active; `/is_alive` returns `alive`, its pool initialized, the config is readable, and a log write appeared on the host mount. The operator waived a real reboot test, so post-reboot startup remains unverified.

**Sources:** [proposal](./PODMAN_DEPLOYMENT_MIGRATION.md), [phase plan](./PODMAN_DEPLOYMENT_MIGRATION_PHASE_PLAN.md), and [Phase 1 task plan](./PODMAN_DEPLOYMENT_MIGRATION_PHASE_1_TASK_PLAN.md).

**Constraints:** Use secrets/config/ as the application-config source and secrets/.env as the runtime environment source. The .env environment is production. Use the unique matching .pgpass entry for SEAD_AUTHORITY_OPTIONS_DATABASE_PASSWORD; do not mount .pgpass. The operator explicitly says the empty OPENAI_API_KEY is intentional because the OpenAI feature is disabled; do not block on it. Do not use tmp/legacy_deploy. Do not run Docker and Podman together or add crossover checks. The operator waived an actual reboot test; check current unit state and record post-reboot startup as unverified. If a required deployment check fails, disable and stop the new Podman service and leave the application undeployed.

## Phase Acceptance Criteria

1. `PH2-AC-1` (from `P-AC-1`): The target host starts the service using the documented rootless Podman setup.
2. `PH2-AC-2` (from `P-AC-2`): The running service uses the approved GHCR tag, environment inputs, config and log mounts, and default port `8024`.
3. `PH2-AC-3` (from `P-AC-3`): The target uses the operator-designated credentials from `secrets/`; values are neither committed nor copied from `tmp/legacy_deploy`.
4. `PH2-AC-4` (from `P-AC-4`): `/is_alive` responds and the systemd user service starts the container after host reboot.
5. `PH2-AC-5` (from `P-AC-5`): Validation checks the first Podman deployment directly without a side-by-side Docker run or crossover comparison.

## Repository Findings

**Repository basis:** Branch sims-identity-allocation-phase-1, commit c2e2a92bde3876cf027ba727fc5d5f193df5340b, updated 2026-10-12. Pre-existing changes were preserved: .gitignore is modified, and deployment/ and the migration documents were already untracked. The gitignored secrets directory is mode 0700; .env, .pgpass, and deployment-secrets.yml are mode 0600. The runtime .env now also sets the approved container UID/GID to 1026:1027. The environment markers now agree on production. A unique .pgpass entry matches the runtime database coordinates using its wildcard fields; its password is in the ignored .env without being printed. The operator says the empty OpenAI key is intentional because the feature is disabled. The target's account switch, first-deployment state, rootless tool versions, and free port were checked from the tool shell. The deployment account cannot read the repository bundle path directly, so the bundle was streamed into an account-owned path before running its Makefile. The pulled image runs as UID/GID 999:999; startup records show this process could not read the mode-0600 config owned by UID 1026.

| Evidence | Verified finding | Planning implication |
|---|---|---|
| docs/proposals/done/PODMAN_DEPLOYMENT_MIGRATION/PODMAN_DEPLOYMENT_MIGRATION_PHASE_PLAN.md | Phase 2 is a first deployment. If a required check fails, stop and disable the new service. | Do not add Docker backup, cutover, or restore tasks. |
| secrets/deployment-secrets.yml and live host checks | Host and deployment-account fields match; the record and runtime .env both select production. The local files are gitignored and have restrictive modes. | Keep host-specific values in the ignored secrets directory and avoid printing secret values. |
| Operator report and sudo check | Authority Service has never been deployed here; sudo -n -u authority-service.sead.se id succeeds from the tool shell. | Use the deployment user's rootless Podman and systemd manager. |
| secrets/config/, secrets/.env, and secrets/.pgpass | The config folder contains config.yml, entities.yml, and prompts.yml. One .pgpass entry matches the .env database coordinates and has a non-empty password; the .env now contains that mapped password. The operator says the empty OpenAI key means the feature is disabled. | Stage the selected config and .env; do not mount .pgpass or require an OpenAI key. |
| deployment/container/Makefile and podman-compose.yml | The bundle sets up $HOME/container, uses config/ and logs/ mounts, and defaults to image latest and port 8024. The Compose service uses /is_alive. | Use the bundle defaults unless the .env provides an approved override; redact resolved configuration output. |
| deployment/container/service/sead-authority-service.service and Makefile | The unit runs podman-compose from %h/container; service-enable enables lingering and starts the unit. | Install and enable the unit as authority-service.sead.se. A real reboot test is waived. |
| Phase 1 task plan | Local bundle checks V-1 through V-9 are recorded as passing. They do not verify target runtime settings or target service behavior. | Run the remaining checks on the target host. |
| Target inventory | Before deployment, the user's container list, runtime directory, and unit were absent; port 8024 was free. After the failed start, cleanup removed the container and left the unit disabled and port free. | This is a first deployment with no existing service to cut over or restore. |
| Pulled image and startup journal | The first start showed appuser 999:999 could not read the private config. The approved second start used UID/GID 1026:1027 and passed the config permission point, but application startup exited with TypeError: the image connection factory rejected the `pool_min_size` keyword supplied by the selected config. | Keep the config private. Resolve the image/config startup contract before another start. |
| GHCR package tags and image labels checked 2026-10-12 | `latest`/`main` point to revision 9f18bd7 (created 2026-01-02); `dev` points to revision ef08c52 (created 2025-10-23). The published main/dev revisions inspected do not filter pool settings before building the database connection. Current remote `dev` source has pool-option filtering, but no published image tag points to that commit. | No compatible published tag was found. Do not substitute the stale `dev` image; wait for an approved compatible tag or source ref. |
| Approved source and local image build on 2026-10-12 | The operator approved remote `dev` commit `1f459f3ac8896bf76ea303cad2a9a574560944e4`. The remote branch still points to this commit. The pinned image built as `phase2-20261012-1f459f3`; its OCI revision label matches the commit, and packaged `src/configuration/setup.py` filters `pool_min_size`, `pool_max_size`, and `pool_timeout` before database connection creation. The tag is absent from GHCR. | Publish the built image to the approved unique tag before changing the target runtime or retrying startup. |
| Published image and deployment start on 2026-10-12 | Tag `phase2-20261012-1f459f3` was published and pulled. GHCR digest is `sha256:21dcbf3c35047dd307139a8693862f7f37a292c23fc7080165be9cd5b8ce0d50`; its revision label matches the approved commit. The third start timed out because the container used the host's LAN address for its database. With the host-gateway mapping and DB host alias applied, the async pool check passed, the service started under systemd, and `/is_alive` returned `alive`. | Keep the host-gateway mapping in Compose and the DB host alias in both source and target `.env` files. The real reboot test is waived. |

## Scope

**In scope:** Verify the host and deployment account; confirm the target has no Authority Service deployment and that port `8024` is available; reconcile the target environment and required credentials; stage the Phase 1 bundle and `secrets/config/`; start the rootless Podman service; verify health, config/log mounts, and current systemd user-unit state. The operator waived a real reboot test.

**Out of scope:** Application changes, using credentials or config from `tmp/legacy_deploy`, Docker backup or rollback, running Docker and Podman together, crossover comparisons, re-enabling GitHub Actions image publishing, and changes to Shape Shifter's host release-management setup.

## Work Breakdown

### Area 1: Confirm target and prepare first deployment

**Objective:** Verify the target is ready for its first Authority Service deployment and stage the approved runtime inputs.

**Affected code:** Target runtime under /data/authority-service.sead.se/container; application config from secrets/config/; runtime variables from secrets/.env; no application source changes.

**Dependencies:** Phase 1 bundle and validation results. Use the confirmed deployment account for target operations.

**Tasks:**

* [x] T2.1 **Change:** Record target identity, clean deployment state, and approved runtime inputs.
  * **Target:** Host humlabsead.srv.its.umu.se; operator roger; deployment account authority-service.sead.se; secrets/deployment-secrets.yml.
  * **Current → required:** Host/account details match; passwordless account switching works; no target runtime directory or unit exists; the Podman inventory is empty; port 8024 is free. Both environment markers select production. The database password was mapped from one matching .pgpass entry. The OpenAI key is intentionally empty under the operator's feature-disabled instruction.
  * **Implementation:** Confirm hostname, deployment identity, passwordless account switching, Podman inventory, runtime files, service unit, and port. Keep secrets/config/ and secrets/.env as the approved sources. Record the operator's reboot-test waiver. Do not print secret values.
  * **Constraints:** Do not use tmp/legacy_deploy or expose secret values. The operator says no OpenAI key is needed because that feature is disabled. Do not start the service until the staged runtime inputs pass V-2.
  * **Validation:** V-1, V-2.
  * **Completion evidence:** Target identity, clean state, and port are verified; production markers agree; runtime DB password is available from the designated source; OpenAI-key waiver and reboot-test waiver are recorded.

* [x] T2.2 **Change:** Stage the Phase 1 bundle, runtime environment, and selected application config.
  * **Target:** /data/authority-service.sead.se/container and the Phase 1 files under deployment/container/.
  * **Current → required:** The bundle and operator-designated files exist locally. The deployment account cannot read the repository path directly; its target runtime directory is absent.
  * **Implementation:** Stream a copy of the sanitized deployment/container bundle into an account-owned path under the deployment user's home, then run its make setup. Copy secrets/.env and the three files from secrets/config/ into $HOME/container; set .env to mode 0600 and restrict config files to the deployment user. Set the container UID/GID to 1026:1027, matching the deployment account and private config owner. Do not copy .pgpass into the runtime. Resolve the Compose configuration and pull the selected image. Review only a redacted summary; do not save or print unredacted output.
  * **Constraints:** Keep credentials outside tracked files. Do not use template credentials. Use the latest and 8024 defaults unless an approved override is recorded. Do not start the service in this task.
  * **Validation:** V-3.
  * **Completion evidence:** The runtime has the reconciled .env, selected config, and log directory; image, mounts, and port match the approved settings; the image is available locally; secret-file permissions are restricted.

**Area completion evidence:** Target identity, clean state, port, and runtime inputs are verified; the Podman bundle and selected config are staged without starting the service.

### Area 2: Start and verify the first Podman deployment

**Objective:** Start the approved image under rootless Podman and verify service behavior and current boot-service configuration.

**Affected code:** Phase 1 bundle under the deployment user's home and target runtime $HOME/container.

**Dependencies:** T2.1 and T2.2 complete. Use the deployment user's rootless Podman and systemd user manager.

**Tasks:**

* [x] T2.3 **Change:** Start the first deployment and install its systemd user service.
  * **Target:** $HOME/container and the deployment user's systemd user manager.
  * **Current → required:** No prior Authority Service deployment exists. The approved bundle and settings must run under the deployment user's rootless Podman context. The operator approved running the container process as UID/GID 1026:1027 to read private config and write logs.
  * **Implementation:** Run make up and make healthcheck as the deployment account. Confirm that only the approved port is published. Install the unit from the account-owned bundle copy, enable lingering, and enable/start the user unit. Check that the unit is enabled and active.
  * **Constraints:** Do not start Docker or another Authority Service runtime. If startup or health checks fail, disable and stop the new Podman service using V-7, then leave the application undeployed.
  * **Validation:** V-4, V-6, and, on failure, V-7.
  * **Completion evidence:** Podman runs the approved image, the health check succeeds, and the systemd user unit is enabled and active.

* [x] T2.4 **Change:** Verify application config and log writes; record the reboot-test waiver.
  * **Target:** Target runtime $HOME/container and the systemd user manager for authority-service.sead.se.
  * **Current → required:** Local Phase 1 checks do not establish target behavior. The running service must read the selected config and write logs. The operator waived a real reboot test.
  * **Implementation:** Check the mounted config and logs with V-5. Check current systemd unit state with V-6. Record that post-reboot startup was waived and remains unverified. If a required check fails, disable the unit and stop Podman with V-7.
  * **Constraints:** Do not claim reboot startup based only on an enabled unit or a local test. Do not run another runtime for comparison.
  * **Validation:** V-5, V-6, and, on failure, V-7.
  * **Completion evidence:** The service answers /is_alive, reads the selected config, writes to the mounted log directory, and the systemd user unit is enabled and active. The reboot test is explicitly recorded as waived and unverified.

**Area completion evidence:** All non-waived target checks pass, or a failed deployment is stopped and disabled with its result recorded. Post-reboot startup remains unverified under the operator's waiver.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
|---|---|---|---|
| `PH2-AC-1` (from `P-AC-1`) | `T2.1`–`T2.4` | `V-1`, `V-3`, `V-4`, `V-6` | The identified target runs the documented rootless Podman service and keeps it running after reboot. |
| `PH2-AC-2` (from `P-AC-2`) | `T2.1`–`T2.4` | `V-2`–`V-5` | The target uses its approved GHCR tag, environment, mounts, and port `8024`. |
| `PH2-AC-3` (from `P-AC-3`) | `T2.1`–`T2.2` | `V-1`–`V-3` | Runtime credentials come from an approved source; copied legacy credentials are not assumed valid or committed. |
| `PH2-AC-4` (from `P-AC-4`) | `T2.3`–`T2.4` | `V-4`–`V-6` | `/is_alive` responds and the systemd user unit starts the service after a real reboot. |
| `PH2-AC-5` (from `P-AC-5`) | `T2.3`–`T2.4` | `V-4`–`V-7` | Validation checks the Podman service directly; a failed deployment is stopped and disabled without starting Docker. |


## Acceptance-Criteria Results

| Criterion | Status | Result |
|---|---|---|
| PH2-AC-1 | Pass | The systemd user unit starts the rootless Podman service and remains active after the login shell exits. Lingering is enabled. |
| PH2-AC-2 | Pass | The running service uses the approved GHCR tag, production environment, selected config and log mounts, and port 8024. `/is_alive` returns `alive`. |
| PH2-AC-3 | Pass | The running application initialized its database pool with the designated runtime credentials; the staged Compose pool check also passed `SELECT 1`. Secret values remain in ignored files. |
| PH2-AC-4 | Partially met; reboot check waived | `/is_alive` responds and the systemd user unit is enabled and active. The operator waived a real reboot test; post-reboot startup remains unverified. |
| PH2-AC-5 | Pass | Validation used Podman only. Earlier failed containers and diagnostic containers were removed; the final service runs under the enabled systemd user unit. |

## Validation And Testing

Run target checks as authority-service.sead.se. The current account switch, host identity, rootless Podman and podman-compose versions, first-deployment state, free port, production markers, and secure database-password mapping were verified on 2026-10-12. Do not retain secret values in output or records. The operator says the empty OpenAI key is intentional because the feature is disabled. The operator waived the real reboot test; V-6 may verify current unit state but must not claim post-reboot startup.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
|---|---|---|---|---|---|
| V-1 | Target identity, first-deployment state, and port | Check hostname, deployment account identity, sudo -n account switching, rootless Podman containers, runtime directory, user unit, and listeners on port 8024. Compare host/account fields with secrets/deployment-secrets.yml. | PH2-AC-1, PH2-AC-2, PH2-AC-3 | Identity matches; account switch works; no prior Authority Service deployment is present; port 8024 is free. | Pass: hostname and UID/GID match; Podman inventory is empty; runtime directory and unit are absent; port 8024 has no listener. |
| V-2 | Runtime environment and credential inputs | Compare environment markers and variable names/status with secrets/deployment-secrets.yml, .pgpass, the bundle template, and Compose. Confirm the DB password maps from the unique matching .pgpass entry without printing it. Check mode 0600; do not mount .pgpass. | PH2-AC-2, PH2-AC-3 | Runtime selects production and has database credentials from the designated source; secret files remain restricted. The intentionally empty OpenAI key is accepted under the operator's disabled-feature instruction. | Pass: environment markers agree on production; one matching non-empty .pgpass entry was mapped into the ignored .env; .env, .pgpass, and deployment record are mode 0600; the .env sets container UID/GID 1026:1027; the operator waived an OpenAI key. |
| V-3 | Staged runtime config and image | As the deployment account, run bundle setup from its account-owned copy; stage .env and secrets/config/; resolve Compose settings with secret output suppressed; pull the selected image. | PH2-AC-1, PH2-AC-2, PH2-AC-3 | The latest image (unless an approved tag overrides it) is available; config, env, mounts, and port match the approved settings. | Pass: Compose config resolves with container user 1026:1027, `host.docker.internal:host-gateway`, the production environment, selected config, and port 8024. Source and target `.env` files are mode 0600; both set the DB host to `host.docker.internal`. The deployment account pulled `phase2-20261012-1f459f3`; its revision label matches the approved commit. GHCR digest: `sha256:21dcbf3c35047dd307139a8693862f7f37a292c23fc7080165be9cd5b8ce0d50`. |
| V-4 | First start and health | As the deployment account, run make up, make healthcheck, and inspect podman-compose ps. | PH2-AC-1, PH2-AC-2, PH2-AC-4, PH2-AC-5 | Only the Podman deployment runs; /is_alive returns HTTP 200 with status alive. | Pass after applying the host-gateway settings. Attempts 1–3 failed on config permissions, unsupported `pool_min_size`, and database pool timeout. Attempt 4 initialized the pool and returned `/is_alive` 200, then exited 143 after the login shell ended while lingering was disabled. After enabling lingering and the systemd unit, the service started again and remained running: container healthy with zero restarts, systemd unit enabled/active, and `make healthcheck` returned `{"status":"alive"}`. |
| V-5 | Config and log mounts | Check that /app/config/config.yml is readable in the container. Write a temporary file under /app/logs, confirm it appears under $HOME/container/logs, remove it, and inspect startup logs for config-load errors. | PH2-AC-2, PH2-AC-5 | The service reads the selected config and writes through the mounted log directory. | Pass: the running container read `/app/config/config.yml`; a temporary file written under `/app/logs` appeared under `$HOME/container/logs` and was removed. Startup logs show successful pool and application initialization. |
| V-6 | Systemd user service and reboot waiver | Check systemctl --user is-enabled and is-active for sead-authority-service. Do not reboot. Record the operator's waiver dated 2026-10-12; post-reboot startup remains unverified. | PH2-AC-1, PH2-AC-4, PH2-AC-5 | The unit is enabled and active now. Do not report reboot persistence as passed. | Pass for current state: unit enabled and active, `loginctl` reports lingering enabled, and the service remains healthy after the login shell exits. The real reboot check was waived; post-reboot startup remains unverified. |
| V-7 | Failed first-deployment cleanup | If a required check fails, disable and stop the systemd user unit and run make down. Confirm the unit is disabled, no Authority Service container remains, and port 8024 is free. | PH2-AC-5 | The new service is stopped and will not start on a later boot; the application remains undeployed. | Pass for the earlier failed attempts: failed service and diagnostic containers were removed and temporary networks cleaned. The corrected deployment is now intentionally active under systemd, and port 8024 is listening. |
| V-8 | Container-side database connectivity diagnostic | With the service stopped, run one-off containers in the Compose network. First test the staged DB host; then temporarily add `host.docker.internal:host-gateway` and override only the DB host to that alias. Test direct `psycopg` `SELECT 1` and the application's async pool. Remove the diagnostic container and temporary override afterward. Do not start the service. | PH2-AC-2, PH2-AC-3 | The container can connect to the configured database and run `SELECT 1` directly and through the application pool. | Pass and cause confirmed. The staged DB hostname resolves to this server; direct `SELECT 1` through that host address was refused. With the gateway alias, the direct query and async pool query passed. The same mapping and host are now in the repository Compose template and staged target Compose/.env. The actual service pool initialized successfully. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
|---|---|---|---|
| Verified target and approved runtime settings | secrets/deployment-secrets.yml, secrets/.env, secrets/.pgpass, and operator/change record for non-secret notes | T2.1 | V-1 and V-2 verify target identity, clean state, port, production setting, and credential source without exposing secrets. |
| Staged rootless Podman runtime | /data/authority-service.sead.se/container | T2.2 | V-3 confirms the selected image and resolved runtime settings. |
| First Podman deployment and systemd user service | $HOME/container and deployment user's systemd manager | T2.3, T2.4 | Complete: the approved image is selected, the systemd user unit is enabled/active with lingering enabled, `/is_alive` returns `alive`, and config/log mounts passed V-5. Post-reboot startup remains unverified under the operator's waiver. |
| First-deployment result | Operator/change record | T2.4 | Records deployment results, the reboot waiver, and any cleanup after a failed check. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1: Confirm target and prepare first deployment | Complete | None remaining | T2.1 and T2.2 are complete; V-1 through V-3 passed. |
| Area 2: Start and verify Podman | Complete; reboot check waived | None for non-waived checks | The host-gateway mapping and DB host are applied in the source and target runtime files. The systemd-managed container is healthy with zero restarts, the unit is enabled/active, lingering is on, `/is_alive` returns `alive`, and V-5 config/log checks passed. The operator waived the actual reboot test, so post-reboot startup remains unverified. |

## Definition Of Done

- [x] The destination host and rootless deployment account are verified on the target.
- [x] No previous Authority Service deployment is present and port 8024 is available before first start.
- [x] The production environment and database credential source are confirmed; OpenAI-key waiver, image-tag default, mounts, and port are recorded without secret values.
- [x] The runtime uses secrets/config/ and the approved GHCR image.
- [x] The Podman service responds at /is_alive, reads the selected config, and writes to the mounted logs directory.
~~- [ ] The systemd user unit starts the service and passes health checks after a real host reboot. The operator waived this test on 2026-10-12; post-reboot startup will remain unverified.~~
~~- [ ] All five Phase 2 acceptance criteria have supporting task and validation results. PH2-AC-4 will not be fully demonstrated under the reboot waiver.~~
- [x] Failed service attempts and diagnostic containers were cleaned up before the corrected service was started under systemd.
- [x] Secret values were not committed or included in this plan or the operator/change record.

## Risks And Open Questions

- **Database connection:** The original configured hostname resolved to the target server and was refused from the container. The tested `host.docker.internal:host-gateway` mapping and runtime DB-host override are now applied to both the repository template and target runtime. The async pool diagnostic and the actual application startup both passed; the service is healthy.
- **OpenAI key:** The key remains empty by explicit operator instruction because the feature is disabled. This is not treated as the cause or as a deployment blocker.
~~- **Reboot test:** The operator waived a real reboot test on 2026-10-12. Post-reboot startup remains unverified; PH2-AC-4 is not demonstrated.~~
- **Failed starts:** Attempts 1–3 were cleaned up. The first corrected manual start initialized its pool and passed health, then exited 143 after the login shell ended while lingering was disabled. The deployment user service is now enabled with lingering, and its replacement container is healthy with zero restarts. The operator waived a real reboot test, so boot persistence is not demonstrated.
