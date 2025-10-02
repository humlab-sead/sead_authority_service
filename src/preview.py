from typing import Any, Dict

from loguru import logger
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.configuration.inject import ConfigValue
from src.configuration.setup import get_connection
from src.strategies.interface import ReconciliationStrategy, Strategies


async def render_preview(uri: str) -> ValueError | str:
    """Provides a generic HTML preview for a given entity ID."""

    logger.debug(f"Rendering preview for URI: {uri}")
    id_base: str = ConfigValue("options:id_base").resolve()
    connection: AsyncConnection = await get_connection()

    if not uri.startswith(id_base):
        raise ValueError("Invalid ID format")

    parts: list[str] = uri.replace(id_base, "").split("/")
    if len(parts) != 2:
        raise ValueError("Invalid ID path")

    entity_path, entity_id_str = parts

    logger.debug(f"Entity path: {entity_path}, Entity ID: {entity_id_str}")
    if not Strategies.items.get(entity_path):
        raise ValueError(f"Unknown entity type: {entity_path}")

    strategy: ReconciliationStrategy = Strategies.items.get(entity_path)()

    if not strategy:
        raise ValueError(f"Unknown entity type: {entity_path}")

    async with connection.cursor(row_factory=dict_row) as cur:
        details: Dict[str, Any] | None = await strategy.get_details(entity_id_str, cur)

    if not details:
        raise ValueError(f"Entity with ID {entity_id_str} not found or preview not implemented.")

    html = "<div style='padding:10px; font:14px sans-serif; line-height:1.6;'>"
    # Use 'Name' or 'label' for the title, falling back to the first value
    title = details.get("Name") or details.get("label") or next(iter(details.values()), "Details")
    html += f"<h3 style='margin-top:0;'>{title}</h3>"

    for key, value in details.items():
        if value is not None and str(value).strip() != "":
            html += "<div style='margin-bottom:5px;'>"
            html += f"<strong style='color:#333; min-width:100px; display:inline-block;'>{key}:</strong> "
            html += f"<span>{value}</span>"
            html += "</div>"

    html += "</div>"
    return html
