"""
OpenRefine Suggest API implementation for autocomplete and inline previews.

This module provides the Suggest API endpoints that enable:
- Entity autocomplete suggestions as users type
- Inline tooltip/flyout previews on hover
- Type and property suggestions
"""

from typing import Any

from loguru import logger
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.configuration.inject import ConfigValue
from src.configuration.setup import get_connection
from src.strategies.strategy import ReconciliationStrategy, Strategies


# pylint: disable=too-many-locals
async def render_flyout_preview(uri: str) -> dict[str, Any]:
    """
    Generate compact HTML preview for OpenRefine flyout/tooltip.

    Returns JSON with 'id' and 'html' fields for inline preview display.
    """
    logger.info(f"Rendering flyout preview for URI: {uri}")
    id_base: str = ConfigValue("options:id_base").resolve()
    connection: AsyncConnection = await get_connection()

    if not uri.startswith(id_base):
        raise ValueError("Invalid ID format")

    parts: list[str] = uri.replace(id_base, "").split("/")
    if len(parts) != 2:
        raise ValueError("Invalid ID path")

    entity_path, entity_id_str = parts

    logger.info(f"Flyout - Entity path: {entity_path}, Entity ID: {entity_id_str}")

    if not Strategies.items.get(entity_path):
        raise ValueError(f"Unknown entity type: {entity_path}")

    strategy: ReconciliationStrategy = Strategies.items.get(entity_path)()

    async with connection.cursor(row_factory=dict_row) as cur:
        details: dict[str, Any] | None = await strategy.get_details(entity_id_str, cur)

    if not details:
        raise ValueError(f"Entity with ID {entity_id_str} not found")

    # Create compact HTML for tooltip display
    title = details.get("Name") or details.get("label") or next(iter(details.values()), "Details")

    html = f"""<div style="padding:6px 8px; font-family:sans-serif; font-size:11px; line-height:1.3; max-width:300px;">
    <div style="font-weight:600; font-size:12px; margin-bottom:3px; color:#1a1a1a; border-bottom:1px solid #e0e0e0; padding-bottom:2px;">
        {title}
    </div>
    <div style="background:#f5f5f5; padding:2px 6px; border-radius:2px; display:inline-block; font-size:9px; margin-bottom:4px; color:#666; text-transform:uppercase;">
        {entity_path}
    </div>
"""

    # Add key details (limit to most important fields for compact display)
    detail_count = 0
    max_details = 5

    for key, value in details.items():
        if value is not None and str(value).strip() != "" and key not in ["Name", "label"]:
            if detail_count >= max_details:
                break

            # Truncate long values more aggressively
            value_str = str(value)
            if len(value_str) > 60:
                value_str = value_str[:57] + "..."

            html += f"""    <div style="margin:2px 0; padding:1px 0;">
        <span style="font-weight:500; color:#555; font-size:10px;">{key}:</span>
        <span style="color:#222; margin-left:3px; font-size:10px;">{value_str}</span>
    </div>
"""
            detail_count += 1

    html += "</div>"

    return {"id": uri, "html": html}


async def suggest_entities(prefix: str, entity_type: str = "", limit: int = 10) -> dict[str, Any]:
    """
    Suggest entities based on prefix (autocomplete).

    Args:
        prefix: The text prefix to match
        entity_type: Optional entity type filter (e.g., 'site', 'location', 'taxon')
        limit: Maximum number of suggestions to return

    Returns:
        JSON response with suggested entities
    """
    logger.info(f"Entity suggest: prefix='{prefix}', type='{entity_type}', limit={limit}")

    if not prefix or len(prefix) < 2:
        return {"result": []}

    connection: AsyncConnection = await get_connection()
    id_base: str = ConfigValue("options:id_base").resolve()

    results = []

    # Determine which strategies to query
    strategies_to_query = {}
    if entity_type and entity_type in Strategies.items:
        strategies_to_query[entity_type] = Strategies.items[entity_type]
    else:
        strategies_to_query = dict(Strategies.items)

    async with connection.cursor(row_factory=dict_row) as cursor:
        for type_key, strategy_class in strategies_to_query.items():
            strategy: ReconciliationStrategy = strategy_class()

            # Use the existing find_candidates method with limit
            try:
                candidates = await strategy.find_candidates(cursor=cursor, query=prefix, properties={}, limit=limit)

                # Convert to suggest API format
                for candidate in candidates[:limit]:
                    entity_id = candidate.get(strategy.get_entity_id_field())
                    label = candidate.get(strategy.get_label_field())

                    if entity_id and label:
                        results.append(
                            {
                                "id": f"{id_base}{type_key}/{entity_id}",
                                "name": label,
                                "type": [{"id": type_key, "name": type_key}],
                                "description": candidate.get("description", ""),
                                "score": candidate.get("name_sim", 0),
                            }
                        )

                if len(results) >= limit:
                    break

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"Error suggesting entities from {type_key}: {e}")
                continue

    # Sort by score and limit
    results.sort(key=lambda x: x.get("score", 0), reverse=True)

    return {"result": results[:limit]}


async def suggest_types(prefix: str = "") -> dict[str, Any]:
    """
    Suggest entity types based on prefix.

    Args:
        prefix: Optional prefix to filter types

    Returns:
        JSON response with type suggestions
    """
    logger.info(f"Type suggest: prefix='{prefix}'")

    all_types: list[dict[str, str]] = [{"id": type_key, "name": strategy_class().get_display_name()} for type_key, strategy_class in Strategies.items.items()]

    # Filter by prefix if provided
    if prefix:
        prefix_lower: str = prefix.lower()
        filtered_types: list[dict[str, str]] = [t for t in all_types if prefix_lower in t["id"].lower() or prefix_lower in t["name"].lower()]
    else:
        filtered_types = all_types

    return {"result": filtered_types}


async def suggest_properties(prefix: str = "", entity_type: str = "") -> dict[str, Any]:
    """
    Suggest properties based on prefix and optional entity type.

    Args:
        prefix: Optional prefix to filter properties
        entity_type: Optional entity type to filter properties

    Returns:
        JSON response with property suggestions
    """
    logger.info(f"Property suggest: prefix='{prefix}', type='{entity_type}'")

    all_properties = []

    # Determine which strategies to query
    if entity_type and entity_type in Strategies.items:
        strategy = Strategies.items[entity_type]()
        all_properties = strategy.get_properties_meta()
    else:
        # Get properties from all strategies
        for strategy_class in Strategies.items.values():
            strategy = strategy_class()
            all_properties.extend(strategy.get_properties_meta())

    # Convert to suggest API format
    property_suggestions = [{"id": prop["id"], "name": prop["name"], "description": prop.get("description", "")} for prop in all_properties]

    # Filter by prefix if provided
    if prefix:
        prefix_lower = prefix.lower()
        property_suggestions = [
            p
            for p in property_suggestions
            if prefix_lower in p["id"].lower() or prefix_lower in p["name"].lower() or prefix_lower in p.get("description", "").lower()
        ]

    # Remove duplicates by id
    seen = set()
    unique_properties = []
    for prop in property_suggestions:
        if prop["id"] not in seen:
            seen.add(prop["id"])
            unique_properties.append(prop)

    return {"result": unique_properties}
