"""Provider-scope business-key contracts for the SIMS identity module.

A provider scope (for example ``provider://<code>/<schema>``) must register the
ordered business-key list it uses for each entity type before it sends identity
work to SIMS. This module holds the rules shared by the service and the API
layer:

- which scopes need a contract (provider scopes only);
- how a caller is authorized to register a scope;
- the error types raised on a re-registration conflict or a missing contract.

The contract rows live in ``sead_identity.scope_entity_contracts`` and are read
and written by ``ScopeEntityContractRepository``.
"""

from __future__ import annotations

import hmac
from collections.abc import Sequence
from dataclasses import dataclass

from loguru import logger

from src.configuration import ConfigValue
from src.identity.models import EntityContractConflict

PROVIDER_SCOPE_PREFIX = "provider://"
"""Scope-name prefix used by provider-schema scopes that need a contract."""

_CONTRACT_REGISTRATION_CONFIG_PATH = "identity:contract_registration:callers"


class ContractAuthorizationError(PermissionError):
    """Raised when a caller may not register the requested provider scope."""


class IdentityContractConflict(ValueError):
    """Raised when submitted keys differ from the registered keys.

    The error carries one ``EntityContractConflict`` per mismatched entity type
    so the API layer can return the registered and submitted key lists.
    """

    def __init__(self, scope_name: str, conflicts: Sequence[EntityContractConflict]) -> None:
        self.scope_name: str = scope_name
        self.conflicts: list[EntityContractConflict] = list(conflicts)
        details = "; ".join(
            f"{conflict.entity_type}: registered {conflict.registered}, submitted {conflict.submitted}" for conflict in self.conflicts
        )
        super().__init__(f"Business-key contract conflict for scope '{scope_name}' ({details})")


class IdentityContractRequired(ValueError):
    """Raised when a provider scope sends identity work without a contract."""

    def __init__(self, scope_name: str, missing_entity_types: Sequence[str]) -> None:
        self.scope_name: str = scope_name
        self.missing_entity_types: list[str] = list(missing_entity_types)
        super().__init__(
            f"Provider scope '{scope_name}' has no registered business-key contract for: "
            f"{', '.join(self.missing_entity_types)}. Register the contract before sending identity work."
        )


def is_provider_scope(scope_name: str) -> bool:
    """Return True when *scope_name* is a provider scope that needs a contract."""
    return scope_name.strip().startswith(PROVIDER_SCOPE_PREFIX)


def require_provider_scope(scope_name: str) -> str:
    """Return the trimmed scope name, or raise ValueError for a non-provider scope.

    Internal SIMS scopes such as ``sead://admin`` keep working without a
    contract, so a contract registration for them is rejected.
    """
    text = scope_name.strip()
    if not text:
        raise ValueError("scope_name must not be blank")
    if not text.startswith(PROVIDER_SCOPE_PREFIX):
        raise ValueError(f"Business-key contracts apply to provider scopes only; '{text}' is not a '{PROVIDER_SCOPE_PREFIX}' scope")
    return text


@dataclass(frozen=True)
class ContractCaller:
    """One caller allowed to register provider-scope contracts.

    Attributes
    ----------
    name:
        Caller identifier sent in the ``X-SIMS-Caller`` header.
    token:
        Shared secret sent in the ``X-SIMS-Caller-Token`` header. An empty token
        disables the caller.
    scope_prefixes:
        Scope-name prefixes this caller may register. A caller can never claim
        a scope outside its configured prefixes.
    """

    name: str
    token: str
    scope_prefixes: tuple[str, ...]

    def allows(self, scope_name: str) -> bool:
        """Return True when *scope_name* starts with one of the allowed prefixes."""
        return any(scope_name.startswith(prefix) for prefix in self.scope_prefixes)


@dataclass(frozen=True)
class ContractRegistrationPolicy:
    """Caller allowlist for provider-scope contract registration.

    The allowlist is configured in SIMS, not supplied by the caller. A request
    without a configured caller, without the matching token, or for a scope
    outside the caller's prefixes is rejected.
    """

    callers: tuple[ContractCaller, ...] = ()

    @classmethod
    def from_config(cls) -> "ContractRegistrationPolicy":
        """Build the policy from ``identity.contract_registration.callers``."""
        try:
            raw_callers = ConfigValue(_CONTRACT_REGISTRATION_CONFIG_PATH, default=[]).resolve()
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(f"Contract registration config could not be read; registration is disabled: {exc}")
            return cls()
        return cls(callers=tuple(_to_callers(raw_callers or [])))

    def authorize(self, caller_name: str | None, caller_token: str | None, scope_name: str) -> str:
        """Return the caller name, or raise ContractAuthorizationError.

        An empty configured token is treated as a disabled caller so an unset
        secret environment variable cannot open registration.
        """
        if not self.callers:
            raise ContractAuthorizationError("No contract registration callers are configured; registration is disabled")

        name = (caller_name or "").strip()
        token = caller_token or ""
        caller = next((candidate for candidate in self.callers if candidate.name == name), None)
        if caller is None:
            raise ContractAuthorizationError(f"Caller '{name or '<missing>'}' is not authorized to register contracts")
        if not caller.token:
            raise ContractAuthorizationError(f"Caller '{caller.name}' has no registration token configured")
        if not token or not hmac.compare_digest(caller.token, token):
            raise ContractAuthorizationError(f"Caller '{caller.name}' supplied an invalid registration token")
        if not caller.allows(scope_name):
            raise ContractAuthorizationError(f"Caller '{caller.name}' is not authorized for scope '{scope_name}'")
        return caller.name


def _to_callers(raw_callers: Sequence[object]) -> list[ContractCaller]:
    """Convert configured caller entries into ContractCaller instances.

    Entries without a name or without any scope prefix are skipped, and the
    remaining invalid entries are logged. Registration stays closed when no
    usable caller is left.
    """
    callers: list[ContractCaller] = []
    for entry in raw_callers:
        if not isinstance(entry, dict):
            logger.warning(f"Ignoring contract registration caller entry that is not a mapping: {entry!r}")
            continue
        name = str(entry.get("name") or "").strip()
        prefixes = tuple(str(prefix).strip() for prefix in entry.get("scope_prefixes") or () if str(prefix).strip())
        if not name or not prefixes:
            logger.warning(f"Ignoring contract registration caller without a name or scope prefixes: {entry!r}")
            continue
        callers.append(
            ContractCaller(
                name=name,
                token=str(entry.get("token") or ""),
                scope_prefixes=prefixes,
            )
        )
    return callers
