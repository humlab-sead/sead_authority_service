"""Verify reconciliation candidates against SEAD and report match readiness."""

from urllib.parse import urlsplit

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
from src.strategies.query import BaseRepository
from src.strategies.site import SiteRepository
from src.strategies.strategy import ReconciliationStrategy, Strategies

DATABASE_ERRORS = (psycopg.Error, PoolClosed, PoolTimeout)


class UnsupportedReadinessType(ValueError):
    """Raised when a reconciliation type has no supported readiness check."""


def _configured_id_base() -> str | None:
    value = ConfigValue("options:id_base").resolve()
    return value if isinstance(value, str) and value else None


def _valid_id_base(id_base: str | None) -> bool:
    if not id_base or "?" in id_base or "#" in id_base:
        return False
    try:
        parsed = urlsplit(id_base)
    except ValueError:
        return False
    return bool(parsed.scheme and parsed.netloc and parsed.path.endswith("/") and not parsed.query and not parsed.fragment)


def _site_strategy(entity_type: str, policy: IdentityPolicy) -> type[ReconciliationStrategy] | None:
    strategy_cls = Strategies.items.get(entity_type)
    if entity_type != "site" or strategy_cls is None or not policy.supports(entity_type, "bind_existing"):
        return None
    return strategy_cls


def _site_id_from_candidate(candidate_id: str, entity_type: str, id_base: str | None) -> int | None:
    if not _valid_id_base(id_base) or "?" in candidate_id or "#" in candidate_id:
        return None
    try:
        base = urlsplit(id_base)
        candidate = urlsplit(candidate_id)
    except ValueError:
        return None
    if (
        not candidate.scheme
        or not candidate.netloc
        or candidate.scheme.casefold() != base.scheme.casefold()
        or candidate.netloc.casefold() != base.netloc.casefold()
        or candidate.query
        or candidate.fragment
        or not candidate.path.startswith(base.path)
    ):
        return None

    relative_path = candidate.path[len(base.path) :]
    type_segment, separator, id_segment = relative_path.partition("/")
    if not separator or type_segment != entity_type or "/" in id_segment or not id_segment.isascii() or not id_segment.isdecimal():
        return None
    try:
        aggregate_id = int(id_segment)
    except ValueError:
        return None
    return aggregate_id if aggregate_id > 0 else None


async def verify_candidate_batch(items: list[CandidateVerificationItem]) -> list[CandidateVerificationResult]:
    """Return one ordered, read-only SEAD existence result for each candidate."""
    policy = IdentityPolicy()
    id_base = _configured_id_base()
    results: list[CandidateVerificationResult] = []

    for item in items:
        strategy_cls = _site_strategy(item.type, policy)
        if strategy_cls is None:
            results.append(CandidateVerificationResult(type=item.type, id=item.id, outcome="unsupported_type"))
            continue

        site_id = _site_id_from_candidate(item.id, item.type, id_base)
        if site_id is None:
            results.append(CandidateVerificationResult(type=item.type, id=item.id, outcome="invalid_candidate"))
            continue

        repository: BaseRepository = strategy_cls().get_repository()
        if not isinstance(repository, SiteRepository):
            results.append(CandidateVerificationResult(type=item.type, id=item.id, outcome="unsupported_type"))
            continue

        if await repository.site_exists(site_id):
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
