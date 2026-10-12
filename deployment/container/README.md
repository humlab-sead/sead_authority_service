# SEAD Authority Service — Rootless Podman Deployment

This bundle runs the SEAD Authority Service with rootless Podman. It preserves
the existing runtime settings: the GHCR image and tag convention, `.env`
inputs, the read-only `config/` mount, the writable `logs/` mount, host
port `8024`, and the `/is_alive` health endpoint.

Image publishing stays manual. The GitHub Actions image workflow
(`.github/workflows/docker-build.yml`) remains disabled. Its existing filename
is retained for compatibility; both jobs use Podman.

## Requirements

- Linux host with Podman (validated with 5.7.0) and podman-compose (validated with 1.5.0).
- One rootless deployment user. Do not run these commands as root.
- No Docker is needed or used.

## Layout

The deployment runtime lives in `~/container` for the deployment user:

```text
~/container/
├── .env                  # runtime settings and credentials (never tracked)
├── podman-compose.yml    # service definition
├── Containerfile         # image definition (used by scripts/build.sh)
├── Makefile              # lifecycle commands
├── scripts/build.sh      # manual image build/push
├── config/               # mounted read-only at /app/config
└── logs/                 # mounted read-write at /app/logs
```

`make setup` copies the bundle files there and creates `.env` and `config/`
from the tracked templates. Edit `~/container/.env` with the target host's own
values before starting the service. Keep credentials out of tracked files.

## First-time setup

```bash
cd deployment/container
make setup            # creates ~/container with .env and config/ from templates
vi ~/container/.env   # set database, LLM provider, and port values
```

Key `.env` settings:

| Variable | Purpose | Default |
|---|---|---|
| `SEAD_AUTHORITY_ENVIRONMENT` | Build target: `dev`, `staging`, `production` | `staging` |
| `SEAD_AUTHORITY_GIT_REF` | Branch or tag the image is built from | `main` |
| `SEAD_AUTHORITY_IMAGE_TAG` | Image tag to build, pull, and run | `staging` |
| `SEAD_AUTHORITY_PORT` | Host port published to container port 8000 | `8024` |
| `SEAD_AUTHORITY_CONTAINER_UID` / `SEAD_AUTHORITY_CONTAINER_GID` | Numeric user and group for the container process; set these to the deployment account's `id -u` and `id -g` so it can read private config files and write logs | `1000` / `1000` |
| `SEAD_AUTHORITY_OPTIONS_DATABASE_*` | Database connection | — |
| `LLM_PROVIDER`, `OPENAI_*`, `OLLAMA_*` | LLM provider selection and keys | — |

The sample settings use the `staging` tag for build, pull, and run. If you
change the build target or Git ref, set `SEAD_AUTHORITY_IMAGE_TAG` to the tag
you intend to deploy. For example, production from `main` uses `latest`.

### Separate staging instance on the same host

Run a second staging instance as a separate rootless deployment user, such as
`test-authority-service.sead.se`. Use that account's own `~/container`, set
`SEAD_AUTHORITY_ENVIRONMENT=staging` and
`SEAD_AUTHORITY_IMAGE_TAG=staging`, and provide staging database credentials
and config. Set the container UID/GID to that account's IDs and choose a free
host port distinct from the other instances. Then follow the setup, build or
pull, lifecycle, and boot steps below. See the
[Operations Guide](../../docs/OPERATIONS.md) for the same-host port rule.

## Build or pull the image

Build from the selected GitHub ref (the `.env` values above drive a
no-argument build; the build never uses the local worktree):

```bash
cd ~/container
make build            # scripts/build.sh, no push
```

Or build with explicit options:

```bash
./scripts/build.sh --git-ref dev --target-env dev --tag dev
./scripts/build.sh --git-ref main --target-env staging --tag staging
./scripts/build.sh --git-ref v1.2.0 --target-env production --tag v1.2.0 --push
```

If no tag is set in the environment or `.env`, the helper derives tags using
the established mapping:

- `--target-env dev` produces `:dev`
- `--target-env staging` produces `:staging`
- `--target-env production` with `--git-ref main` produces `:latest`
- `--target-env production` with a version ref such as `v1.2.0` produces that version tag
- Other production refs produce a sanitized branch tag; `--tag` overrides

Push only when requested and authenticated:

```bash
echo $GITHUB_TOKEN | podman login ghcr.io -u USERNAME --password-stdin
make push
```

Or skip the build and pull a published tag:

```bash
make pull             # pulls the SEAD_AUTHORITY_IMAGE_TAG value (staging in the sample .env)
```

## Lifecycle

From `~/container`:

```bash
make up               # start (podman-compose up -d)
make down             # stop
make restart          # restart
make logs             # follow logs
make status           # container status
make config           # render the resolved compose configuration
make healthcheck      # curl /is_alive on the host port
```

Health check by hand:

```bash
curl http://localhost:8024/is_alive
# {"status":"alive"}
```

Logs are also on the host at `~/container/logs/`.

## Start on host boot

Install and enable the systemd user unit, then enable lingering so the user
service runs without an active login session:

```bash
cd deployment/container
make service-install  # copies the unit and reloads the user manager
make service-enable   # loginctl enable-linger + systemctl --user enable --now
```

Check it:

```bash
systemctl --user status sead-authority-service
journalctl --user -u sead-authority-service
```

The unit runs `podman-compose up -d` from `~/container`, the same project the
Makefile controls.

## GitHub Actions image workflow (disabled)

Image builds and pushes stay manual. The workflow file
`.github/workflows/docker-build.yml` keeps its existing filename for
compatibility. Its disabled build job uses the Podman build helper and Podman
push command. Both workflow jobs
remain guarded by `if: false`, so it does not build or publish images. If the
workflow is ever re-enabled, it must stay within GitHub's free allowances.
Limits checked on 2026-10-11:

- Standard GitHub-hosted runners are free for public repositories; larger
  runners are billed.
- GitHub Free includes 500 MB of Actions artifact storage and 10 GB of cache
  per repository.
- Public GHCR packages are free.

Publish images directly to GHCR, do not store image archives as Actions
artifacts, keep any caches and artifacts within the limits above, and set
retention or cleanup. Recheck the current rules before enabling or changing
the workflow:

- [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [Actions limits](https://docs.github.com/en/actions/reference/limits)
- [GitHub Packages billing](https://docs.github.com/en/billing/concepts/product-billing/github-packages)
