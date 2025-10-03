from typing import Any, Dict

from loguru import logger
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.configuration.inject import ConfigValue
from src.configuration.setup import get_connection
from src.strategies.interface import ReconciliationStrategy, Strategies


async def render_preview(uri: str) -> ValueError | str:
    """Provides a generic HTML preview for a given entity ID."""

    logger.info(f"Rendering preview for URI: {uri}")
    id_base: str = ConfigValue("options:id_base").resolve()
    connection: AsyncConnection = await get_connection()

    if not uri.startswith(id_base):
        raise ValueError("Invalid ID format")

    parts: list[str] = uri.replace(id_base, "").split("/")
    if len(parts) != 2:
        raise ValueError("Invalid ID path")

    entity_path, entity_id_str = parts

    logger.info(f"Entity path: {entity_path}, Entity ID: {entity_id_str}")
    if not Strategies.items.get(entity_path):
        raise ValueError(f"Unknown entity type: {entity_path}")

    strategy: ReconciliationStrategy = Strategies.items.get(entity_path)()

    if not strategy:
        raise ValueError(f"Unknown entity type: {entity_path}")

    async with connection.cursor(row_factory=dict_row) as cur:
        details: Dict[str, Any] | None = await strategy.get_details(entity_id_str, cur)

    if not details:
        raise ValueError(f"Entity with ID {entity_id_str} not found or preview not implemented.")

    # Create a compact, popup-friendly HTML preview
    title = details.get("Name") or details.get("label") or next(iter(details.values()), "Details")
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title} - Preview</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 16px;
            background: #f8f9fa;
            font-size: 14px;
            line-height: 1.5;
        }}
        .preview-container {{
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
            margin: 0 0 16px 0;
            font-size: 20px;
            font-weight: 600;
            color: #1a1a1a;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 12px;
        }}
        .entity-type {{
            display: inline-block;
            background: #e3f2fd;
            color: #1976d2;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
            margin-bottom: 12px;
        }}
        .detail-row {{
            display: flex;
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
        }}
        .detail-row:last-child {{
            border-bottom: none;
        }}
        .detail-label {{
            flex: 0 0 140px;
            font-weight: 600;
            color: #495057;
            font-size: 13px;
        }}
        .detail-value {{
            flex: 1;
            color: #212529;
            word-break: break-word;
        }}
        .uri-link {{
            font-size: 11px;
            color: #6c757d;
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid #e9ecef;
            word-break: break-all;
        }}
        @media (max-width: 640px) {{
            .preview-container {{
                padding: 16px;
            }}
            .detail-row {{
                flex-direction: column;
            }}
            .detail-label {{
                margin-bottom: 4px;
            }}
        }}
    </style>
</head>
<body>
    <div class="preview-container">
        <span class="entity-type">{entity_path.upper()}</span>
        <h1>{title}</h1>
"""
    
    # Add detail rows
    for key, value in details.items():
        if value is not None and str(value).strip() != "" and key not in ["Name", "label"]:
            html += f"""        <div class="detail-row">
            <div class="detail-label">{key}:</div>
            <div class="detail-value">{value}</div>
        </div>
"""
    
    # Add URI at bottom
    html += f"""        <div class="uri-link">
            <strong>URI:</strong> {uri}
        </div>
    </div>
</body>
</html>"""
    
    return html
