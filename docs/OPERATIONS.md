# SEAD Authority Service - Operations Guide

Runbook for operators and maintainers of deployed SEAD Authority Service environments. The supported container deployment uses rootless Podman and the bundle in [deployment/container/README.md](../deployment/container/README.md).

---

## Environments

| Environment | Purpose                | Typical image tag                                  |
|-------------|------------------------|----------------------------------------------------|
| Production  | Live service           | `latest`, a version tag, or an approved pinned tag |
| Staging     | Pre-release validation | `staging`                                          |
| Development | Development deployment | `dev`                                              |

Set the environment, source ref, and image tag in the deployment user's `~/container/.env`. When running more than one environment on the same host, use a separate deployment account and a distinct host port for each environment. The default host port is `8024`; the application listens on port `8000` inside the container.

---

## Operational Assumptions and Invariants

- Run the service as a dedicated Linux deployment user with rootless Podman. Do not run the deployment commands as root.
- The container uses `userns_mode: "keep-id"`. Set `SEAD_AUTHORITY_CONTAINER_UID` and `SEAD_AUTHORITY_CONTAINER_GID` to the deployment account's numeric UID and GID so it can read private config files and write logs.
- The service exposes plain HTTP. Terminate TLS at NGINX or another trusted reverse proxy.
- The identity module runs inside this service; it does not need a separate deployment.
- PostgreSQL must provide the extensions required by the enabled service features. LLM-backed strategies also need a configured, reachable provider when enabled.

---

## Configuration and Secrets

The Compose service reads runtime variables from `~/container/.env`. `make setup` creates this file with mode `0600` if it does not exist. Store database credentials, provider keys, and other secrets in that ignored file, or populate it from the approved host secret store. Do not commit secrets or include unredacted `make config` output in tickets or logs.

| Variable                                                        | Purpose                                                                  |
|-----------------------------------------------------------------|--------------------------------------------------------------------------|
| `CONFIG_FILE`                                                   | Config file path inside the container; normally `/app/config/config.yml` |
| `SEAD_AUTHORITY_ENVIRONMENT`                                    | Deployment environment (`dev`, `staging`, or `production`)               |
| `SEAD_AUTHORITY_IMAGE_TAG`                                      | GHCR image tag pulled and run by this deployment                         |
| `SEAD_AUTHORITY_PORT`                                           | Host port mapped to container port `8000` (default `8024`)               |
| `SEAD_AUTHORITY_CONTAINER_UID` / `SEAD_AUTHORITY_CONTAINER_GID` | Deployment account IDs used by the container process                     |
| `SEAD_AUTHORITY_OPTIONS_DATABASE_*`                             | PostgreSQL database name, host, port, user, and password                 |
| `LLM_PROVIDER`, `OPENAI_*`, `ANTHROPIC_*`, `OLLAMA_*`           | LLM provider selection and settings                                      |
| `GEONAMES_USERNAME`                                             | GeoNames service account, when used                                      |

The `config/` directory is mounted read-only at `/app/config/`. `config.yml` includes the entity and prompt configuration files; keep included files together or preserve their configured paths. Compose maps `host.docker.internal` to the host gateway. Use that database hostname when PostgreSQL runs on the deployment host; use the database's normal network hostname when it runs elsewhere.

---

## Runtime Data Layout

The deployment account owns the runtime at `~/container`:

| Host path                        | Container path      | Purpose                                              |
|----------------------------------|---------------------|------------------------------------------------------|
| `~/container/.env`               | Compose environment | Runtime settings and credentials                     |
| `~/container/config/`            | `/app/config/:ro`   | Application configuration                            |
| `~/container/logs/`              | `/app/logs/:rw`     | Application log files                                |
| `~/container/podman-compose.yml` | Compose definition  | Image, environment, mounts, port, and restart policy |

The container has no persistent application-data mount. Service data is stored in PostgreSQL. Database backups are managed by the SEAD database operations team.

---

## Image Build and Publication

Images use the GHCR repository
`ghcr.io/humlab-sead/sead_authority_service:<tag>`. GitHub Actions builds and
publishes staging and release images. Manual development builds use
`deployment/container/Makefile.dev` and `scripts/build.sh` from a developer
checkout; they build from the selected GitHub ref, not uncommitted local
source. Builds target `linux/amd64`.

Run these commands from a developer checkout to create a local development runtime and build or publish a dev image:

```bash
cd deployment/container
make -f Makefile.dev setup
# Edit ~/container-dev/.env with development database and provider settings.
# Set container UID/GID to the developer account's IDs.
make -f Makefile.dev build
podman login ghcr.io -u USERNAME
make -f Makefile.dev push
```

The developer Makefile defaults to the `dev` Git ref and `dev` image tag. It
only builds or publishes tags prefixed with `dev`. The runtime Makefile has no
build or push targets; deployment users only pull published images.

---

## Deployment and Updates

For initial setup or an update, a developer account on the deployment host can
sync runtime files from the checkout root with passwordless `sudo` access to
the deployment account. On first setup, run the sync without `--dry-run` because
the target directory does not exist yet:

```bash
deployment/scripts/sync-to-deploy authority-service.sead.se
```

For an existing deployment, preview the file changes first:

```bash
deployment/scripts/sync-to-deploy authority-service.sead.se --dry-run
deployment/scripts/sync-to-deploy authority-service.sead.se
```

The helper syncs runtime files to the deployment user's `~/container`, removes
obsolete bundle files, and preserves `.env`, `config/`, and `logs/`. On first
sync it creates missing `.env` and `config/` from templates. It installs the
systemd user unit for the default `container` directory and reloads the user
manager when it is running, but does not enable or restart the service or pull
an image. It uses local `sudo` and does not connect over SSH.

