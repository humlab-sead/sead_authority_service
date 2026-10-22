# SEAD Authority Service — Rootless Podman Deployment

This bundle runs the SEAD Authority Service with rootless Podman. It preserves
the existing runtime settings: the GHCR image and tag convention, `.env`
inputs, the read-only `config/` mount, the writable `logs/` mount, host
port `8024`, and the `/is_alive` health endpoint.

Image publication is automated for `staging` and release tags, and manual
development builds remain available from the checkout. Pushes to `staging`
publish the `staging` tag; a semantic-release release on `main` publishes the
release tag and `latest`. The GitHub Actions workflow
(`.github/workflows/build.yml`) uses Podman for both jobs.

## Requirements

- Linux host with Podman (validated with 5.7.0) and podman-compose (validated with 1.5.0).
- One rootless deployment user. Do not run these commands as root.
- No Docker is needed or used.

## Layout

The deployment runtime lives in `~/container` for the deployment user:

```text
~/container/
├── .env                  # runtime settings and credentials (never tracked)
├── .env.example          # runtime settings template
├── podman-compose.yml    # service definition
├── Makefile              # runtime and lifecycle commands
├── service/              # systemd user unit source
├── config/               # mounted read-only at /app/config
└── logs/                 # mounted read-write at /app/logs
```

The runtime bundle contains no image build tools. `make setup` copies only
runtime files and creates `.env` and `config/` from the tracked templates.
Edit `~/container/.env` with the target host's own values before starting the
service. Keep credentials out of tracked files.

## First-time setup

For a deployment account that can read the checkout, initialize its runtime
directory with `make setup` from `deployment/container/`. When the deployment
account should not access the checkout, run this from the developer checkout
root instead; the first sync creates `.env` and `config/` from templates if
they are missing:

```bash
deployment/scripts/sync-to-deploy authority-service.sead.se
```

Then edit `~/container/.env` as the deployment user.

Key `.env` settings:

| Variable | Purpose | Default |
|---|---|---|
| `SEAD_AUTHORITY_ENVIRONMENT` | Runtime environment: `dev`, `staging`, `production` | `staging` |
| `SEAD_AUTHORITY_IMAGE_TAG` | Published image tag to pull and run | `staging` |
| `SEAD_AUTHORITY_PORT` | Host port published to container port 8000 | `8024` |
| `SEAD_AUTHORITY_CONTAINER_UID` / `SEAD_AUTHORITY_CONTAINER_GID` | Numeric user and group for the container process; set these to the deployment account's `id -u` and `id -g` so it can read private config files and write logs | `1000` / `1000` |
| `SEAD_AUTHORITY_OPTIONS_DATABASE_*` | Database connection | — |
| `LLM_PROVIDER`, `OPENAI_*`, `OLLAMA_*` | LLM provider selection and keys | — |

The sample settings use the published `staging` tag. Set
`SEAD_AUTHORITY_IMAGE_TAG` to the published tag you intend to deploy. For
example, production from `main` uses `latest`.

## Sync files from a development checkout

To update an existing deployment bundle from a development checkout on the
deployment host, run the sync helper from the checkout root as a developer
account with passwordless `sudo` access to the deployment account:

```bash
deployment/scripts/sync-to-deploy authority-service.sead.se --dry-run
deployment/scripts/sync-to-deploy authority-service.sead.se
```

The helper copies runtime files from `deployment/container/` into the
deployment user's `~/container`, removes obsolete bundle files, and preserves
the target `.env`, `config/`, and `logs/`. On first sync it creates missing
`.env` and `config/` from templates. It installs the systemd user unit for the
default `container` directory and reloads the user manager when it is running.
It does not enable or restart the service or pull a new image. Use the
lifecycle steps below after syncing if the deployment should run a new image.

For an isolated bundle such as `container-dev`, use:

```bash
deployment/scripts/sync-to-deploy authority-service.sead.se --remote-dir container-dev
```

This does not install or reload the systemd user unit. The helper runs local
`sudo` on the current host and does not use SSH. On first sync to this
non-default directory, it creates `.env` from `.env.dev.example`. Pass
`DEPLOY_DIR=~/container-dev` to runtime Makefile commands for this directory,
for example `make pull DEPLOY_DIR=~/container-dev`.

### Separate staging instance on the same host

Run a second staging instance as a separate rootless deployment user, such as
`test-authority-service.sead.se`. Use that account's own `~/container`, set
`SEAD_AUTHORITY_ENVIRONMENT=staging` and
`SEAD_AUTHORITY_IMAGE_TAG=staging`, and provide staging database credentials
and config. Set the container UID/GID to that account's IDs and choose a free
host port distinct from the other instances. Then follow the setup, pull,
lifecycle, and boot steps below. See the
[Operations Guide](../../docs/OPERATIONS.md) for the same-host port rule.

## Pull or build the image

### Pull a published image on the deployment account

```bash
cd ~/container
make pull             # pulls SEAD_AUTHORITY_IMAGE_TAG from .env
```

The deployment account does not need the `Containerfile` or image build
script. It needs access to pull the selected GHCR image.

### Build or publish a development image from the checkout

Builds run from the developer checkout and use a separate `~/container-dev`
directory with defaults from `.env.dev.example`:

```bash
cd deployment/container
make -f Makefile.dev setup
# Edit ~/container-dev/.env with development database and provider settings.
# Set container UID/GID to the developer account's IDs.
make -f Makefile.dev build
podman login ghcr.io -u USERNAME
make -f Makefile.dev push
```

`Makefile.dev` includes the runtime `Makefile` and adds `build` and `push`.
Those targets default to the `dev` ref and a `dev`-prefixed tag; set
`DEV_IMAGE_TAG=dev-name` to choose another development tag, for example
`make -f Makefile.dev push DEV_IMAGE_TAG=dev-name`. They refuse tags that do
not start with `dev`. The builder always uses the selected GitHub ref, not
uncommitted source from the checkout.

The developer Makefile's `service-install` and `service-enable` targets use a
separate `sead-authority-service-dev` unit for `~/container-dev`.

The GitHub Actions workflow remains the build and publication path for
`staging` and release tags. Use the developer Makefile for development images
or local image checks.

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
cd ~/container
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

## GitHub Actions image publication

The workflow `.github/workflows/build.yml` runs tests and lint, then
builds with Podman and publishes to GHCR:

| Trigger | Environment | Tags |
|---|---|---|
| Push to `staging` | `staging` | `staging` |
| Release on `main` | `production` | the release tag (`vX.Y.Z`) and `latest` |
| Manual `workflow_dispatch` | chosen input | chosen comma-separated tags |

The release path is a `workflow_call` from `.github/workflows/release.yml`, so
the image is built from the exact commit that semantic-release tagged. A push
to `main` that produces no release publishes no image. The workflow must stay
within GitHub's free allowances. Limits checked on 2026-10-11:

- Standard GitHub-hosted runners are free for public repositories; larger
  runners are billed.
- GitHub Free includes 500 MB of Actions artifact storage and 10 GB of cache
  per repository.
- Public GHCR packages are free.

Publish images directly to GHCR, do not store image archives as Actions
artifacts, keep any caches and artifacts within the limits above, and set
retention or cleanup. Recheck the current rules before changing the workflow:

- [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [Actions limits](https://docs.github.com/en/actions/reference/limits)
- [GitHub Packages billing](https://docs.github.com/en/billing/concepts/product-billing/github-packages)
