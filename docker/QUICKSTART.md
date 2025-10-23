# Quick Start Guide - Docker Deployment

## Prerequisites
- Docker 20.10 or later
- Docker Compose 2.0 or later
- Access to SEAD database
- OpenAI API key (or Ollama/Anthropic credentials)
- GeoNames account

## Quick Start (Development)

```bash
# 1. Navigate to docker directory
cd docker

# 2. Create environment file from template
cp .env.example .env

# 3. Edit .env with your credentials
nano .env
# Set at minimum:
#   - SEAD_AUTHORITY_OPTIONS_DATABASE_HOST
#   - SEAD_AUTHORITY_OPTIONS_DATABASE_USER
#   - SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME
#   - OPENAI_API_KEY
#   - GEONAMES_USERNAME

# 4. Review and customize config.yml if needed
nano config.yml

# 5. Build and start the service
docker-compose up --build

# 6. Test the service (in another terminal)
curl http://localhost:8000/is_alive
```

The service will be available at http://localhost:8000

## Quick Start (Production with GHCR)

```bash
# 1. Navigate to docker directory
cd docker

# 2. Create production environment file
cp .env.production.example .env.production

# 3. Edit .env.production with production credentials
nano .env.production

# 4. Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# 5. Pull and start the service
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# 6. Check logs
docker-compose -f docker-compose.prod.yml logs -f

# 7. Verify service is running
curl http://localhost:8000/is_alive
```

## Testing the Service

### Health Check
```bash
curl http://localhost:8000/is_alive
```

Expected response:
```json
{"status": "alive"}
```

### Test Reconciliation
```bash
curl -X GET "http://localhost:8000/reconcile"
```

Expected: OpenRefine service manifest in JSON format

### Test with OpenRefine
1. Open OpenRefine
2. Start to Reconcile a column
3. Click "Add Standard Service"
4. Enter: `http://localhost:8000/reconcile`
5. Select the service and reconcile

## Common Commands

### View logs
```bash
docker-compose logs -f
```

### Restart service
```bash
docker-compose restart
```

### Stop service
```bash
docker-compose down
```

### Update to latest version
```bash
docker-compose pull
docker-compose up -d
```

### Rebuild after code changes
```bash
docker-compose up --build
```

## Troubleshooting

### Service won't start
```bash
# Check logs
docker-compose logs sead-authority-service

# Common issues:
# - Database connection: Check credentials in .env
# - Port conflict: Change port in docker-compose.yml
# - Config file missing: Ensure config.yml exists
```

### Database connection failed
```bash
# Test database connectivity
docker-compose exec sead-authority-service ping -c 3 your-db-host

# Check database credentials in .env file
```

### Need to reset everything
```bash
docker-compose down -v
docker-compose up --build
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Configure LLM providers in `config.yml`
- Set up monitoring and logging
- Configure reverse proxy for HTTPS
- Set up automated backups

## Support

For issues: https://github.com/humlab-sead/sead_authority_service/issues
