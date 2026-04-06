"""SIMS Identity Policy loader.

Reads config/identity_policy.yml (or the file pointed to by
ConfigValue("identity:policy_file")) and exposes per-entity-type rules.

Usage::

    from src.identity.policy import IdentityPolicy

    policy = IdentityPolicy()               # loads default YAML
    ep = policy.get_entity_policy("site")   # → EntityPolicy
    if ep.allow_allocation:
        tracked = await repo.mint("site")

The policy object is lightweight (a parsed YAML dict) and safe to instantiate
per-request, or to cache as a module-level singleton.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml
from loguru import logger

# Path resolution: honour CONFIG_FILE env var directory structure, or fall back
# to the standard location relative to this file's package root.
_DEFAULT_POLICY_PATH = Path(__file__).parent.parent.parent / "config" / "identity_policy.yml"

EntitySubtype = Literal["provider_owned", "shared_metadata", "relationship"]


@dataclass(frozen=True)
class EntityPolicy:
    """Immutable policy snapshot for one entity type."""

    entity_type: str
    entity_subtype: EntitySubtype
    accept_uuid: bool
    allow_allocation: bool
    auto_confirm: bool

    @property
    def is_provider_owned(self) -> bool:
        return self.entity_subtype == "provider_owned"

    @property
    def is_shared_metadata(self) -> bool:
        return self.entity_subtype == "shared_metadata"

    @property
    def is_relationship(self) -> bool:
        return self.entity_subtype == "relationship"


@dataclass
class IdentityPolicy:
    """Loaded identity policy. Instantiate once and re-use.

    Parameters
    ----------
    policy_path:
        Path to a YAML file.  Defaults to ``config/identity_policy.yml``
        (resolved relative to the repository root).  Override in tests by
        passing an explicit path, or via the ``IDENTITY_POLICY_FILE``
        environment variable.
    """

    policy_path: Path = field(default_factory=lambda: _resolve_policy_path())

    # Populated during __post_init__
    _raw: dict = field(init=False, repr=False, default_factory=dict)
    _entities: dict[str, dict] = field(init=False, repr=False, default_factory=dict)
    _defaults: dict = field(init=False, repr=False, default_factory=dict)

    def __post_init__(self) -> None:
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_entity_policy(self, entity_type: str) -> EntityPolicy:
        """Return the policy for *entity_type*, falling back to defaults."""
        base = dict(self._defaults)
        base.update(self._entities.get(entity_type, {}))
        return EntityPolicy(
            entity_type=entity_type,
            entity_subtype=base["entity_subtype"],
            accept_uuid=bool(base["accept_uuid"]),
            allow_allocation=bool(base["allow_allocation"]),
            auto_confirm=bool(base["auto_confirm"]),
        )

    def known_entity_types(self) -> list[str]:
        """Return entity types explicitly listed in the policy file."""
        return list(self._entities.keys())

    def reload(self) -> None:
        """Re-read the YAML file (useful after hot-reloading config)."""
        self._load()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _load(self) -> None:
        path: Path = self.policy_path
        if not path.is_file():
            raise FileNotFoundError(f"Identity policy file not found: {path}")
        with path.open("r", encoding="utf-8") as fh:
            self._raw = yaml.safe_load(fh) or {}
        self._entities = self._raw.get("entities", {})
        self._defaults = self._raw.get("defaults", {})
        _validate_policy(self._entities, self._defaults)
        logger.debug(f"Identity policy loaded from {path} ({len(self._entities)} entities)")


def _resolve_policy_path() -> Path:
    """Return the policy file path, honouring the IDENTITY_POLICY_FILE env var."""
    env_override: str | None = os.environ.get("IDENTITY_POLICY_FILE")
    if env_override:
        return Path(env_override)
    return _DEFAULT_POLICY_PATH


# Required fields every entity entry and the defaults block must supply.
_REQUIRED_FIELDS: frozenset[str] = frozenset({"entity_subtype", "accept_uuid", "allow_allocation", "auto_confirm"})
_VALID_SUBTYPES: frozenset[str] = frozenset({"provider_owned", "shared_metadata", "relationship"})


def _validate_policy(entities: dict, defaults: dict) -> None:
    """Raise ValueError on a malformed policy file. Called once on load."""
    missing: frozenset[str] = _REQUIRED_FIELDS - set(defaults)
    if missing:
        raise ValueError(f"Identity policy 'defaults' block is missing fields: {missing}")

    if defaults.get("entity_subtype") not in _VALID_SUBTYPES:
        raise ValueError(f"Invalid entity_subtype in defaults: {defaults.get('entity_subtype')!r}")

    for name, cfg in entities.items():
        # Merge with defaults so partial entries are valid
        merged = {**defaults, **cfg}
        missing = _REQUIRED_FIELDS - set(merged)
        if missing:
            raise ValueError(f"Entity policy for '{name}' is missing fields: {missing}")
        if merged.get("entity_subtype") not in _VALID_SUBTYPES:
            raise ValueError(f"Invalid entity_subtype for '{name}': {merged.get('entity_subtype')!r}")
