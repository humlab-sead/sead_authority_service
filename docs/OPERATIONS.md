# SEAD Authority Service - Operations Guide

Runbook for operators and maintainers of deployed SEAD Authority Service environments.

---

## Environments

| Environment | Purpose | Branch | Port |
|-------------|---------|--------|------|
| Production | Live service on `sead-tools` | `main` | 8000 |
| Staging | Pre-release validation | `dev` or feature | 8000 |
| Development | Local developer instances | any | 8000 |

Production and staging run on `humlabseadserv.srv.its.umu.se`. The canonical deploy directory is `docker/production/` (or `docker/staging/`).

---

## Operational Assumptions and Invariants

- **Stateless per request.** There is no in-process cache or session store. Multiple Uvicorn workers may be used.
- **Non-root container user.** The container runs as a non-root user. Host volume mounts must be writable by that user.
- **No built-in TLS.** TLS termination is expected upstream (reverse proxy). The container exposes plain HTTP on port 8000.
- **SIMS co-located.** The identity module (`src/identity/`) runs inside this service; there is no separate SIMS deployment.
- **PostgreSQL extensions required.** `pg_trgm` must be available. `pgvector` and PostGIS are needed for semantic search and geographic proximity features respectively; without them those strategy features are unavailable.
- **LLM provider required for RAG strategies.** Strategies that use LLM validation fail at runtime without a configured and reachable provider.

---

## Configuration and Secrets

### Runtime environment variables

All runtime settings are loaded from `.env` (or `.env.staging`) via `env_file` in `docker-compose.yml`.

| Variable | Purpose |
|----------|---------|
| `CONFIG_FILE` | Path to mounted config file (default `/app/config/config.yml`) |
| `SEAD_AUTHORITY_ENVIRONMENT` | Environment name (`staging`, `production`) |
| `SEAD_AUTHORITY_OPTIONS_DATABASE_HOST` | PostgreSQL host |
| `SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME` | Database name |
| `SEAD_AUTHORITY_OPTIONS_DATABASE_USER` | Database user |
| `SEAD_AUTHORITY_OPTIONS_DATABASE_PORT` | PostgreSQL port |
| `LLM_PROVIDER` | Active LLM provider (`openai`, `anthropic`, `ollama`) |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | OpenAI credentials and model |
| `ANTHROPIC_API_KEY` | Anthropic credentials |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | Ollama endpoint and model |
| `GEONAMES_USERNAME` | GeoNames API credentials |

Secrets (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, database password) must not be committed to version control. Use `.env` files excluded by `.gitignore`.

### Configuration file

`config/config.yml` is mounted read-only into the container at `/app/config/config.yml`. `entities.yml` and `prompts.yml` are included via `@include` directives in `config.yml` and must be co-located or referenced with correct paths.

---

## Data Layout

Persistent data is mounted from the deploy directory on the host into `/app/` in the container:

| Host path | Container path | Contents |
|-----------|---------------|---------|
| `./config.yml` | `/app/config/config.yml:ro` | Runtime configuration |
| `/var/log/sead-authority/` | `/app/logs/` | Application log files |
| `./data/` | `/app/data/:ro` | Shared reference data |

Create log directories before first startup:

```bash
sudo mkdir -p /var/log/sead-authority
```

---

## Build Artifacts

The build produces a single Docker image pushed to GHCR:

```
ghcr.io/humlab-sead/sead_authority_service:<tag>
```

The `Dockerfile` is a multi-stage build:

1. **Builder stage**: installs system build dependencies, optionally clones from GitHub (`FROM_GITHUB=true --build-arg GIT_TAG=...`) or uses local context.
2. **Runtime stage**: Python slim image, non-root user, `uvicorn` entrypoint on port 8000.

Build supports both local source and GitHub clone:

```bash
# From local source
docker build -f docker/Dockerfile -t sead-authority-service .

# From a specific GitHub tag
docker build -f docker/Dockerfile \
  --build-arg FROM_GITHUB=true \
  --build-arg GIT_TAG=v1.0.0 \
  -t sead-authority-service .
```

---

## Deployment Flow

Production deployments use the pre-built GHCR image via `docker/production/docker-compose.yml`.

### Initial setup

```bash
# On the deploy host
cd docker/production
cp .env.example .env      # fill in credentials
chmod 600 .env
sudo mkdir -p /var/log/sead-authority
```

