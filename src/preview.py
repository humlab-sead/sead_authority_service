from typing import Any, Dict

from loguru import logger
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.configuration.inject import ConfigValue
from src.configuration.setup import get_connection
from src.strategies.strategy import ReconciliationStrategy, Strategies


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
    <title>{title} – Preview</title>
    <style>
        /* Compact styles for a ~400x300 iframe */
        :root {{
            --pad: 10px;
            --gap: 6px;
            --font: 12px;
            --label-w: 120px;
        }}
        html, body {{
            height: 100%;
            margin: 0;
            background: #f8f9fa;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            font-size: var(--font);
            line-height: 1.4;
            color: #1a1a1a;
        }}
        .preview {{
            height: 100%;
            padding: var(--pad);
            box-sizing: border-box;
        }}
        .card {{
            height: 100%;
            background: #fff;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            box-shadow: 0 1px 4px rgba(0,0,0,.06);
            padding: var(--pad);
            box-sizing: border-box;

            display: grid;
            grid-template-rows: auto auto 1fr auto;
            row-gap: var(--gap);
        }}
        .pill {{
            display: inline-block;
            font-size: 11px;
            font-weight: 600;
            color: #1976d2;
            background: #e3f2fd;
            border: 1px solid #d7e9fb;
            padding: 2px 8px;
            border-radius: 999px;
            max-width: 100%;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        h1 {{
            margin: 2px 0 0 0;
            font-size: 15px;
            line-height: 1.25;
            font-weight: 700;
            color: #1a1a1a;

            /* Clamp to two lines in small space */
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .details {{
            overflow: auto;                 /* allow scrolling in 300px height */
            padding-top: var(--gap);
            border-top: 1px solid #f0f0f0;
        }}
        .row {{
            display: grid;
            grid-template-columns: minmax(80px, var(--label-w)) 1fr;
            column-gap: 8px;
            padding: 6px 0;
            border-bottom: 1px solid #f7f7f7;
        }}
        .row:last-child {{ border-bottom: 0; }}
        .label {{
            color: #495057;
            font-weight: 600;
            font-size: 11px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .value {{
            color: #212529;
            word-break: break-word;
        }}
        .uri {{
            border-top: 1px solid #e9ecef;
            padding-top: 8px;
            margin-top: 6px;
            font-size: 10px;
            color: #6c757d;
            word-break: break-all;
            max-height: 38px;               /* avoid growing too tall */
            overflow: hidden;
        }}
        /* Smallest safety */
        @media (max-width: 420px) {{
            :root {{ --label-w: 100px; }}
        }}
    </style>
    </head>
    <body>
    <div class="preview">
        <div class="card">
        <span class="pill">{entity_path.upper()}</span>
        <h1>{title}</h1>
        <div class="details">
    """
    # detail rows
    for key, value in details.items():
        if value is not None and str(value).strip() != "" and key not in ["Name", "label"]:
            html += f"""        <div class="row">
            <div class="label">{key}:</div>
            <div class="value">{value}</div>
            </div>
    """

    # URI
    html += f"""      </div>
        <div class="uri"><strong>URI:</strong> {uri}</div>
        </div>
    </div>
    </body>
    </html>"""

    return html
