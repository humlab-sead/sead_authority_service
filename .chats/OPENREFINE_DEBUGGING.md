# OpenRefine Integration Debugging Guide

## Quick Diagnosis Checklist

### 1. Service Discovery (Metadata Endpoint)
Test the metadata endpoint to ensure OpenRefine can discover your service:

```bash
curl -s http://localhost:8001/reconcile | python3 -m json.tool
```

**Expected Response Structure:**
```json
{
  "name": "SEAD Entity Reconciliation",
  "identifierSpace": "https://w3id.org/sead/id/",
  "schemaSpace": "http://www.w3.org/2004/02/skos/core#",
  "defaultTypes": [
    {"id": "location", "name": "location"},
    {"id": "site", "name": "site"},
    {"id": "taxon", "name": "taxon"}
  ],
  "view": {
    "url": "http://localhost:8001/reconcile/preview?id={{id}}"
  },
  "extend": {
    "propose_properties": {
      "service_url": "http://localhost:8001/reconcile",
      "service_path": "/properties"
    },
    "property_settings": [...]
  }
}
```

**Common Issues:**
- ✅ `view.url` must use `{{id}}` (double braces) for OpenRefine template substitution
- ✅ `service_url` must NOT have double slashes (`//reconcile`)
- ✅ `defaultTypes` ids must match your registered strategy keys

### 2. Property Suggestions
Test the properties endpoint:

```bash
# Get all properties
curl -s "http://localhost:8001/reconcile/properties" | python3 -m json.tool

# Get properties for a specific entity type
curl -s "http://localhost:8001/reconcile/properties?type=site" | python3 -m json.tool

# Search properties
curl -s "http://localhost:8001/reconcile/properties?query=latitude" | python3 -m json.tool
```

**Expected Response:**
```json
{
  "properties": [
    {
      "id": "latitude",
      "name": "Latitude",
      "type": "number",
      "description": "Geographic latitude in decimal degrees (WGS84)"
    },
    ...
  ]
}
```

**Common Issues:**
- ✅ Response must have `"properties"` wrapper
- ✅ Each property needs `id`, `name`, `type`, and `description` fields
- ✅ The `type` field is the **data type** (string/number/date), NOT the entity type

### 3. Entity Preview
Test the preview endpoint with a real entity ID:

```bash
# First, get a real ID from reconciliation
curl -s -X POST "http://localhost:8001/reconcile" \
  -H "Content-Type: application/json" \
  -d '{"queries": {"q0": {"query": "Stockholm", "type": "location"}}}' \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['q0']['result'][0]['id'] if d.get('q0', {}).get('result') else 'No results')"

# Then test preview with that ID
curl -s "http://localhost:8001/reconcile/preview?id=https://w3id.org/sead/id/location/4196"
```

**Expected Response:**
HTML content displaying entity details.

**Common Issues:**
- ✅ Preview URL in metadata must match actual preview endpoint path
- ✅ Entity IDs returned in reconciliation must match the format preview endpoint expects
- ✅ The `id` parameter must be the **full URI**, not just the numeric ID
- ✅ Preview endpoint must accept IDs that start with `identifierSpace`

### 4. Reconciliation Query
Test actual reconciliation:

```bash
curl -s -X POST "http://localhost:8001/reconcile" \
  -H "Content-Type: application/json" \
  -d '{
    "queries": {
      "q0": {
        "query": "Stockholm",
        "type": "location"
      }
    }
  }' | python3 -m json.tool
```

**Expected Response:**
```json
{
  "q0": {
    "result": [
      {
        "id": "https://w3id.org/sead/id/location/4196",
        "name": "Stockholm",
        "score": 100.0,
        "match": true,
        "type": [{"id": "location", "name": "Stockholm"}]
      }
    ]
  }
}
```

## OpenRefine Setup

### Adding the Service in OpenRefine

1. Open OpenRefine and load your project
2. Click the dropdown arrow next to the column you want to reconcile
3. Select **"Reconcile" → "Start reconciling..."**
4. Click **"Add Standard Service"**
5. Enter the service URL: `http://localhost:8001/reconcile`
6. Click **"Add Service"**

### Verifying It Works

After adding the service, you should see:
- ✅ "SEAD Entity Reconciliation" in the service list
- ✅ Entity types (location, site, taxon) in the dropdown
- ✅ Property suggestions when you click "Add property" (if configured)
- ✅ Preview popup when hovering over matched candidates

### Common OpenRefine Issues

**Properties Not Showing:**
- Check browser console (F12) for CORS errors
- Verify `/reconcile/properties?type=<entity>` returns results
- Ensure `extend.propose_properties` is correctly configured in metadata

**Preview Not Working:**
- Check that `view.url` in metadata uses `{{id}}` template
- Verify preview endpoint returns HTML (not JSON)
- Check browser console for 400/500 errors
- Ensure IDs in reconciliation results match identifierSpace + entity path

**Service Not Found:**
- Ensure server is running and accessible from the machine running OpenRefine
- Check CORS is enabled (your app has `CORSMiddleware` with `allow_origins=["*"]`)
- Test metadata endpoint from browser: `http://localhost:8001/reconcile`

## Server Logs

Monitor server logs in real-time to see requests from OpenRefine:

```bash
# If running with make serve:
tail -f server.log

# If running in background:
tail -f /tmp/sead_server.log
```

Look for:
- GET `/reconcile` - metadata discovery
- GET `/reconcile/properties` - property suggestions
- POST `/reconcile` - reconciliation queries  
- GET `/reconcile/preview` - entity previews

## Testing from REST Client (VS Code)

Use the test file `tests/test.rest` to test all endpoints:

1. Open `tests/test.rest` in VS Code
2. Install "REST Client" extension if not already installed
3. Click "Send Request" above any `###` line
4. Check responses match expected formats

## Troubleshooting Steps

1. **Start fresh:**
   ```bash
   pkill -f uvicorn
   make serve
   ```

2. **Test metadata endpoint** - should return JSON with proper structure
3. **Test properties endpoint** - should return properties list
4. **Test a simple reconciliation** - should return candidates with full URIs as IDs
5. **Test preview with a real ID** - should return HTML
6. **Try in OpenRefine** - add service and test reconciliation

## Current Known Working Configuration

- **Service URL**: `http://localhost:8001/reconcile`
- **Entity Types**: location, site, taxon
- **Sample Working IDs**:
  - Location: `https://w3id.org/sead/id/location/4196` (Stockholm)
  - Site: `https://w3id.org/sead/id/site/<site_id>`
  - Taxon: `https://w3id.org/sead/id/taxon/<taxon_id>`

## Contact & Support

If issues persist after following this guide:
1. Check server logs for errors
2. Test each endpoint individually with curl
3. Verify CORS is enabled
4. Ensure database connection is working
