from typing import Any

from src.configuration import ConfigValue
from src.strategies.strategy import ReconciliationStrategy, StrategyRegistry


def get_reconcile_properties(strategies: StrategyRegistry, query: str = None, entity_type: str = None) -> list[dict[str, str]] | Any:
    """
    Collects property suggestions returned by the `/properties endpoint` for OpenRefine.

    Endpoint: /reconcile/properties

    Returns available properties that can be used for enhanced reconciliation.
    OpenRefine calls this endpoint to populate property selection dropdowns.

    Args:
        query: Optional search term to filter properties
        type: Optional entity type to filter properties (e.g., "site", "taxon")

    Returns:
        Dict with matching properties
    """
    all_properties = _get_properties(strategies, entity_type)

    # Remove duplicates based on property "id". This keeps last property occurrence.
    # This assumes that properties with the same ID are identical across strategies.
    unique_properties = list({d["id"]: d for d in all_properties}.values())

    # Filter properties based on query if provided
    if query:
        query_lower: str = query.lower()
        filtered_properties = [
            prop
            for prop in unique_properties
            if query_lower in prop["id"].lower() or query_lower in prop["name"].lower() or query_lower in prop.get("description", "").lower()
        ]
    else:
        filtered_properties: list[dict[str, str]] = unique_properties
    return filtered_properties


def _get_properties(strategies, entity_type):
    """Collects properties from all registered strategies or a specific strategy if entity_type is provided."""
    if entity_type and entity_type in strategies.items:
        # Get properties for the specific entity type
        return strategies.items[entity_type]().get_properties_meta()

    if entity_type and entity_type not in strategies.items:
        # Unknown entity type - return empty to avoid confusion
        return []
    # Return properties from all strategies
    return [p for strategy_class in strategies.items.values() for p in strategy_class().get_properties_meta()]


def _compile_property_settings(strategies) -> list[dict[str, str]]:
    """
    Collects property settings from all registered strategies for OpenRefine.

    Endpoint: /reconcile (GET)
    Returns a list of property settings dicts for OpenRefine's property selection UI.
    """
    property_settings: list[dict[str, str]] = []
    for strategy_cls in strategies.items.values():
        strategy: ReconciliationStrategy = strategy_cls()
        specific_settings: dict[str, dict[str, Any]] = strategy.get_property_settings() or {}

        for item in strategy.get_properties_meta():

            property_setting: dict[str, str] | None = next((s for s in property_settings if s["name"] == item["id"]), None)
            if not property_setting:
                property_setting = {
                    "name": item["id"],
                    "label": item["name"],
                    "type": item["type"],
                    "help_text": item.get("description", ""),
                    "entity_types": [strategy.get_id_path()],
                }
                property_settings.append(property_setting)
            else:
                # Property already exists, so just add this strategy's entity type if not already present
                if strategy.get_id_path() not in property_setting["entity_types"]:
                    property_setting["entity_types"].append(strategy.get_id_path())

            if specific_settings:
                # Add settings if defined for this property (overwrite if already present)
                if item["id"] in specific_settings:
                    property_setting["settings"] = specific_settings[item["id"]]

    return property_settings


def _get_default_types(strategies: StrategyRegistry) -> list[dict[str, str]]:
    """Collects default types from all registered strategies for OpenRefine."""
    default_types: list[dict[str, str]] = [
        {
            "id": entity_type,
            "name": strategy_class().get_display_name(),
        }
        for entity_type, strategy_class in strategies.items.items()
    ]

    default_types.sort(key=lambda x: (x["name"]))

    return default_types


def get_reconciliation_metadata(strategies: StrategyRegistry, host: str) -> dict[str, Any]:
    """
    Collects reconciliation metadata from all registered strategies.
    """
    default_types: list[dict[str, str]] = _get_default_types(strategies)
    id_base: str = ConfigValue("options:id_base").resolve()

    # Collect property settings from all registered strategies
    property_settings: list[dict[str, str]] = _compile_property_settings(strategies)

    # Ensure host doesn't end with slash to avoid double slashes
    base_url_clean: str = str(host).rstrip("/")

    return {
        "name": "SEAD Entity Reconciliation",
        "identifierSpace": f"{id_base}",
        "schemaSpace": "http://www.w3.org/2004/02/skos/core#",
        "defaultTypes": default_types,
        "view": {"url": f"{base_url_clean}/reconcile/preview?id={{{{id}}}}"},
        "preview": {"url": f"{base_url_clean}/reconcile/preview?id={{{{id}}}}", "width": 400, "height": 300},
        "suggest": {
            "entity": {
                "service_url": f"{base_url_clean}",
                "service_path": "/suggest/entity",
                "flyout_service_url": f"{base_url_clean}",
                "flyout_service_path": "/flyout/entity?id=${{id}}",
            },
            "type": {"service_url": f"{base_url_clean}", "service_path": "/suggest/type"},
            "property": {"service_url": f"{base_url_clean}", "service_path": "/suggest/property"},
        },
        "extend": {
            "propose_properties": {
                "service_url": f"{base_url_clean}/reconcile",
                "service_path": "/properties",
            },
            "property_settings": property_settings,
        },
    }
