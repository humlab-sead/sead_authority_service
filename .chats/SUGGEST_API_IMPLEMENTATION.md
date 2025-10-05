# OpenRefine Suggest API Implementation

## Overview

The OpenRefine Suggest API has been successfully implemented to provide inline tooltip previews and autocomplete functionality in OpenRefine. This eliminates the need for opening entity previews in new browser tabs and provides a more seamless user experience.

## Implementation Status

✅ **COMPLETE** - All Suggest API endpoints implemented and tested

## What Changed

### 1. New Module: `src/suggest.py`

Created a new module containing all Suggest API functionality:

- **`render_flyout_preview(uri: str)`** - Generates compact HTML previews for inline tooltips
- **`suggest_entities(prefix: str, entity_type: str, limit: int)`** - Entity autocomplete search
- **`suggest_types(prefix: str)`** - Entity type filtering
- **`suggest_properties(prefix: str, entity_type: str)`** - Property filtering

### 2. Updated Router: `src/api/router.py`

Added four new API endpoints:

```python
GET /suggest/entity?prefix=<query>&type=<type>
GET /suggest/type?prefix=<query>
GET /suggest/property?prefix=<query>&type=<type>
GET /flyout/entity?id=<entity_uri>
```

### 3. Enhanced Metadata: `src/metadata.py`

Updated `get_reconciliation_metadata()` to include Suggest API configuration:

```json
{
  "suggest": {
    "entity": {
      "service_url": "http://localhost:8001",
      "service_path": "/suggest/entity",
      "flyout_service_url": "http://localhost:8001",
      "flyout_service_path": "/flyout/entity?id=${{id}}"
    },
    "type": {
      "service_url": "http://localhost:8001",
      "service_path": "/suggest/type"
    },
    "property": {
      "service_url": "http://localhost:8001",
      "service_path": "/suggest/property"
    }
  },
  "preview": {
    "url": "http://localhost:8001/reconcile/preview?id={{id}}",
    "width": 400,
    "height": 300
  }
}
```

### 4. Comprehensive Tests: `tests/test_suggest.py`

Created 12 test cases covering:
- Entity suggestions with prefix
- Entity suggestions with type filter
- Type suggestions with and without prefix
- Property suggestions by type and prefix
- Flyout HTML generation
- Metadata configuration validation
- Error handling

All tests pass ✅

## API Endpoints

### 1. Entity Autocomplete

**Endpoint:** `GET /suggest/entity`

**Parameters:**
- `prefix` (required, min 2 chars) - Text to search for
- `type` (optional) - Filter by entity type (site, location, taxon)

**Example:**
```bash
curl "http://localhost:8001/suggest/entity?prefix=upp"
```

**Response:**
```json
{
  "result": [
    {
      "id": "https://w3id.org/sead/id/location/806",
      "name": "Uppland",
      "type": [{"id": "location", "name": "location"}],
      "description": "",
      "score": 0.333
    }
  ]
}
```

### 2. Type Autocomplete

**Endpoint:** `GET /suggest/type`

**Parameters:**
- `prefix` (optional) - Filter types by prefix

**Example:**
```bash
curl "http://localhost:8001/suggest/type?prefix=loc"
```

**Response:**
```json
{
  "result": [
    {"id": "location", "name": "Location"}
  ]
}
```

### 3. Property Autocomplete

**Endpoint:** `GET /suggest/property`

**Parameters:**
- `prefix` (optional) - Filter properties by name/description
- `type` (optional) - Filter by entity type

**Example:**
```bash
curl "http://localhost:8001/suggest/property?type=site"
```

**Response:**
```json
{
  "result": [
    {
      "id": "latitude",
      "name": "Latitude",
      "description": "Geographic latitude in decimal degrees (WGS84)"
    },
    {
      "id": "longitude",
      "name": "Longitude",
      "description": "Geographic longitude in decimal degrees (WGS84)"
    }
  ]
}
```

### 4. Flyout Preview

**Endpoint:** `GET /flyout/entity`

**Parameters:**
- `id` (required) - Entity URI to preview

**Example:**
```bash
curl "http://localhost:8001/flyout/entity?id=https://w3id.org/sead/id/location/806"
```

**Response:**
```json
{
  "id": "https://w3id.org/sead/id/location/806",
  "html": "<div style=\"padding:12px; font-family:sans-serif; font-size:13px; line-height:1.4; max-width:350px;\">...</div>"
}
```

The HTML is compact and optimized for tooltip display with:
- Entity name as title
- Entity type badge
- Key properties (limited to 5 most important)
- Truncated long values (max 100 chars)
- Inline CSS styling

## How It Works

### OpenRefine Integration

When you configure OpenRefine to use this reconciliation service:

