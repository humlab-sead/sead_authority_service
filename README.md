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

## License

[Add your license information here]
