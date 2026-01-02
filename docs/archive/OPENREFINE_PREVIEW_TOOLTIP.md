# OpenRefine Preview: Tooltip vs New Tab

## Current Behavior

When you click on a reconciliation candidate in OpenRefine, the preview opens in a **new browser tab** rather than showing as an inline tooltip/popup. This is the **expected behavior** for OpenRefine's Reconciliation API.

## Why Not a Tooltip?

The OpenRefine Reconciliation API specification uses the `view.url` field to provide a link that opens in a new window/tab. OpenRefine does not support inline tooltip previews through the standard Reconciliation API.

### Current Implementation

```json
{
  "view": {
    "url": "http://localhost:8001/reconcile/preview?id={{id}}"
  }
}
```

This tells OpenRefine: "When the user clicks to preview an entity, open this URL in a new tab."

## How to Get Inline Tooltips

To get inline tooltip-style previews in OpenRefine, you need to implement the **Suggest API** (also called the **Flyout API**), which is a separate specification from the Reconciliation API.

### Suggest API Overview

The Suggest API provides:
- **Autocomplete/type-ahead** suggestions as users type
- **Inline preview flyouts** that appear on hover (tooltip-style)
- Property and type suggestions

### Required Endpoints for Suggest API

To implement inline tooltips, you would need these additional endpoints:

1. **Entity Suggest** (autocomplete)
   ```
   GET /suggest/entity?prefix=<query>&type=<type>
   ```
   Returns entity suggestions as the user types.

2. **Flyout/Preview** (inline tooltip)
   ```
   GET /flyout/entity?id=<id>
   ```
   Returns HTML for the inline preview popup (shown on hover).

3. **Type Suggest** (optional)
   ```
   GET /suggest/type?prefix=<query>
   ```
   Returns entity type suggestions.

4. **Property Suggest** (optional)
   ```
   GET /suggest/property?prefix=<query>&type=<type>
   ```
   Returns property suggestions.

### Metadata Configuration for Suggest API

You would update your metadata to include:

```json
{
  "name": "SEAD Entity Reconciliation",
  "identifierSpace": "https://w3id.org/sead/id/",
  "view": {
    "url": "http://localhost:8001/reconcile/preview?id={{id}}"
  },
  "suggest": {
    "entity": {
      "service_url": "http://localhost:8001/suggest",
      "service_path": "/entity"
    },
    "type": {
      "service_url": "http://localhost:8001/suggest",
      "service_path": "/type"
    },
    "property": {
      "service_url": "http://localhost:8001/suggest",
      "service_path": "/property"
    }
  },
  "preview": {
    "url": "http://localhost:8001/flyout/entity?id={{id}}",
    "width": 400,
    "height": 300
  }
}
```

The `preview.url` endpoint (flyout) provides the inline tooltip content.

### Example Flyout Response

```json
{
  "id": "https://w3id.org/sead/id/location/4196",
  "html": "<div style='padding:10px'>
    <h3>Stockholm</h3>
    <p><strong>Type:</strong> Settlement</p>
    <p><strong>Description:</strong> Capital city of Sweden</p>
    <p><strong>Coordinates:</strong> 59.3293° N, 18.0686° E</p>
  </div>"
}
```

## Current Workarounds

Since implementing the full Suggest API is significant work, here are alternative approaches:

### 1. Improved Preview Page (✅ Implemented)

We've improved the preview page to be:
- **Compact and readable** - Clean, modern design
- **Popup-friendly** - Works well when opened in new tab
- **Mobile-responsive** - Adapts to small screens
- **Fast loading** - Minimal HTML with embedded CSS

The preview now includes:
- Entity type badge
- Clean header with title
- Organized detail rows
- Full URI at bottom
- Professional styling

### 2. Use Target="_blank" Behavior

Users can:
- **Middle-click** (scroll wheel click) to open in background tab
- **Ctrl+Click** (Cmd+Click on Mac) to open in background tab
- Keep the preview tab open and switch back to it

### 3. Browser Extensions

Some browser extensions can modify link behavior to show previews in popups rather than new tabs.

### 4. OpenRefine Workflows

Recommended workflow:
1. Reconcile your column
2. Click preview links for ambiguous matches
3. Keep preview tab open
4. Switch between tabs using **Ctrl+Tab** / **Ctrl+Shift+Tab**

## Future Enhancement: Implement Suggest API

If you want inline tooltip previews, the implementation plan would be:

### Phase 1: Flyout Endpoint (Inline Tooltips)
```python
@router.get("/flyout/entity")
async def flyout_entity(id: str) -> JSONResponse:
    """Return compact HTML for inline preview flyout"""
    # Reuse existing preview logic but return JSON with HTML
    html = await render_preview_compact(id)
    return JSONResponse({
        "id": id,
        "html": html
    })
```

### Phase 2: Entity Suggest (Autocomplete)
```python
@router.get("/suggest/entity")
async def suggest_entity(prefix: str, type: str = "") -> JSONResponse:
    """Return entity suggestions as user types"""
    # Search entities matching prefix
    results = await search_entities(prefix, type, limit=10)
    return JSONResponse({
        "result": [
            {
                "id": entity["id"],
                "name": entity["name"],
                "type": [{"id": type, "name": type}],
                "description": entity.get("description", "")
            }
            for entity in results
        ]
    })
```

### Phase 3: Update Metadata
Add `suggest` and `preview` sections to reconciliation metadata.

### Estimated Effort
- **Flyout endpoint**: 2-4 hours
- **Entity suggest**: 4-8 hours (needs efficient search)
- **Type/Property suggest**: 2-4 hours each
- **Testing & documentation**: 2-4 hours
- **Total**: 10-20 hours

## References

- [OpenRefine Reconciliation API Specification](https://reconciliation-api.github.io/specs/latest/)
- [OpenRefine Suggest API Specification](https://github.com/OpenRefine/OpenRefine/wiki/Suggest-API)
- [OpenRefine Preview/Flyout Documentation](https://github.com/OpenRefine/OpenRefine/wiki/Reconciliation-Service-API#preview-api)

## Current Status

✅ **Reconciliation API**: Fully implemented  
✅ **Property Suggestions**: Working  
✅ **Preview (new tab)**: Working with improved styling  
⬜ **Suggest API**: Not implemented  
⬜ **Flyout/Inline Preview**: Not implemented  

## Recommendation

For most use cases, the current **preview in new tab** approach is sufficient and follows the standard OpenRefine workflow. The improved preview page makes this experience better.

If inline tooltips are critical for your workflow, implementing the Suggest API would be the next step.