1. **Service Discovery**: OpenRefine queries `GET /reconcile` and receives metadata including the `suggest` configuration
2. **Autocomplete**: As you type in reconciliation dialogs, OpenRefine calls `/suggest/entity?prefix=<text>` to show suggestions
3. **Hover Preview**: When hovering over a suggestion, OpenRefine calls `/flyout/entity?id=<uri>` and displays the HTML in an inline tooltip
4. **Type Filtering**: Type selection dropdowns use `/suggest/type`
5. **Property Selection**: Property dropdowns use `/suggest/property`

### User Experience

**Before (Standard Reconciliation API):**
- Click entity → Opens new browser tab
- Must switch windows to see preview
- No autocomplete suggestions

**After (With Suggest API):**
- Type entity name → See autocomplete suggestions instantly
- Hover over suggestion → See inline tooltip preview
- Click suggestion → Apply without leaving OpenRefine
- Seamless, fast workflow

## Testing

### Manual Testing

Start the server:
```bash
cd /home/roger/source/sead_authority_service
uv run uvicorn main:app --reload --port 8001
```

Test the endpoints:
```bash
# Check metadata includes suggest config
curl -s "http://localhost:8001/reconcile" | jq '.suggest'

# Test entity suggestions
curl -s "http://localhost:8001/suggest/entity?prefix=upp" | jq '.'

# Test type suggestions
curl -s "http://localhost:8001/suggest/type" | jq '.'

# Test property suggestions
curl -s "http://localhost:8001/suggest/property?type=site" | jq '.result[0:3]'

# Test flyout preview
curl -s "http://localhost:8001/flyout/entity?id=https://w3id.org/sead/id/location/806" | jq '.'
```

### Automated Testing

Run the test suite:
```bash
uv run pytest tests/test_suggest.py -v
```

All 12 tests pass ✅

## OpenRefine Configuration

To use the Suggest API in OpenRefine:

1. Start the reconciliation service
2. In OpenRefine, select a column to reconcile
3. Click "Reconcile" → "Start reconciling..."
4. Add service URL: `http://localhost:8001/reconcile`
5. OpenRefine will automatically detect and use the Suggest API

You'll now see:
- Autocomplete suggestions as you type
- Inline tooltip previews on hover
- Type and property suggestions in dropdowns

## Technical Details

### Entity Search Strategy

The `suggest_entities()` function:
1. Requires minimum 2-character prefix to avoid overwhelming results
2. Queries registered strategies (site, location, taxon)
3. Uses existing `find_candidates()` method for consistency
4. Limits results to 10 matches
5. Sorts by relevance score
6. Returns results in OpenRefine-compatible format

### Flyout HTML Generation

The `render_flyout_preview()` function:
1. Validates entity URI format
2. Uses strategy pattern to fetch entity details
3. Generates compact HTML with inline CSS
4. Limits to 5 most important properties
5. Truncates long values (max 100 chars)
6. Includes entity type badge
7. Optimized for tooltip display (max 350px width)

### Type and Property Suggestions

- **Type suggestions**: Returns all registered entity types from `Strategies.items`
- **Property suggestions**: Aggregates properties from strategies, filters by prefix and type
- Both support prefix filtering for autocomplete functionality

## Performance Considerations

- Minimum prefix length (2 chars) prevents excessive queries
- Result limits (10 for entities, 5 for properties in flyout)
- Reuses existing database queries and connection pooling
- Compact HTML minimizes payload size
- Efficient filtering with lowercase comparison

## Future Enhancements

Possible improvements:
1. **Caching**: Cache type/property lists (they rarely change)
2. **Fuzzy matching**: Implement fuzzy string matching for better suggestions
3. **Highlighting**: Add query term highlighting in suggestions
4. **Images**: Include entity images in flyout previews if available
5. **Scoring improvements**: Better relevance scoring for entity suggestions
6. **Pagination**: Support for loading more suggestions beyond limit

## References

- [OpenRefine Reconciliation API Specification](https://reconciliation-api.github.io/specs/latest/)
- [OpenRefine Suggest API Documentation](https://reconciliation-api.github.io/specs/latest/#suggest-services)
- Implementation files:
  - `/src/suggest.py` - Suggest API implementation
  - `/src/api/router.py` - API endpoints
  - `/src/metadata.py` - Metadata configuration
  - `/tests/test_suggest.py` - Test suite

## Summary

The OpenRefine Suggest API implementation is **complete and fully tested**. All four required endpoints are working correctly:

✅ Entity autocomplete  
✅ Type suggestions  
✅ Property suggestions  
✅ Inline flyout previews  

OpenRefine users can now enjoy a seamless reconciliation experience with autocomplete and tooltip previews instead of opening new browser tabs.
