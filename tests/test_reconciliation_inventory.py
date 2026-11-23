from pathlib import Path
from typing import Any

import pytest
import yaml

from src.configuration import get_config_provider
from src.scripts.generate_reconciliation_inventory import (
    ROWS_END,
    ROWS_START,
    build_inventory,
    documented_registrations,
    registered_types,
    render_document,
)
from src.strategies.configured_classifier import ClassifierConfigurationError
from src.strategies.strategy import Strategies

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(name="inventory_inputs")
def make_inventory_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, str], dict[str, Any]]:
    model: dict[str, Any] = {
        "model": {"version": "test"},
        "entities": {
            "colour": {"role": "classifier", "target_table": "tbl_colours"},
            "taxa": {"role": "classifier", "target_table": "tbl_taxa"},
            "dataset": {"role": "lookup", "target_table": "tbl_datasets"},
            "feature": {"role": "lookup", "target_table": "tbl_features"},
            "link": {"role": "bridge", "target_table": "tbl_links"},
        },
    }
    specs: dict[str, Any] = {
        "colour": {
            "table_name": "tbl_colours",
            "label_column": "colour_name",
            "reconciliation": "simple",
            "scope_columns": ["method_id"],
        },
        "taxa_tree_master": {"table_name": "tbl_taxa", "label_column": "species"},
        "feature": {"table_name": "tbl_features", "label_column": "feature_name"},
        "country": {"table_name": "tbl_locations", "label_column": "location_name", "reconciliation": "simple"},
    }
    registrations = {"colour": "supported", "taxon": "excluded", "country": "supported"}
    notes: dict[str, Any] = {
        "aliases": {"taxa": "taxon"},
        "reasons": {
            "taxa": "The taxon strategy is a placeholder.",
            "dataset": "Tracked aggregate.",
            "feature": "Not yet registered.",
        },
        "planned": {"feature": "Phase 2"},
    }
    return model, specs, registrations, notes


def test_build_inventory_uses_registry_status_and_explicit_aliases(
    inventory_inputs: tuple[dict[str, Any], dict[str, Any], dict[str, str], dict[str, Any]],
) -> None:
    model, specs, registrations, notes = inventory_inputs
    entries = build_inventory(model, specs, registrations, notes)
    by_entity = {entry.entity: entry for entry in entries}

    assert by_entity["colour"].service_type == "colour"
    assert by_entity["colour"].disposition == "supported"
    assert by_entity["colour"].marker == "simple"
    assert by_entity["colour"].label_column == "colour_name"
    assert by_entity["colour"].scope_columns == ("method_id",)
    assert by_entity["taxa"].service_type == "taxon"
    assert by_entity["taxa"].disposition == "excluded"
    assert by_entity["taxa"].label_column == "species"
    assert by_entity["dataset"].disposition == "excluded"
    assert by_entity["link"].disposition == "not-a-target"
    assert by_entity["feature"].disposition == "excluded"
    assert by_entity["feature"].planned == "Phase 2"
    assert by_entity["country"].role == "service-only"
    assert {entry.service_type for entry in entries if entry.service_type} == set(registrations)


def test_inventory_rejects_unexplained_exclusions(
    inventory_inputs: tuple[dict[str, Any], dict[str, Any], dict[str, str], dict[str, Any]],
) -> None:
    model, specs, registrations, notes = inventory_inputs
    notes["reasons"].pop("taxa")

    with pytest.raises(ValueError, match="taxa.*reason"):
        build_inventory(model, specs, registrations, notes)


def test_inventory_rejects_duplicate_registration_aliases(
    inventory_inputs: tuple[dict[str, Any], dict[str, Any], dict[str, str], dict[str, Any]],
) -> None:
    model, specs, registrations, notes = inventory_inputs
    notes["aliases"]["feature"] = "taxon"

    with pytest.raises(ValueError, match="taxon.*more than one"):
        build_inventory(model, specs, registrations, notes)


def test_inventory_rejects_planned_phases_for_supported_types(
    inventory_inputs: tuple[dict[str, Any], dict[str, Any], dict[str, str], dict[str, Any]],
) -> None:
    model, specs, registrations, notes = inventory_inputs
    notes["planned"]["colour"] = "Phase 2"

    with pytest.raises(ValueError, match="colour.*planned phase"):
        build_inventory(model, specs, registrations, notes)


def test_render_document_preserves_manual_notes_and_is_idempotent(
    inventory_inputs: tuple[dict[str, Any], dict[str, Any], dict[str, str], dict[str, Any]],
) -> None:
    model, specs, registrations, notes = inventory_inputs
    manual = yaml.safe_dump(notes, sort_keys=True)
    document = (
        "# Inventory\n\n"
        "<!-- reconciliation-inventory:manual\n"
        f"{manual}"
        "-->\n\n"
        "<!-- reconciliation-inventory:generated:start -->\n"
        "Old generated content.\n"
        "<!-- reconciliation-inventory:generated:end -->\n"
    )

    rendered = render_document(document, model, specs, registrations)

    assert manual in rendered
    assert "Old generated content." not in rendered
    assert "The taxon strategy is a placeholder." in rendered
    assert "Model entities: 5. Registered service types: 3." in rendered
    assert "| supported | 2 |" in rendered
    assert documented_registrations(rendered) == registrations
    assert render_document(rendered, model, specs, registrations) == rendered

    notes["planned"] = {}
    updated_manual = yaml.safe_dump(notes, sort_keys=True)
    without_plans = render_document(document.replace(manual, updated_manual), model, specs, registrations)
    assert "Planned phase" not in without_plans


def test_documented_registrations_rejects_duplicate_service_types() -> None:
    document = (
        f"{ROWS_START}\n"
        "| Entity | Service type | Target table | Role | Disposition |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| `colour` | `colour` | `tbl_colours` | classifier | supported |\n"
        "| `other` | `colour` | `tbl_colours` | classifier | excluded |\n"
        f"{ROWS_END}\n"
    )

    with pytest.raises(ValueError, match="colour.*more than once"):
        documented_registrations(document)


def test_registry_state_is_restored_after_configuration_error() -> None:
    original_provider = get_config_provider()
    original_strategies = dict(Strategies.items)

    with pytest.raises(ClassifierConfigurationError):
        registered_types({}, {})

    assert get_config_provider() is original_provider
    assert Strategies.items == original_strategies


def test_checked_in_inventory_matches_the_real_registry() -> None:
    specs: dict[str, Any] = yaml.safe_load((REPOSITORY_ROOT / "config/entities.yml").read_text(encoding="utf-8"))
    config: dict[str, Any] = yaml.safe_load((REPOSITORY_ROOT / "config/config.yml").read_text(encoding="utf-8"))
    original_provider = get_config_provider()
    original_strategies = dict(Strategies.items)

    registrations = registered_types(specs, config["options"]["reconciliation"])

    assert get_config_provider() is original_provider
    assert Strategies.items == original_strategies
    document = (REPOSITORY_ROOT / "docs/RECONCILIATION_TYPE_INVENTORY.md").read_text(encoding="utf-8")
    assert documented_registrations(document) == registrations
