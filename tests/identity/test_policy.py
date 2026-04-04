"""Tests for src.identity.policy — no database required."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest
import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_policy(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "identity_policy.yml"
    p.write_text(textwrap.dedent(content))
    return p


def _minimal_policy(extra_entities: str = "") -> str:
    """Return a well-formed minimal policy YAML."""
    return f"""
    entities:
      site:
        entity_subtype: provider_owned
        accept_uuid: false
        allow_allocation: true
        auto_confirm: true
      taxa:
        entity_subtype: shared_metadata
        accept_uuid: true
        allow_allocation: false
        auto_confirm: false
    {extra_entities}
    defaults:
      entity_subtype: shared_metadata
      accept_uuid: true
      allow_allocation: false
      auto_confirm: false
    """


# ---------------------------------------------------------------------------
# Import — must follow helpers so tmp_path is ready
# ---------------------------------------------------------------------------

from src.identity.policy import EntityPolicy, IdentityPolicy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def minimal_policy_file(tmp_path: Path) -> Path:
    return _write_policy(tmp_path, _minimal_policy())


@pytest.fixture()
def loaded_policy(minimal_policy_file: Path) -> IdentityPolicy:
    return IdentityPolicy(policy_path=minimal_policy_file)


# ---------------------------------------------------------------------------
# Construction & loading
# ---------------------------------------------------------------------------


class TestPolicyConstruction:
    def test_loads_from_explicit_path(self, minimal_policy_file: Path) -> None:
        policy = IdentityPolicy(policy_path=minimal_policy_file)
        assert policy is not None

    def test_loads_default_path(self) -> None:
        """Default path (config/identity_policy.yml) must exist and load cleanly."""
        policy = IdentityPolicy()
        assert policy is not None
        assert len(policy.known_entity_types()) > 0

    def test_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            IdentityPolicy(policy_path=tmp_path / "nonexistent.yml")

    def test_env_var_override(self, monkeypatch: pytest.MonkeyPatch, minimal_policy_file: Path) -> None:
        monkeypatch.setenv("IDENTITY_POLICY_FILE", str(minimal_policy_file))
        # Need to re-import _resolve_policy_path after env var is set
        from src.identity.policy import _resolve_policy_path

        resolved = _resolve_policy_path()
        assert resolved == minimal_policy_file


# ---------------------------------------------------------------------------
# known_entity_types
# ---------------------------------------------------------------------------


class TestKnownEntityTypes:
    def test_returns_explicitly_listed_types(self, loaded_policy: IdentityPolicy) -> None:
        types = loaded_policy.known_entity_types()
        assert "site" in types
        assert "taxa" in types

    def test_length_matches_yaml(self, loaded_policy: IdentityPolicy) -> None:
        assert len(loaded_policy.known_entity_types()) == 2


# ---------------------------------------------------------------------------
# get_entity_policy — known entities
# ---------------------------------------------------------------------------


class TestKnownEntityPolicies:
    def test_site_is_provider_owned(self, loaded_policy: IdentityPolicy) -> None:
        ep = loaded_policy.get_entity_policy("site")
        assert ep.entity_subtype == "provider_owned"
        assert ep.is_provider_owned

    def test_site_disallows_accept_uuid(self, loaded_policy: IdentityPolicy) -> None:
        ep = loaded_policy.get_entity_policy("site")
        assert ep.accept_uuid is False

    def test_site_allows_allocation(self, loaded_policy: IdentityPolicy) -> None:
        ep = loaded_policy.get_entity_policy("site")
        assert ep.allow_allocation is True

    def test_site_auto_confirms(self, loaded_policy: IdentityPolicy) -> None:
        ep = loaded_policy.get_entity_policy("site")
        assert ep.auto_confirm is True

    def test_taxa_is_shared_metadata(self, loaded_policy: IdentityPolicy) -> None:
        ep = loaded_policy.get_entity_policy("taxa")
        assert ep.entity_subtype == "shared_metadata"
        assert ep.is_shared_metadata

    def test_taxa_does_not_allow_allocation(self, loaded_policy: IdentityPolicy) -> None:
        ep = loaded_policy.get_entity_policy("taxa")
        assert ep.allow_allocation is False

    def test_taxa_does_not_auto_confirm(self, loaded_policy: IdentityPolicy) -> None:
        ep = loaded_policy.get_entity_policy("taxa")
        assert ep.auto_confirm is False

    def test_entity_type_stored_on_policy(self, loaded_policy: IdentityPolicy) -> None:
        ep = loaded_policy.get_entity_policy("site")
        assert ep.entity_type == "site"


# ---------------------------------------------------------------------------
# get_entity_policy — unknown entities fall back to defaults
# ---------------------------------------------------------------------------


class TestDefaultFallback:
    def test_unknown_type_returns_default_subtype(self, loaded_policy: IdentityPolicy) -> None:
        ep = loaded_policy.get_entity_policy("unknown_entity_xyz")
        assert ep.entity_subtype == "shared_metadata"

    def test_unknown_type_returns_default_accept_uuid(self, loaded_policy: IdentityPolicy) -> None:
        ep = loaded_policy.get_entity_policy("unknown_entity_xyz")
        assert ep.accept_uuid is True

    def test_unknown_type_disallows_allocation_by_default(self, loaded_policy: IdentityPolicy) -> None:
        ep = loaded_policy.get_entity_policy("unknown_entity_xyz")
        assert ep.allow_allocation is False

    def test_unknown_type_does_not_auto_confirm_by_default(self, loaded_policy: IdentityPolicy) -> None:
        ep = loaded_policy.get_entity_policy("unknown_entity_xyz")
        assert ep.auto_confirm is False


# ---------------------------------------------------------------------------
# EntityPolicy helper properties
# ---------------------------------------------------------------------------


class TestEntityPolicyProperties:
    def test_is_provider_owned_true(self) -> None:
        ep = EntityPolicy(
            entity_type="site",
            entity_subtype="provider_owned",
            accept_uuid=False,
            allow_allocation=True,
            auto_confirm=True,
        )
        assert ep.is_provider_owned
        assert not ep.is_shared_metadata
        assert not ep.is_relationship

    def test_is_shared_metadata_true(self) -> None:
        ep = EntityPolicy(
            entity_type="taxa",
            entity_subtype="shared_metadata",
            accept_uuid=True,
            allow_allocation=False,
            auto_confirm=False,
        )
        assert ep.is_shared_metadata
        assert not ep.is_provider_owned
        assert not ep.is_relationship

    def test_is_relationship_true(self) -> None:
        ep = EntityPolicy(
            entity_type="abundance",
            entity_subtype="relationship",
            accept_uuid=False,
            allow_allocation=False,
            auto_confirm=False,
        )
        assert ep.is_relationship
        assert not ep.is_provider_owned
        assert not ep.is_shared_metadata

    def test_entity_policy_is_frozen(self) -> None:
        ep = EntityPolicy(
            entity_type="site",
            entity_subtype="provider_owned",
            accept_uuid=False,
            allow_allocation=True,
            auto_confirm=True,
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            ep.auto_confirm = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class TestValidationErrors:
    def test_missing_defaults_field_raises(self, tmp_path: Path) -> None:
        bad_yaml = """
        entities: {}
        defaults:
          entity_subtype: shared_metadata
          accept_uuid: true
          allow_allocation: false
          # auto_confirm intentionally missing
        """
        p = _write_policy(tmp_path, bad_yaml)
        with pytest.raises(ValueError, match="auto_confirm"):
            IdentityPolicy(policy_path=p)

    def test_invalid_subtype_in_defaults_raises(self, tmp_path: Path) -> None:
        bad_yaml = """
        entities: {}
        defaults:
          entity_subtype: INVALID
          accept_uuid: true
          allow_allocation: false
          auto_confirm: false
        """
        p = _write_policy(tmp_path, bad_yaml)
        with pytest.raises(ValueError, match="entity_subtype"):
            IdentityPolicy(policy_path=p)

    def test_invalid_subtype_in_entity_raises(self, tmp_path: Path) -> None:
        bad_yaml = """
        entities:
          site:
            entity_subtype: WRONG_TYPE
            accept_uuid: false
            allow_allocation: true
            auto_confirm: true
        defaults:
          entity_subtype: shared_metadata
          accept_uuid: true
          allow_allocation: false
          auto_confirm: false
        """
        p = _write_policy(tmp_path, bad_yaml)
        with pytest.raises(ValueError, match="entity_subtype"):
            IdentityPolicy(policy_path=p)


# ---------------------------------------------------------------------------
# Real policy file smoke test
# ---------------------------------------------------------------------------


class TestRealPolicyFile:
    def test_site_in_real_policy(self) -> None:
        policy = IdentityPolicy()
        ep = policy.get_entity_policy("site")
        assert ep.is_provider_owned
        assert ep.allow_allocation is True

    def test_taxa_tree_master_in_real_policy(self) -> None:
        policy = IdentityPolicy()
        ep = policy.get_entity_policy("taxa_tree_master")
        assert ep.is_shared_metadata

    def test_unknown_entity_falls_back_to_defaults(self) -> None:
        policy = IdentityPolicy()
        ep = policy.get_entity_policy("some_entity_not_in_file")
        assert ep.entity_subtype is not None  # defaults applied

    def test_reload_does_not_raise(self) -> None:
        policy = IdentityPolicy()
        policy.reload()  # should not raise
