# SEAD Authority Service - Docker Deployment Guide

## Overview

This directory contains Docker configuration files for deploying the SEAD Authority Service. Multiple deployment strategies are supported.

## Deployment Options

### Option 1: Local Build (Development)
Build the Docker image locally from your source code.

```bash
cd docker
docker-compose up --build
```

### Option 2: Build from GitHub (Specific Version)
Build from a specific GitHub tag/branch.

```bash
docker build -f docker/Dockerfile.github \
  --build-arg GIT_TAG=v0.1.0 \
  -t sead-authority-service:v0.1.0 \
  .
```

### Option 3: Use Pre-built Image from GHCR (Production)
Use images built and pushed by GitHub Actions CI/CD.

```bash
cd docker
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### Option 4: GitHub Actions CI/CD (Automated)
The `.github/workflows/docker-build.yml` workflow automatically:
- Builds on push to `main` or `dev` branches
- Builds on version tags (`v*`)
- Pushes to GitHub Container Registry (GHCR)
- Supports multi-architecture builds (amd64, arm64)

## Directory Structure

```
docker/
├── Dockerfile                 # Main Dockerfile (local build)
├── Dockerfile.github          # Build from GitHub release
├── docker-compose.yml         # Development compose file
├── docker-compose.prod.yml    # Production compose file
├── config.yml                 # Configuration template
├── .env.example              # Environment variables template
├── .env.production.example   # Production environment template
├── logs/                     # Log files (mounted volume)
└── data/                     # Data files (mounted volume)
```

## Configuration

### 1. Environment Variables

Copy the example environment file and configure:

```bash
cp .env.example .env
# Edit .env with your actual values
```

Required variables:
- `SEAD_AUTHORITY_OPTIONS_DATABASE_HOST` - Database hostname
- `SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME` - Database name
- `SEAD_AUTHORITY_OPTIONS_DATABASE_USER` - Database user
- `SEAD_AUTHORITY_OPTIONS_DATABASE_PORT` - Database port
- `OPENAI_API_KEY` - OpenAI API key (if using OpenAI)
- `GEONAMES_USERNAME` - GeoNames username

### 2. Configuration File

The `config.yml` file is mounted from the host. Customize it for your deployment:

```bash
# Edit config.yml with your settings
nano config.yml
```

Key sections:
- `options.database` - Database connection settings
- `llm` - LLM provider configuration
- `policy` - Strategy-specific policies
- `logging` - Log configuration

## Usage

### Development Deployment

```bash
# 1. Navigate to docker directory
cd docker

# 2. Copy and configure environment
cp .env.example .env
# Edit .env with your values

# 3. Build and start services
docker-compose up --build

# 4. Access the service
curl http://localhost:8000/is_alive
```

### Production Deployment

```bash
# 1. Navigate to docker directory
cd docker

# 2. Configure production environment
cp .env.production.example .env.production
# Edit .env.production with your production values

# 3. Pull latest image from GHCR
docker-compose -f docker-compose.prod.yml pull

# 4. Start services
docker-compose -f docker-compose.prod.yml up -d

# 5. Check logs
docker-compose -f docker-compose.prod.yml logs -f

# 6. Check health
curl http://localhost:8000/is_alive
```

### Build from Specific GitHub Tag

```bash
# Build from a specific release
docker build \
  -f docker/Dockerfile.github \
  --build-arg GIT_TAG=v0.1.0 \
  -t sead-authority-service:v0.1.0 \
  ..

# Run the built image
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/config.yml:/app/config/config.yml:ro \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  sead-authority-service:v0.1.0
```

## Container Management

### View Logs
```bash
docker-compose logs -f
docker-compose logs -f sead-authority-service
```

### Restart Service
```bash
docker-compose restart sead-authority-service
```

### Stop Service
```bash
docker-compose down
```

### Update Service (Production)
```bash
# Pull latest image
docker-compose -f docker-compose.prod.yml pull

