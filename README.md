# SEAD Authority Service

[![semantic-release: angular](https://img.shields.io/badge/semantic--release-angular-e10079?logo=semantic-release)](https://github.com/semantic-release/semantic-release)

A FastAPI-based reconciliation service for SEAD (Strategic Environmental Archaeology Database) entities, providing OpenRefine-compatible reconciliation endpoints for archaeological and environmental data.

## Features

- **Entity Reconciliation**: Support for sites and taxonomic entities
- **OpenRefine Integration**: Full compatibility with OpenRefine reconciliation protocol
- **Fuzzy Matching**: Advanced text matching with similarity scoring
- **Geographic Queries**: Location-based search capabilities
- **Property-based Filtering**: Enhanced reconciliation using entity properties

## Quick Start

### Prerequisites

- Python 3.13+
- UV package manager
- PostgreSQL database with SEAD data

### Installation

```bash
git clone <repository-url>
cd sead_authority_service
uv install
```

### Configuration

Copy the configuration template and adjust database settings:

```bash
cp config/config.yml.template config/config.yml
# Edit config/config.yml with your database credentials
```

### Running the Service

```bash
# Development mode with auto-reload
make serve

# Or manually
uv run uvicorn main:app --reload
```

The service will be available at `http://localhost:8000`

## OpenRefine Integration

### Adding the Service to OpenRefine

1. **Open OpenRefine** and go to your project
2. **Click on the dropdown arrow** next to a column you want to reconcile
3. **Select "Reconcile" → "Start reconciling..."**
4. **Click "Add Standard Service"**
5. **Enter the service URL:** `http://localhost:8000/reconcile`
6. **Click "Add Service"**

### Service URL

```
http://localhost:8000/reconcile
```

### Available Entity Types

The service supports reconciliation for these entity types:

- **site** - Archaeological/geographic sites and locations
- **taxon** - Taxonomic entities (species, genera, etc.)

### Enhanced Properties

When reconciling, you can use additional properties to improve matching accuracy:

#### Site Properties
- `latitude` - Decimal latitude coordinate
- `longitude` - Decimal longitude coordinate  
- `country` - Country name
- `region` - Administrative region
- `elevation` - Elevation in meters

#### Taxon Properties
- `kingdom` - Taxonomic kingdom
- `phylum` - Taxonomic phylum
- `class` - Taxonomic class
- `order` - Taxonomic order
- `family` - Taxonomic family

### API Endpoints

- **Service Metadata**: `GET /reconcile` - Returns service information and available entity types
- **Reconciliation**: `POST /reconcile` - Performs entity reconciliation queries
- **Properties**: `GET /reconcile/properties` - Returns available properties for entity types
- **Preview**: `GET /reconcile/preview` - Returns entity preview information

### Example Usage

1. **Start the service**:
   ```bash
   make serve
   ```

2. **In OpenRefine**, add the service URL: `http://localhost:8000/reconcile`

3. **Select your entity type** (site or taxon) when configuring reconciliation

4. **Add property constraints** if available to improve matching accuracy

## Development

### Running Tests

```bash
make test
```

### Code Quality

```bash
make lint
make format
```

### Project Structure

```
src/
├── api/           # FastAPI routes and endpoints
├── configuration/ # Configuration management
├── strategies/    # Entity-specific reconciliation strategies
└── utility/       # Helper functions and utilities
```

## Configuration

The service uses YAML configuration files. Key settings:

```yaml
options:
  database:
    host: localhost
    port: 5432
    database: sead_db
    username: your_user
    password: your_password
  
  default_query_limit: 10
  id_base: "https://w3id.org/sead/id/"
```

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation.

## Deployment

### Docker Deployment

The service includes comprehensive Docker support with multiple deployment strategies. All Docker-related files are in the `docker/` directory.

#### Quick Start with Docker

**Development:**
```bash
cd docker
cp .env.example .env
# Edit .env with your credentials
docker-compose up --build
```

**Production:**
```bash
cd docker
cp .env.production.example .env.production
# Edit .env.production with your credentials
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

See [docker/QUICKSTART.md](docker/QUICKSTART.md) for detailed quick start instructions.

### CI/CD Pipeline

The project uses GitHub Actions for automated Docker image builds and deployment.

#### How It Works

1. **Automated Builds**: On every push to `main` or `dev` branches, or when creating version tags
2. **Multi-Architecture**: Builds for both `linux/amd64` and `linux/arm64`
3. **Container Registry**: Images published to GitHub Container Registry (GHCR)
4. **Version Tags**: Automatic tagging based on git tags and branches

#### Workflow Triggers

The GitHub Actions workflow (`.github/workflows/docker-build.yml`) is triggered by:

- **Push to main/dev**: Builds and pushes with `latest` or `dev` tag
- **Version tags**: Push tags like `v1.0.0` to build versioned images
- **Pull requests**: Builds image for testing (doesn't push)
- **Manual dispatch**: Trigger builds manually from GitHub UI

#### Image Tags

Images are available at `ghcr.io/humlab-sead/sead_authority_service` with these tags:

- `latest` - Latest stable release from main branch
- `dev` - Latest development version from dev branch
- `v*` - Specific version tags (e.g., `v0.1.0`, `v1.2.3`)
- `main-sha-<commit>` - Specific commit from main branch
- `dev-sha-<commit>` - Specific commit from dev branch

#### Using Pre-built Images

```bash
# Pull latest stable version
docker pull ghcr.io/humlab-sead/sead_authority_service:latest

# Pull specific version
docker pull ghcr.io/humlab-sead/sead_authority_service:v0.1.0

# Pull development version
docker pull ghcr.io/humlab-sead/sead_authority_service:dev

# Run the image
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/docker/config.yml:/app/config/config.yml:ro \
  -v $(pwd)/docker/logs:/app/logs \
  --env-file docker/.env \
  ghcr.io/humlab-sead/sead_authority_service:latest
```

#### Creating a Release

To create a new release and trigger automated builds:

```bash
# Create and push a version tag
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0

# GitHub Actions will:
# 1. Build the Docker image
# 2. Tag it as v0.1.0, v0.1, v0, and latest
# 3. Push to ghcr.io/humlab-sead/sead_authority_service
# 4. Generate build attestation for security
```

#### Deployment Workflow

**For development:**
```bash
# Automatic on every push to dev branch
git checkout dev
git push origin dev
# Image built and tagged as 'dev'
```

**For production:**
```bash
# 1. Create release tag
git tag v1.0.0
git push origin v1.0.0

# 2. GitHub Actions builds and pushes automatically

# 3. Deploy on server
cd docker
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

#### Build Process

The CI/CD pipeline uses a multi-stage Docker build:

1. **Builder Stage**: Installs dependencies and builds application
2. **Runtime Stage**: Minimal runtime image with only necessary components
3. **Security**: Runs as non-root user, includes health checks
4. **Optimization**: Layer caching for faster builds, minimal image size

#### Monitoring Builds

- **GitHub Actions**: View build status at `https://github.com/humlab-sead/sead_authority_service/actions`
- **Container Registry**: View published images at `https://github.com/humlab-sead/sead_authority_service/pkgs/container/sead_authority_service`

### Deployment Options

The service supports multiple deployment strategies:

1. **Local Build** - Build Docker image from local source code
   - Best for: Development and testing
   - See: `docker/Dockerfile`

2. **GitHub Build** - Build from specific GitHub tag/branch
   - Best for: Reproducible builds from releases
   - See: `docker/Dockerfile.github`

3. **Pre-built Images** - Use images from GHCR
   - Best for: Production deployments
   - See: `docker/docker-compose.prod.yml`

4. **CI/CD Pipeline** - Automated builds via GitHub Actions (Recommended)
   - Best for: Continuous deployment
   - See: `.github/workflows/docker-build.yml`

### Configuration

The Docker deployment uses environment variables for configuration:

```bash
# Required environment variables
SEAD_AUTHORITY_OPTIONS_DATABASE_HOST=your-db-host
SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME=sead_staging
SEAD_AUTHORITY_OPTIONS_DATABASE_USER=your-db-user
SEAD_AUTHORITY_OPTIONS_DATABASE_PORT=5432

OPENAI_API_KEY=your-openai-key
GEONAMES_USERNAME=your-geonames-username
```

Configuration file (`config.yml`) is mounted from the host as a read-only volume for security and easy updates without rebuilding images.

### Production Deployment Checklist

- [ ] Configure production environment variables in `docker/.env.production`
- [ ] Review and customize `docker/config.yml` for production settings
- [ ] Set up reverse proxy (nginx/traefik) for HTTPS
- [ ] Configure log rotation and monitoring
- [ ] Set up automated backups for logs and data
- [ ] Configure resource limits in docker-compose
- [ ] Set up monitoring and alerting (Prometheus, Grafana)
- [ ] Review security settings (firewall, access controls)
- [ ] Test health checks and auto-restart behavior
- [ ] Configure SSL/TLS certificates

### Documentation

For detailed deployment information, see:

- [docker/README.md](docker/README.md) - Comprehensive deployment guide
- [docker/QUICKSTART.md](docker/QUICKSTART.md) - Quick start guide
- [.github/workflows/docker-build.yml](.github/workflows/docker-build.yml) - CI/CD workflow definition

## License

[Add your license information here]