After syncing, run these commands as the deployment user. Edit `.env` and
stage the approved environment config before pulling the image:

```bash
cd ~/container
chmod 600 .env
make pull
make config  # Review locally; output can contain credentials.
```

For an isolated directory, pass `--remote-dir container-dev`; the helper skips
the systemd unit install and reload. It preserves that directory's own `.env`,
`config/`, and `logs/` too. On first sync, it creates `.env` with development
defaults from `.env.dev.example`. Pass `DEPLOY_DIR=~/container-dev` to runtime
Makefile commands for this directory, for example:

```bash
make pull DEPLOY_DIR=~/container-dev
```

Install and enable the user service to keep the container running and start it
at host boot:

```bash
make service-install
make service-enable
make healthcheck
make status
```

`make service-enable` enables systemd lingering for the deployment user and
starts `sead-authority-service.service`. The unit runs the same Compose project
from `~/container` as the Makefile.

To deploy a new approved image tag, update `SEAD_AUTHORITY_IMAGE_TAG` in
`~/container/.env`, then pull, restart, and verify:

```bash
make pull
make restart
make healthcheck
make status
```

---

## CI and Release Process

Container image publication runs in two paths:

- Pushes to `staging` publish `ghcr.io/humlab-sead/sead_authority_service:staging`.
- Pushes to `main` run semantic-release (`.github/workflows/release.yml`). When semantic-release creates a release tag, the same run publishes that tag and `latest` from the release commit, for example `:v1.7.0` and `:latest`.

Both paths run the test and lint jobs in `.github/workflows/build.yml` before publishing. They build from the selected GitHub ref and commit, never from the local worktree. The image workflow also supports manual `workflow_dispatch` runs for other tags.

The image workflow publishes images only; it does not deploy the service.
Deploy a published tag with the procedure above. Manual development builds use
`deployment/container/Makefile.dev` from the checkout.

---

## Post-Deployment Verification and Logs

The host health check calls `/is_alive` on `SEAD_AUTHORITY_PORT` (default `8024`):

```bash
make healthcheck
curl -fsS http://localhost:8024/is_alive
make status
make logs
```

A healthy response is `{"status":"alive"}`. Application log files are under `~/container/logs/`; `make logs` follows the container's stdout and stderr. Check the systemd user service with `systemctl --user status sead-authority-service` and its unit messages with `journalctl --user -u sead-authority-service`.

No alerting service is configured. Review the application logs and health endpoint during deployment and incident response.

## Reconciliation Readiness and Candidate Verification

`GET /reconcile` returns the OpenRefine manifest; it does not verify that the database-backed match query works. Use `GET /reconcile/readiness?type=site` to run the registered site strategy with a bounded query. An empty result is ready when the query succeeds. A missing or invalid `options:id_base`, database failure, or missing match function returns `ready: false` with a reason.

The site strategy requires `authority.fuzzy_site(text, integer)` and the `authority.site` view. Check the function with `SELECT to_regprocedure('authority.fuzzy_site(text,integer)')`. If it is missing, generate or review the SQL from the current schema source with `make generate-schema`, then deploy the generated [`schema/generated/site.sql`](../schema/generated/site.sql) through the approved database deployment process. Do not edit generated SQL directly.

`POST /reconcile/verify-candidates` performs a read-only existence check against `authority.site`. It accepts full candidate IDs under `options:id_base` and currently supports `site` only when the strategy is registered and SIMS allows `bind_existing`. Results distinguish `exists`, `not_found`, `invalid_candidate`, and `unsupported_type`. A database or pool failure returns HTTP 503; do not treat it as a missing site. This check does not create SIMS identities or bindings and does not adopt an existing SEAD site into SIMS.

---

## Rollback

To return to a known-good image, set `SEAD_AUTHORITY_IMAGE_TAG` in `~/container/.env` to the previous tag, then pull and restart it:

```bash
make pull
make restart
make healthcheck
```

If the health check fails, review `make logs` and the systemd user journal before choosing another image. Keep the previous known-good tag available in GHCR until the new deployment is verified.

---

## Backup and Recovery

The service stores application data in PostgreSQL; the database operations team owns database backup and recovery. Back up the runtime `config/` and `.env` files through the host's approved backup process. The `.env` file contains credentials and must remain protected during backup and restore. Reapply the deployment user's ownership and restrictive permissions before restarting the service.

---

## References

- [deployment/container/README.md](../deployment/container/README.md) — Podman setup, image build, lifecycle, and systemd user service
- [deployment/scripts/sync-to-deploy](../deployment/scripts/sync-to-deploy) — sync the bundle from a development checkout on the deployment host
- [deployment/container/Makefile](../deployment/container/Makefile) — supported deployment commands
- [deployment/container/Makefile.dev](../deployment/container/Makefile.dev) — developer image build and publication commands
- [deployment/container/podman-compose.yml](../deployment/container/podman-compose.yml) — runtime image, mounts, port, and host-gateway mapping
- [deployment/container/service/sead-authority-service.service](../deployment/container/service/sead-authority-service.service) — systemd user unit
- [deployment/container/scripts/build.sh](../deployment/container/scripts/build.sh) — image build helper used by CI and the developer Makefile
- [.github/workflows/build.yml](../.github/workflows/build.yml) — Podman image build and GHCR publication workflow
- [.github/workflows/release.yml](../.github/workflows/release.yml) — source release workflow