# Recreate containers with new image
docker-compose -f docker-compose.prod.yml up -d
```

## Health Checks

The container includes a health check that monitors:
- HTTP endpoint `/is_alive`
- Interval: 30 seconds
- Timeout: 10 seconds
- Retries: 3

Check health status:
```bash
docker ps
docker inspect sead-authority-service | grep Health -A 5
```

## Volumes

### Mounted Volumes

1. **Configuration** (`./config.yml:/app/config/config.yml:ro`)
   - Read-only mount of configuration file
   - Changes require container restart

2. **Logs** (`./logs:/app/logs`)
   - Application log files
   - Rotated automatically (10MB, 30 days retention)

3. **Data** (`./data:/app/data`)
   - Optional data files (e.g., CSV files for import)

## Networking

Default configuration:
- Container port: 8000
- Host port: 8000 (configurable in docker-compose.yml)
- Network: `sead-network` (bridge driver)

## Security Considerations

1. **Non-root User**: Container runs as `appuser` (non-root)
2. **Read-only Config**: Configuration file mounted as read-only
3. **Environment Variables**: Sensitive data in `.env` (not committed)
4. **Resource Limits**: CPU and memory limits defined in compose files
5. **Health Checks**: Automatic monitoring and restart on failure

## Troubleshooting

### Container Won't Start

Check logs:
```bash
docker-compose logs sead-authority-service
```

Common issues:
- Database connection failed → Check database credentials in `.env`
- Config file not found → Ensure `config.yml` exists in docker directory
- Port already in use → Change port mapping in `docker-compose.yml`

### Database Connection Issues

Test database connectivity:
```bash
docker-compose exec sead-authority-service \
  curl -v telnet://your-db-host:5432
```

### API Not Responding

Check if service is running:
```bash
docker ps
docker-compose ps
```

Test health endpoint:
```bash
curl http://localhost:8000/is_alive
```

### View Application Logs

```bash
# Live logs
docker-compose logs -f sead-authority-service

# Last 100 lines
docker-compose logs --tail=100 sead-authority-service

# Logs from host volume
tail -f logs/sead_authority.log
```

## GitHub Container Registry (GHCR)

### Pulling Images

Images are automatically built and pushed to GHCR by GitHub Actions.

```bash
# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull specific version
docker pull ghcr.io/humlab-sead/sead_authority_service:v0.1.0

# Pull latest
docker pull ghcr.io/humlab-sead/sead_authority_service:latest

# Pull development version
docker pull ghcr.io/humlab-sead/sead_authority_service:dev
```

### Available Tags

- `latest` - Latest stable release from main branch
- `dev` - Latest development version from dev branch
- `v*` - Specific version tags (e.g., `v0.1.0`)
- `main-sha-*` - Specific commit from main branch
- `dev-sha-*` - Specific commit from dev branch

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/docker-build.yml`) automatically:

1. **Triggers on**:
   - Push to `main` or `dev` branches
   - Version tags (`v*`)
   - Pull requests (build only, no push)
   - Manual workflow dispatch

2. **Build Process**:
   - Multi-stage build for optimized image size
   - Multi-architecture support (amd64, arm64)
   - Layer caching for faster builds

3. **Publish**:
   - Push to GHCR with multiple tags
   - Generate attestation for supply chain security

## Performance Tuning

### Resource Limits

Adjust in `docker-compose.yml` or `docker-compose.prod.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G
    reservations:
      cpus: '1'
      memory: 1G
```

### Uvicorn Configuration

Customize in docker-compose command:

```yaml
command: >
  uvicorn main:app
  --host 0.0.0.0
  --port 8000
  --workers 4
  --log-level info
```

## Production Checklist

- [ ] Configure `.env.production` with production credentials
- [ ] Update `config.yml` for production settings
- [ ] Set appropriate resource limits
- [ ] Configure log rotation and retention
- [ ] Set up monitoring and alerting
- [ ] Configure backup for logs and data volumes
- [ ] Test health checks and auto-restart
- [ ] Review security settings (non-root user, read-only mounts)
- [ ] Set up reverse proxy (nginx, traefik) if needed
- [ ] Configure SSL/TLS certificates
- [ ] Set up monitoring (Prometheus, Grafana)

## Support

For issues or questions:
- GitHub Issues: https://github.com/humlab-sead/sead_authority_service/issues
- Documentation: See main README.md