### Deploy or update

```bash
cd docker/production

# Pull latest image from GHCR
docker compose pull

# Restart with new image
docker compose up -d --force-recreate
```

To deploy a specific tag:

```bash
# Edit docker-compose.yml: image: ghcr.io/humlab-sead/sead_authority_service:v1.2.3
docker compose up -d --force-recreate
```

### Authenticate with GHCR (if image is private)

```bash
echo $GITHUB_PAT | docker login ghcr.io -u <github-username> --password-stdin
```

---

## CI Pipeline

Defined in `.github/workflows/docker-build.yml`. Triggers on push to `main` and `workflow_dispatch`.

Steps:
1. Checkout repository.
2. Run `uv run pytest` (full test suite) and `uv run ruff check`.
3. Build multi-architecture Docker image (`linux/amd64`, `linux/arm64`).
4. Push to GHCR with computed tags.
5. Generate supply chain attestation.

**The image is only pushed if tests pass.**

| Trigger | Tags applied |
|---------|-------------|
| Push to `main` | `latest`, `main`, `main-sha-<commit>` |
| Push tag `v1.2.3` | `v1.2.3`, `v1.2`, `v1`, `latest` |
| `workflow_dispatch` | Based on branch |
| Pull request | Build only, no push |

---

## CD Triggers and Release Process

There is no automated continuous deployment. The release process is:

1. Merge PRs into `dev`, then merge `dev` → `main`.
2. **`release.yml`** runs `semantic-release` on push to `main`: analyses conventional commits, bumps version, updates `CHANGELOG.md`, creates a GitHub Release, and tags the commit.
3. **`docker-build.yml`** triggers on the same push, builds the image, and pushes it tagged with the new version.
4. An operator deploys by pulling the new tag on the deploy host (see Deployment Flow).

---

## Post-Deployment Verification

```bash
# Health check
curl -sf http://localhost:8000/is_alive

# Check container is running
docker compose -f docker/production/docker-compose.yml ps

# Tail recent logs
docker compose -f docker/production/docker-compose.yml logs -f --tail 50
```

Smoke-check reconciliation:

```bash
curl -s "http://localhost:8000/reconcile?queries=%7B%22q0%22%3A%7B%22query%22%3A%22test%22%7D%7D"
```

---

## Rollback

The container is stateless (all config in mounted files and env vars). To roll back:

1. Identify the last known-good image tag (e.g., `v1.1.0` or `main-sha-abc123`).
2. Update `image:` in `docker-compose.yml` to pin the previous tag.
3. Restart:

```bash
docker compose up -d --force-recreate
```

4. Verify with the health check above.

---

## Health Checks and Observability

### Health endpoint

```
GET /is_alive
```

Returns HTTP 200 when the application is running and the DB connection pool is active.

### Logs

Loguru writes logs to `/app/logs/` (mounted to `/var/log/sead-authority/` on the host). The container also emits logs to stdout (captured by Docker's `json-file` driver with `max-size: 10m`, `max-file: 3`).

```bash
# Live log stream
docker compose logs -f

# Host log directory
tail -f /var/log/sead-authority/sead_authority.log
```

Log level is controlled by `logging.level` in `config/config.yml`.

### Alerting

TBD — no alerting infrastructure is currently configured.

---

## Backup and Recovery

The service holds no application state beyond what is in PostgreSQL and the mounted config files. Database backups are the responsibility of the SEAD database operations team and are outside the scope of this service.

Config file backup:

```bash
cp docker/production/config.yml /backup/$(date +%Y%m%d)-config.yml
cp docker/production/.env       /backup/$(date +%Y%m%d)-.env
```

---

## References

- [docker/README.md](../docker/README.md) — Docker setup, volume layout, and compose files
- [docker/QUICKSTART.md](../docker/QUICKSTART.md) — Quick start for first-time deployment
- [.github/workflows/docker-build.yml](../.github/workflows/docker-build.yml) — CI build and push workflow
- [.github/workflows/release.yml](../.github/workflows/release.yml) — Semantic release workflow
- [docs/DEVELOPMENT.md](DEVELOPMENT.md) — Local development setup and contributor workflow
- [docs/DESIGN.md](DESIGN.md) — Architecture and system constraints
