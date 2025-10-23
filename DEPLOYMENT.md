# Deployment Guide - SEAD Authority Service

This document provides comprehensive deployment instructions for the SEAD Authority Service, focusing on the CI/CD workflow and production deployment strategies.

## Table of Contents

- [Overview](#overview)
- [CI/CD Pipeline](#cicd-pipeline)
- [Deployment Strategies](#deployment-strategies)
- [Environment Setup](#environment-setup)
- [Release Management](#release-management)
- [Production Deployment](#production-deployment)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)

## Overview

The SEAD Authority Service uses a modern CI/CD pipeline built on GitHub Actions, Docker, and GitHub Container Registry (GHCR). This setup provides:

- **Automated builds** on code changes
- **Multi-architecture support** (amd64, arm64)
- **Version management** through git tags
- **Security attestation** for supply chain integrity
- **Fast deployments** with pre-built images

## CI/CD Pipeline

### Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌────────────┐
│   Git Push  │────>│GitHub Actions│────>│ Docker Build│────>│   GHCR     │
│  or Tag     │     │   Workflow   │     │ Multi-arch  │     │  Registry  │
└─────────────┘     └──────────────┘     └─────────────┘     └────────────┘
                                                │
                                                ▼
                                         ┌─────────────┐
                                         │ Attestation │
                                         │  Generated  │
                                         └─────────────┘
```

### Workflow File

The CI/CD pipeline is defined in `.github/workflows/docker-build.yml`:

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main, dev]
    tags: ['v*']
  pull_request:
    branches: [main, dev]
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
```

### Trigger Events

| Event | Branch/Tag | Action | Image Tags |
|-------|------------|--------|------------|
| Push | `main` | Build & Push | `latest`, `main`, `main-sha-<commit>` |
| Push | `dev` | Build & Push | `dev`, `dev-sha-<commit>` |
| Push | `v1.2.3` | Build & Push | `v1.2.3`, `v1.2`, `v1`, `latest` |
| PR | Any | Build Only | No push |
| Manual | Any | Build & Push | Based on branch |

### Build Process

The workflow performs the following steps:

1. **Checkout Repository** - Pulls the code
2. **Set up Buildx** - Configures Docker multi-platform builds
3. **Login to GHCR** - Authenticates with GitHub Container Registry
4. **Extract Metadata** - Determines appropriate tags
5. **Build & Push** - Builds for amd64 and arm64, pushes to registry
6. **Generate Attestation** - Creates supply chain security attestation

### Image Tagging Strategy

Images are tagged according to the source:

**From main branch:**
```
ghcr.io/humlab-sead/sead_authority_service:latest
ghcr.io/humlab-sead/sead_authority_service:main
ghcr.io/humlab-sead/sead_authority_service:main-sha-abc123
```

**From dev branch:**
```
ghcr.io/humlab-sead/sead_authority_service:dev
ghcr.io/humlab-sead/sead_authority_service:dev-sha-def456
```

**From version tag (v1.2.3):**
```
ghcr.io/humlab-sead/sead_authority_service:v1.2.3
ghcr.io/humlab-sead/sead_authority_service:v1.2
ghcr.io/humlab-sead/sead_authority_service:v1
ghcr.io/humlab-sead/sead_authority_service:latest
```

### Build Optimization

The workflow uses several optimization techniques:

- **Layer Caching**: Uses GitHub Actions cache to speed up builds
- **Multi-stage Build**: Reduces final image size
- **Buildx**: Enables advanced features and multi-platform builds
- **Cache Modes**: `type=gha,mode=max` for optimal caching

## Deployment Strategies

### Strategy 1: Pull Pre-built Images (Recommended for Production)

**Best for:** Production environments, quick deployments

```bash
# On your production server
cd /opt/sead_authority_service/docker

# Pull latest stable version
docker pull ghcr.io/humlab-sead/sead_authority_service:latest

# Or pull specific version
docker pull ghcr.io/humlab-sead/sead_authority_service:v1.0.0

# Start with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

**Advantages:**
- ✅ Fast deployment (no build time)
- ✅ Consistent across environments
- ✅ Tested and verified images
- ✅ Easy rollback to previous versions

### Strategy 2: Local Build

**Best for:** Development, customization

```bash
cd docker
./build.sh --tag custom-v1
docker-compose up
```

**Advantages:**
- ✅ Full control over build process
- ✅ Test local changes
- ✅ Offline capability

### Strategy 3: Build from GitHub Tag

**Best for:** Reproducible builds from specific versions

```bash
cd docker
./build.sh --github-tag v1.0.0
```

**Advantages:**
- ✅ Reproducible builds
- ✅ No local source code needed
- ✅ Build any version from history

### Strategy 4: Automated CI/CD (Recommended Overall)

**Best for:** Continuous deployment workflows

The automated workflow handles everything:
1. Developer pushes code or creates tag
2. GitHub Actions builds automatically
3. Image pushed to GHCR
4. Deploy on server pulls latest image

**Advantages:**
- ✅ Fully automated
- ✅ No manual builds needed
- ✅ Consistent process
- ✅ Audit trail in GitHub

## Environment Setup

### Prerequisites

**On Development Machine:**
- Git
- Docker 20.10+
- Docker Compose 2.0+
- Text editor

**On Production Server:**
- Docker 20.10+
- Docker Compose 2.0+
- Access to GHCR (GitHub Container Registry)
- Secure environment variable management

### GitHub Container Registry Access

#### For Public Images

If your repository is public, anyone can pull images:

```bash
docker pull ghcr.io/humlab-sead/sead_authority_service:latest
```

#### For Private Images

Authenticate with a Personal Access Token (PAT):

```bash
# Create PAT with 'read:packages' scope at:
# https://github.com/settings/tokens

# Login to GHCR
echo $GITHUB_PAT | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# Pull image
docker pull ghcr.io/humlab-sead/sead_authority_service:latest
```

### Environment Variables

Create environment files from templates:

**Development:**
```bash
cd docker
cp .env.example .env
nano .env
```

**Production:**
```bash
cd docker
cp .env.production.example .env.production
nano .env.production
```

**Required Variables:**
```bash
# Database
SEAD_AUTHORITY_OPTIONS_DATABASE_HOST=db.example.com
SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME=sead_staging
SEAD_AUTHORITY_OPTIONS_DATABASE_USER=sead_user
SEAD_AUTHORITY_OPTIONS_DATABASE_PORT=5432

# LLM Provider
OPENAI_API_KEY=sk-...
GEONAMES_USERNAME=your_username

# Optional
OLLAMA_BASE_URL=http://ollama.internal:11434
ANTHROPIC_API_KEY=sk-ant-...
```

## Release Management

### Semantic Versioning

The project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version (v1.0.0 → v2.0.0): Incompatible API changes
- **MINOR** version (v1.0.0 → v1.1.0): New features, backward compatible
- **PATCH** version (v1.0.0 → v1.0.1): Bug fixes, backward compatible

### Creating a Release

#### 1. Prepare Release

```bash
# Ensure you're on main branch and up to date
git checkout main
git pull origin main

# Update version in relevant files (if any)
# Update CHANGELOG.md with changes

# Commit changes
git add .
git commit -m "chore: prepare release v1.0.0"
git push origin main
```

#### 2. Create and Push Tag

```bash
# Create annotated tag
git tag -a v1.0.0 -m "Release version 1.0.0

Features:
- Feature A
- Feature B

Bug Fixes:
- Fix for issue #123
"

# Push tag to trigger CI/CD
git push origin v1.0.0
```

#### 3. Monitor Build

Watch the build progress:
```bash
# Visit GitHub Actions page
https://github.com/humlab-sead/sead_authority_service/actions

# Or use GitHub CLI
gh run watch
```

#### 4. Verify Image

Once build completes:
```bash
# Pull the new image
docker pull ghcr.io/humlab-sead/sead_authority_service:v1.0.0

# Verify it works
docker run --rm ghcr.io/humlab-sead/sead_authority_service:v1.0.0 \
  uvicorn main:app --version
```

#### 5. Create GitHub Release

Create a release on GitHub:
1. Go to `https://github.com/humlab-sead/sead_authority_service/releases/new`
2. Select tag: `v1.0.0`
3. Add release notes
4. Publish release

### Pre-release Versions

For testing before official release:

```bash
# Create pre-release tag
git tag -a v1.0.0-rc1 -m "Release candidate 1 for v1.0.0"
git push origin v1.0.0-rc1

# Image will be tagged as:
# ghcr.io/humlab-sead/sead_authority_service:v1.0.0-rc1
```

### Rollback Strategy

If a release has issues:

```bash
# Option 1: Deploy previous version
docker-compose -f docker-compose.prod.yml pull
docker tag ghcr.io/humlab-sead/sead_authority_service:v0.9.0 \
  ghcr.io/humlab-sead/sead_authority_service:latest
docker-compose -f docker-compose.prod.yml up -d

# Option 2: Delete problematic tag (triggers rebuild)
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0

# Create new corrected version
git tag -a v1.0.1 -m "Hotfix for v1.0.0"
git push origin v1.0.1
```

## Production Deployment

### Initial Setup

#### 1. Prepare Server

```bash
# Install Docker and Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Create application directory
sudo mkdir -p /opt/sead_authority_service
sudo chown $USER:$USER /opt/sead_authority_service
cd /opt/sead_authority_service

# Clone repository (for docker configs)
git clone https://github.com/humlab-sead/sead_authority_service.git .
cd docker
```

#### 2. Configure Environment

```bash
# Create production environment file
cp .env.production.example .env.production

# Edit with secure values
nano .env.production

# Secure the file
chmod 600 .env.production
```

#### 3. Customize Configuration

```bash
# Edit config.yml for production
nano config.yml

# Key changes for production:
# - Set appropriate log levels (INFO or WARNING)
# - Configure log rotation
# - Set resource limits
# - Disable debug features
```

#### 4. Login to GHCR

```bash
# Using Personal Access Token
echo $GITHUB_PAT | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

#### 5. Deploy

```bash
# Pull latest image
docker-compose -f docker-compose.prod.yml pull

# Start service
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

### Zero-Downtime Updates

For production updates without downtime:

```bash
# Pull new image
docker-compose -f docker-compose.prod.yml pull

# Recreate containers with new image
docker-compose -f docker-compose.prod.yml up -d --no-deps --build sead-authority-service

# Old container stops after new one is healthy
```

### Reverse Proxy Setup (Nginx)

```nginx
# /etc/nginx/sites-available/sead-authority-service
server {
    listen 80;
    server_name reconcile.sead.se;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/sead-authority-service \
  /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Add SSL with Let's Encrypt
sudo certbot --nginx -d reconcile.sead.se
```

## Monitoring and Maintenance

### Health Checks

The container includes built-in health checks:

```bash
# Check health status
docker inspect sead-authority-service | grep -A 10 Health

# Manual health check
curl http://localhost:8000/is_alive
```

### Log Management

View logs:
```bash
# Live logs
docker-compose -f docker-compose.prod.yml logs -f

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100

# Logs from mounted volume
tail -f /opt/sead_authority_service/docker/logs/sead_authority.log
```

Configure log rotation in `config.yml`:
```yaml
logging:
  handlers:
    - sink: "sead_authority.log"
      rotation: "10 MB"
      retention: "30 days"
      compression: "zip"
```

### Monitoring

#### Prometheus Metrics (Optional)

Add metrics endpoint:
```python
# Install prometheus_client
pip install prometheus-client

# In main.py
from prometheus_client import make_asgi_app

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

#### Resource Usage

Monitor container resources:
```bash
# Real-time stats
docker stats sead-authority-service

# Historical usage
docker logs sead-authority-service 2>&1 | grep -i memory
```

### Backup Strategy

#### Configuration Backup

```bash
# Backup configuration
tar -czf backup-$(date +%Y%m%d).tar.gz \
  docker/.env.production \
  docker/config.yml \
  docker/logs/*.log

# Store securely off-site
```

#### Database Backup

```bash
# If using containerized PostgreSQL
docker-compose exec postgres pg_dump -U sead_user sead_db > backup.sql

# Restore
docker-compose exec -T postgres psql -U sead_user sead_db < backup.sql
```

## Troubleshooting

### Build Failures

**Problem:** GitHub Actions build fails

**Solutions:**
```bash
# Check workflow logs
gh run view --log

# Re-run failed jobs
gh run rerun <run-id>

# Test build locally
docker build -f docker/Dockerfile -t test .
```

### Image Pull Failures

**Problem:** Cannot pull from GHCR

**Solutions:**
```bash
# Verify authentication
docker logout ghcr.io
echo $GITHUB_PAT | docker login ghcr.io -u USERNAME --password-stdin

# Check PAT permissions (needs read:packages)
# Verify image exists
docker manifest inspect ghcr.io/humlab-sead/sead_authority_service:latest
```

### Container Startup Failures

**Problem:** Container exits immediately

**Solutions:**
```bash
# Check logs
docker-compose logs sead-authority-service

# Common issues:
# 1. Database connection - verify credentials in .env
# 2. Missing config.yml - ensure file exists and is mounted
# 3. Port conflict - check if port 8000 is already used

# Debug interactively
docker run -it --rm \
  -v $(pwd)/config.yml:/app/config/config.yml \
  --env-file .env \
  ghcr.io/humlab-sead/sead_authority_service:latest \
  /bin/bash
```

### Performance Issues

**Problem:** Slow response times

**Solutions:**
```bash
# Increase workers in docker-compose.yml
command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Increase resources
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G

# Check database connection pool settings
# Monitor with docker stats
```

## Security Best Practices

1. **Use Specific Version Tags** in production, not `latest`
2. **Secure Environment Variables** - Use secrets management
3. **Regular Updates** - Update images for security patches
4. **Scan Images** - Use `docker scan` or Trivy
5. **Minimize Privileges** - Container runs as non-root
6. **Network Isolation** - Use Docker networks
7. **Read-only Mounts** - Config files mounted as read-only
8. **Log Sensitive Data** - Audit logs for secrets

## Additional Resources

- [Docker Documentation](docker/README.md)
- [Quick Start Guide](docker/QUICKSTART.md)
- [GitHub Actions Workflow](.github/workflows/docker-build.yml)
- [Docker Compose Files](docker/)
- [OpenRefine Integration](README.md#openrefine-integration)

## Support

- **Issues**: https://github.com/humlab-sead/sead_authority_service/issues
- **Discussions**: https://github.com/humlab-sead/sead_authority_service/discussions
- **Security**: Report security issues privately to the maintainers
