"""Verify reconciliation candidates against SEAD and report match readiness."""

import psycopg
from loguru import logger
from psycopg_pool import PoolClosed, PoolTimeout

from src.api.model import (
    CandidateVerificationItem,
    CandidateVerificationResult,
    ReconcileReadinessResponse,
)
from src.configuration import ConfigValue
from src.identity.policy import IdentityPolicy
from src.record_identifiers import parse_record_uri, valid_id_base
from src.record_selection import RecordSelectionPolicy, fetch_record_row, load_record_selection_policy
from src.strategies.site import SiteRepository
from src.strategies.strategy import ReconciliationStrategy, Strategies

DATABASE_ERRORS = (psycopg.Error, PoolClosed, PoolTimeout)


class UnsupportedReadinessType(ValueError):
    """Raised when a reconciliation type has no supported readiness check."""


def _configured_id_base() -> str | None:
    value = ConfigValue("options:id_base").resolve()
    return value if isinstance(value, str) and value else None


def _valid_id_base(id_base: str | None) -> bool:
    return valid_id_base(id_base)


def _site_strategy(entity_type: str, policy: IdentityPolicy) -> type[ReconciliationStrategy] | None:
    strategy_cls = Strategies.items.get(entity_type)
    if entity_type != "site" or strategy_cls is None or not policy.supports(entity_type, "bind_existing"):
        return None
    return strategy_cls


def _site_id_from_candidate(candidate_id: str, entity_type: str, id_base: str | None) -> int | None:
    return parse_record_uri(candidate_id, entity_type, id_base)


async def _verify_pilot_item(
    item: CandidateVerificationItem, policy: RecordSelectionPolicy, id_base: str | None
) -> CandidateVerificationResult:
    """Verify one pilot candidate with the same typed lookup used by details."""
    flags = policy.types.get(item.type)
    if flags is None or not flags.export_verification:
        return CandidateVerificationResult(type=item.type, id=item.id, outcome="unsupported_type")

    target_id: int | None = parse_record_uri(item.id, item.type, id_base)
    if target_id is None:
        return CandidateVerificationResult(type=item.type, id=item.id, outcome="invalid_candidate")

    row = await fetch_record_row(item.type, target_id)
    if row is None:
        return CandidateVerificationResult(type=item.type, id=item.id, outcome="not_found")

    return CandidateVerificationResult(
        type=item.type,
        id=item.id,
        outcome="exists",
        entity_type=item.type,
        aggregate_id=target_id,
    )


async def verify_candidate_batch(items: list[CandidateVerificationItem]) -> list[CandidateVerificationResult]:
    """Return one ordered, read-only SEAD existence result for each candidate."""
    policy = IdentityPolicy()
    selection_policy: RecordSelectionPolicy | None = None
    id_base = _configured_id_base()
    site_strategy_cls = _site_strategy("site", policy) if any(item.type == "site" for item in items) else None
    site_repository: SiteRepository | None = None
    site_repository_checked = False
    results: list[CandidateVerificationResult] = []

    for item in items:
        if item.type != "site":
            if selection_policy is None:
                selection_policy = load_record_selection_policy()
            if item.type in selection_policy.types:
                results.append(await _verify_pilot_item(item, selection_policy, id_base))
                continue
            results.append(CandidateVerificationResult(type=item.type, id=item.id, outcome="unsupported_type"))
            continue

        if site_strategy_cls is None:
            results.append(CandidateVerificationResult(type=item.type, id=item.id, outcome="unsupported_type"))
            continue

        site_id = _site_id_from_candidate(item.id, item.type, id_base)
        if site_id is None:
            results.append(CandidateVerificationResult(type=item.type, id=item.id, outcome="invalid_candidate"))
            continue

        if not site_repository_checked:
            repository = site_strategy_cls().get_repository()
            site_repository = repository if isinstance(repository, SiteRepository) else None
            site_repository_checked = True

        if site_repository is None:
            results.append(CandidateVerificationResult(type=item.type, id=item.id, outcome="unsupported_type"))
            continue

        if await site_repository.site_exists(site_id):
            results.append(
                CandidateVerificationResult(
                    type=item.type,
                    id=item.id,
                    outcome="exists",
                    entity_type="site",
                    aggregate_id=site_id,
                )
            )
        else:
            results.append(CandidateVerificationResult(type=item.type, id=item.id, outcome="not_found"))

    return results


async def get_reconciliation_readiness(entity_type: str) -> ReconcileReadinessResponse:
    """Run the registered strategy's database-backed query before reporting readiness."""
    strategy_cls = _site_strategy(entity_type, IdentityPolicy())
    if strategy_cls is None:
        raise UnsupportedReadinessType(f"Unsupported reconciliation type '{entity_type}'")

    id_base = _configured_id_base()
    if not _valid_id_base(id_base):
        return ReconcileReadinessResponse(type=entity_type, ready=False, reason="The options:id_base setting is missing or invalid.")

    try:
        await strategy_cls().find_candidates(query="readiness", properties={}, limit=1)
    except DATABASE_ERRORS as exc:
        logger.exception("Database-backed reconciliation readiness failed for type '{}': {}", entity_type, exc)
        return ReconcileReadinessResponse(
            type=entity_type,
            ready=False,
            reason="The database-backed match query failed. Check the SEAD database and the configured match function.",
        )

    return ReconcileReadinessResponse(type=entity_type, ready=True, reason=None)
