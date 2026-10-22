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
EntityOperation = Literal["bind_existing", "allocate_new"]

# Version of the GET /identity/capabilities response schema.
CAPABILITY_VERSION = "1.0"


@dataclass(frozen=True)
class EntityPolicy:
    """Immutable policy snapshot for one entity type."""

    entity_type: str
    entity_subtype: EntitySubtype
    accept_uuid: bool
    allow_allocation: bool
    auto_confirm: bool
    bind_existing: bool = False
    allocate_new: bool = False

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
        operations = base.get("operations", {}) or {}
        allocate_new = bool(operations.get("allocate_new", base.get("allow_allocation", False)))
        bind_existing = bool(operations.get("bind_existing", False))
        return EntityPolicy(
            entity_type=entity_type,
            entity_subtype=base["entity_subtype"],
            accept_uuid=bool(base["accept_uuid"]),
            allow_allocation=allocate_new,
            auto_confirm=bool(base["auto_confirm"]),
            bind_existing=bind_existing,
            allocate_new=allocate_new,
        )

    def known_entity_types(self) -> list[str]:
        """Return entity types explicitly listed in the policy file."""
        return list(self._entities.keys())

    def is_configured(self, entity_type: str) -> bool:
        """Return True when *entity_type* is explicitly listed in the policy."""
        return entity_type in self._entities

    def supports(self, entity_type: str, operation: EntityOperation) -> bool:
        """Return True when *entity_type* is configured and permits *operation*."""
        if not self.is_configured(entity_type):
            return False
        ep = self.get_entity_policy(entity_type)
        if operation == "bind_existing":
            return ep.bind_existing
        if operation == "allocate_new":
            return ep.allocate_new
        return False

    def get_capabilities(self) -> list[EntityCapability]:
        """Return a capability snapshot for each configured entity type."""
        capabilities: list[EntityCapability] = []
        for name in sorted(self._entities):
            ep = self.get_entity_policy(name)
            capabilities.append(
                EntityCapability(
                    entity_type=name,
                    entity_subtype=ep.entity_subtype,
                    bind_existing=ep.bind_existing,
                    allocate_new=ep.allocate_new,
                    auto_confirm=ep.auto_confirm,
                    accept_uuid=ep.accept_uuid,
                )
            )
        return capabilities

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
_REQUIRED_FIELDS: frozenset[str] = frozenset({"entity_subtype", "accept_uuid", "auto_confirm"})
_VALID_SUBTYPES: frozenset[str] = frozenset({"provider_owned", "shared_metadata", "relationship"})
_OPERATION_KEYS: frozenset[str] = frozenset({"bind_existing", "allocate_new"})


@dataclass(frozen=True)
class EntityCapability:
    """Published capability snapshot for one configured entity type."""

    entity_type: str
    entity_subtype: EntitySubtype
    bind_existing: bool
    allocate_new: bool
    auto_confirm: bool
    accept_uuid: bool


def _validate_policy(entities: dict, defaults: dict) -> None:
    """Raise ValueError on a malformed policy file. Called once on load."""
    missing: frozenset[str] = _REQUIRED_FIELDS - set(defaults)
    if missing:
        raise ValueError(f"Identity policy 'defaults' block is missing fields: {missing}")

    if defaults.get("entity_subtype") not in _VALID_SUBTYPES:
        raise ValueError(f"Invalid entity_subtype in defaults: {defaults.get('entity_subtype')!r}")
    _validate_operations(defaults.get("operations"), "defaults")

    for name, cfg in entities.items():
        # Merge with defaults so partial entries are valid
        merged = {**defaults, **cfg}
        missing = _REQUIRED_FIELDS - set(merged)
        if missing:
            raise ValueError(f"Entity policy for '{name}' is missing fields: {missing}")
        if merged.get("entity_subtype") not in _VALID_SUBTYPES:
            raise ValueError(f"Invalid entity_subtype for '{name}': {merged.get('entity_subtype')!r}")
        _validate_operations(merged.get("operations"), name)


def _validate_operations(operations: object, context: str) -> None:
    """Raise ValueError when *operations* is not a valid bind/allocate mapping."""
    if operations is None:
        return
    if not isinstance(operations, dict):
        raise ValueError(f"Identity policy '{context}' operations must be a mapping")
    unknown = set(operations) - _OPERATION_KEYS
    if unknown:
        raise ValueError(f"Identity policy '{context}' has unknown operation keys: {sorted(unknown)}")
    for key in _OPERATION_KEYS:
        if key in operations and not isinstance(operations[key], bool):
            raise ValueError(f"Identity policy '{context}' operation '{key}' must be a boolean")
