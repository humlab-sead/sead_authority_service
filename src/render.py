from typing import Any, Dict

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from configuration.inject import ConfigValue
from strategies import Strategies
from strategies.interface import ReconciliationStrategy


async def render_preview(uri: str) -> ValueError | str:
    """Provides a generic HTML preview for a given entity ID."""

    id_base: str = ConfigValue("service:id_base").resolve()
    connection: AsyncConnection = ConfigValue("runtime:connection").resolve()

    if not uri.startswith(id_base):
        raise ValueError("Invalid ID format")

    parts: list[str] = uri.replace(id_base, "").split("/")
    if len(parts) != 2:
        raise ValueError("Invalid ID path")

    entity_path, entity_id_str = parts

    if not Strategies.items.get(entity_path):
        raise ValueError(f"Unknown entity type: {entity_path}")

    strategy: ReconciliationStrategy = Strategies.items.get(entity_path)

    if not strategy:
        raise ValueError(f"Unknown entity type: {entity_path}")

    async with connection.cursor(row_factory=dict_row) as cur:
        details: Dict[str, Any] | None = await strategy.get_details(entity_id_str, cur)

    if not details:
        raise ValueError(
            f"Entity with ID {entity_id_str} not found or preview not implemented.",
            status_code=404,
        )

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
