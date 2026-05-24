# SEAD Authority Service Docker Assets

This directory only contains the Docker build inputs for `sead_authority_service`.

## What is authoritative

- `docker/Dockerfile`: image definition used for both manual builds and the disabled GHCR workflow.
- `docker/build.sh`: manual replacement for the disabled GHCR workflow.
- `docker/.env.example`: single runtime environment template for deployments.
- `docker/config/`: tracked, sanitized config template copied from the deployment config directory.
- `sead-tools/sead_authority_service/docker-compose.yml`: the single deployment compose file.
- `sead-tools/sead_authority_service/.env`: target-environment settings for that deployment.
- `sead-tools/sead_authority_service/config/`: mounted runtime configuration.

The GitHub Actions Docker workflow is intentionally disabled. For now, image releases are handled manually.

## Build the image

Build the same image artifact name used by the disabled GitHub Actions workflow.

```bash
./docker/build.sh --git-ref dev --target-env dev
```

Build and push a staging image manually:

```bash
./docker/build.sh --git-ref main --target-env staging --push
```

The resulting image name is always `ghcr.io/humlab-sead/sead_authority_service:<tag>`.

Default tag selection is deployment-oriented:

- `--target-env dev` produces `:dev`
- `--target-env staging` produces `:staging`
- `--target-env prod` produces `:latest` for `--git-ref main`
- `--target-env prod` produces the release tag itself for version refs such as `v1.2.0`

Use `--tag` when you need to override the derived tag explicitly.

Smoke-test examples:

```bash
# Development image -> ghcr.io/humlab-sead/sead_authority_service:dev
./docker/build.sh --git-ref dev --target-env dev

# Staging image -> ghcr.io/humlab-sead/sead_authority_service:staging
./docker/build.sh --git-ref main --target-env staging

# Production release image -> ghcr.io/humlab-sead/sead_authority_service:v1.2.0
./docker/build.sh --git-ref v1.2.0 --target-env prod
```

## Run the staging deployment

The deployment compose file lives in `sead-tools/sead_authority_service` and reads its environment from the local `.env` file in that directory.

Start from `docker/.env.example` when you need to create or refresh a target deployment `.env` file.
Start from `docker/config/` when you need to create or refresh the mounted runtime config directory.
Build or pull the target image first; the compose file is runtime-only and does not build images.

```bash
cd sead-tools/sead_authority_service
docker compose up -d
```

The service mounts:

- `./config` to `/app/config`
- `./logs` to `/app/logs`

The default published port is `8024`, or `SEAD_AUTHORITY_PORT` if it is set in the deployment environment.

## Health check

```bash
curl http://localhost:8024/is_alive
```

If you change credentials or runtime config, restart the compose project from `sead-tools/sead_authority_service`.

```bash
# Live logs
docker-compose logs -f sead-authority-service

# Last 100 lines
docker-compose logs --tail=100 sead-authority-service

# Logs from host volume
tail -f logs/sead_authority.log
```

## GitHub Container Registry (GHCR)

Images are released manually for now. Pull tags that match the target environment or release version.

```bash
# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull specific version
docker pull ghcr.io/humlab-sead/sead_authority_service:v0.1.0

# Pull latest
docker pull ghcr.io/humlab-sead/sead_authority_service:latest

# Pull development version
docker pull ghcr.io/humlab-sead/sead_authority_service:dev

# Pull staging version
docker pull ghcr.io/humlab-sead/sead_authority_service:staging
```

Available tags:

- `dev`
- `staging`
- `latest`
- release tags such as `v0.1.0`

## Support

For issues or questions:
- GitHub Issues: https://github.com/humlab-sead/sead_authority_service/issues
- Documentation: See main README.md
