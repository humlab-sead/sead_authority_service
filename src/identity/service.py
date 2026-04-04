"""SIMS Identity Service — core operations.

Orchestrates the four operations from IMPLEMENTATION_VIEW § Core Operations:

  1. resolve_identity  — upsert Source Identity, check for existing Binding
  2. bind              — create Binding Set, mint Tracked Identities, create Bindings
  3. confirm_binding_set — transition proposed → confirmed
  4. associate_change_request — link confirmed set to a Sqitch CR name
  5. detect_change     — opaque content-hash comparison (FR-24)

All repository and policy dependencies are injected via the constructor,
making the service fully unit-testable without a live database.

Usage example::

    service = IdentityService()                              # default repos + policy
    scope = await service.get_or_create_scope("sead://reconciliation")

    outcome = await service.resolve_identity(
        scope.scope_uuid,
        ResolutionRequest(
            entity_type="site",
            primary_signal=IdentitySignal(identity_type=IdentityType.BUSINESS_KEY, identity_value="ABC-001"),
        ),
    )
    bsr = await service.bind(submission_uuid=..., outcomes=[outcome])
    # bsr.lifecycle_state == BindingSetState.CONFIRMED  (auto-confirmed for provider-owned)
"""

from __future__ import annotations

from uuid import UUID

from loguru import logger

from src.identity.models import (
    Binding,
    BindingSet,
    BindingSetResponse,
    ChangeDetectionRequest,
    ChangeDetectionResult,
    IdentitySignal,
    ResolutionOutcome,
    ResolutionRequest,
    SourceIdentity,
    SourceScope,
)
from src.identity.policy import EntityPolicy, IdentityPolicy
from src.identity.repository import (
    BindingRepository,
    BindingSetRepository,
    SourceIdentityRepository,
    SourceScopeRepository,
    SubmissionRepository,
    TrackedIdentityRepository,
)
from src.identity.types import (
    BindingMethod,
    BindingSetState,
    ChangeOutcome,
    IdentityType,
    TrackedIdentityState,
)


class IdentityService:
    """Core SIMS service.

    All arguments are optional: if omitted, fresh repository/policy instances
    are created using the project defaults. Pass explicit instances in tests
    to keep tests hermetic.

    Parameters
    ----------
    scope_repo, submission_repo, source_identity_repo,
    tracked_identity_repo, binding_set_repo, binding_repo:
        Repository instances. Default to their own constructors.
    policy:
        Identity policy engine. Defaults to ``IdentityPolicy()`` which
        reads ``config/identity_policy.yml``.
    """

    def __init__(
        self,
        scope_repo: SourceScopeRepository | None = None,
        submission_repo: SubmissionRepository | None = None,
        source_identity_repo: SourceIdentityRepository | None = None,
        tracked_identity_repo: TrackedIdentityRepository | None = None,
        binding_set_repo: BindingSetRepository | None = None,
        binding_repo: BindingRepository | None = None,
        policy: IdentityPolicy | None = None,
    ) -> None:
        self.scope_repo = scope_repo or SourceScopeRepository()
        self.submission_repo = submission_repo or SubmissionRepository()
        self.source_identity_repo = source_identity_repo or SourceIdentityRepository()
        self.tracked_identity_repo = tracked_identity_repo or TrackedIdentityRepository()
        self.binding_set_repo = binding_set_repo or BindingSetRepository()
        self.binding_repo = binding_repo or BindingRepository()
        self.policy = policy or IdentityPolicy()

    # ------------------------------------------------------------------
    # Scope helpers
    # ------------------------------------------------------------------

    async def get_or_create_scope(
        self,
        scope_name: str,
        description: str | None = None,
        created_by: str | None = None,
    ) -> SourceScope:
        """Return the named scope, creating it if it does not exist."""
        existing = await self.scope_repo.get_by_name(scope_name)
        if existing:
            return existing
        created = await self.scope_repo.create(scope_name, description=description, created_by=created_by)
        logger.info(f"Created scope '{scope_name}' ({created.scope_uuid})")
        return created

    # ------------------------------------------------------------------
    # Operation 1 — Resolve Identity
    # ------------------------------------------------------------------

    async def resolve_identity(
        self,
        scope_uuid: UUID,
        request: ResolutionRequest,
        submission_uuid: UUID | None = None,
        created_by: str | None = None,
    ) -> ResolutionOutcome:
        """Resolve one domain entity within a Source Scope.

        Steps:
        1. Upsert the Source Identity (idempotent per uniqueness key).
        2. Link it to the Submission, if provided.
        3. Check for an existing confirmed Binding.
        4. Return ``outcome='matched'`` with the Tracked Identity UUID, or
           ``outcome='new'`` (allocation deferred to the Bind step).

        Implements FR-12 and FR-13 (idempotency).
        """
        ep: EntityPolicy = self.policy.get_entity_policy(request.entity_type)
        primary = request.primary_signal

        # 1. Upsert Source Identity
        source_identity = await self.source_identity_repo.create_or_get(
            scope_uuid=scope_uuid,
            entity_type=request.entity_type,
            identity_type=primary.identity_type.value,
            identity_value=primary.identity_value,
            identity_signals=_signals_to_dict(request),
            created_by=created_by,
        )

        # 2. Link to submission
        if submission_uuid is not None:
            await self.source_identity_repo.link_to_submission(submission_uuid, source_identity.source_identity_uuid)

        # 3. Check for an existing confirmed binding
        existing = await self.binding_repo.find_confirmed_binding(source_identity.source_identity_uuid)
        if existing is not None:
            binding, _ = existing
            logger.debug(
                f"resolve_identity: matched existing binding "
                f"source={source_identity.source_identity_uuid} → tracked={binding.tracked_identity_uuid}"
            )
            return ResolutionOutcome(
                source_identity_uuid=source_identity.source_identity_uuid,
                entity_type=request.entity_type,
                outcome="matched",
                tracked_identity_uuid=binding.tracked_identity_uuid,
            )

        # 4. No existing binding — allocation deferred
        logger.debug(
            f"resolve_identity: no existing binding for source={source_identity.source_identity_uuid}, outcome=new"
        )
        return ResolutionOutcome(
            source_identity_uuid=source_identity.source_identity_uuid,
            entity_type=request.entity_type,
            outcome="new",
            tracked_identity_uuid=None,
        )

    # ------------------------------------------------------------------
    # Operation 2 — Bind
    # ------------------------------------------------------------------

    async def bind(
        self,
        submission_uuid: UUID | None,
        outcomes: list[ResolutionOutcome],
        created_by: str | None = None,
    ) -> BindingSetResponse:
        """Create a Binding Set from resolution outcomes and apply policy.

        For each outcome:
        - ``matched``: creates a Binding to the existing Tracked Identity.
        - ``new``: mints a new Tracked Identity if policy allows, then creates a Binding.

        Auto-confirms the Binding Set if *all* entity types in the batch have
        ``auto_confirm=True`` in the identity policy (D6 — provider-owned entities).

        Returns the BindingSetResponse including the final lifecycle state.
        """
        if not outcomes:
            raise ValueError("bind() requires at least one ResolutionOutcome")

        # Create the proposed Binding Set
        binding_set = await self.binding_set_repo.create(submission_uuid=submission_uuid, created_by=created_by)
        bindings: list[Binding] = []

        for outcome in outcomes:
            ep = self.policy.get_entity_policy(outcome.entity_type)
            binding = await self._bind_single(outcome, binding_set.binding_set_uuid, ep, created_by)
            if binding is not None:
                bindings.append(binding)

        # Auto-confirm if all entity types in this batch permit it
        should_auto_confirm = all(
            self.policy.get_entity_policy(o.entity_type).auto_confirm for o in outcomes
        )

        if should_auto_confirm:
            binding_set = await self.binding_set_repo.transition(binding_set.binding_set_uuid, BindingSetState.CONFIRMED)
            logger.info(f"Binding set {binding_set.binding_set_uuid} auto-confirmed ({len(bindings)} bindings)")
        else:
            logger.info(f"Binding set {binding_set.binding_set_uuid} remains proposed — awaiting manual confirmation")

        return _to_binding_set_response(binding_set, binding_count=len(bindings))

    async def _bind_single(
        self,
        outcome: ResolutionOutcome,
        binding_set_uuid: UUID,
        ep: EntityPolicy,
        created_by: str | None,
    ) -> Binding | None:
        """Create one Binding within a set for a single ResolutionOutcome."""
        if outcome.outcome == "matched":
            assert outcome.tracked_identity_uuid is not None
            # Determine binding method from how the source identity was constructed
            source = await self.source_identity_repo.get(outcome.source_identity_uuid)
            method = _infer_method_from_match(source)
            return await self.binding_repo.create(
                binding_set_uuid=binding_set_uuid,
                source_identity_uuid=outcome.source_identity_uuid,
                tracked_identity_uuid=outcome.tracked_identity_uuid,
                method=method,
                created_by=created_by,
            )

        # outcome == "new"
        if not ep.allow_allocation:
            logger.warning(
                f"bind: allocation blocked by policy for entity_type={outcome.entity_type} "
                f"(source={outcome.source_identity_uuid})"
            )
            return None

        tracked = await self.tracked_identity_repo.mint(entity_type=outcome.entity_type, created_by=created_by)
        return await self.binding_repo.create(
            binding_set_uuid=binding_set_uuid,
            source_identity_uuid=outcome.source_identity_uuid,
            tracked_identity_uuid=tracked.tracked_identity_uuid,
            method=BindingMethod.ALLOCATED,
            provenance={"allocation_policy": ep.entity_subtype},
            created_by=created_by,
        )

    # ------------------------------------------------------------------
    # Submission helper
    # ------------------------------------------------------------------

    async def create_submission(
        self,
        scope_uuid: UUID,
        submission_name: str,
        created_by: str | None = None,
    ):
        """Create and return a new Submission within the given scope."""
        return await self.submission_repo.create(
            scope_uuid=scope_uuid,
            submission_name=submission_name,
            created_by=created_by,
        )

    # ------------------------------------------------------------------
    # Convenience: resolve + bind in one call
    # ------------------------------------------------------------------

    async def resolve_and_bind(
        self,
        scope_uuid: UUID,
        requests: list[ResolutionRequest],
        submission_uuid: UUID | None = None,
        created_by: str | None = None,
    ) -> BindingSetResponse:
        """Shorthand for resolve_identity × N → bind."""
        outcomes = []
        for req in requests:
            outcome = await self.resolve_identity(scope_uuid, req, submission_uuid=submission_uuid, created_by=created_by)
            outcomes.append(outcome)
        return await self.bind(submission_uuid=submission_uuid, outcomes=outcomes, created_by=created_by)

    # ------------------------------------------------------------------
    # Operation 3 — Confirm Binding Set
    # ------------------------------------------------------------------

    async def confirm_binding_set(self, binding_set_uuid: UUID) -> BindingSet | None:
        """Manually transition a proposed Binding Set to confirmed.

        This is a no-op if the set was already auto-confirmed at bind time.
        Returns the updated BindingSet, or None if not found.
        """
        result = await self.binding_set_repo.transition(binding_set_uuid, BindingSetState.CONFIRMED)
        if result:
            logger.info(f"Binding set {binding_set_uuid} confirmed")
        return result

    # ------------------------------------------------------------------
    # Operation 4 — Associate Change Request
    # ------------------------------------------------------------------

    async def associate_change_request(self, binding_set_uuid: UUID, cr_name: str) -> BindingSet | None:
        """Link a confirmed Binding Set to a Sqitch Change Request name (FR-25, FR-27).

        Only succeeds if the Binding Set is in the ``confirmed`` state.
        Returns the updated BindingSet, or None if not found or not confirmed.
        """
        result = await self.binding_set_repo.associate_change_request(binding_set_uuid, cr_name)
        if result:
            logger.info(f"Binding set {binding_set_uuid} associated with change request '{cr_name}'")
        else:
            logger.warning(
                f"associate_change_request: binding set {binding_set_uuid} not found or not confirmed"
            )
        return result

    # ------------------------------------------------------------------
    # Operation 5 — Detect Change
    # ------------------------------------------------------------------

    async def detect_change(self, request: ChangeDetectionRequest) -> ChangeDetectionResult:
        """Compare an incoming content hash against the stored hash for a Tracked Identity.

        Returns:
        - ``insert`` — no prior hash recorded for this Tracked Identity (new entity).
        - ``update`` — hash differs from the stored value (content changed).
        - ``skip``   — hash matches (content unchanged; no action needed).

        The stored hash is updated whenever the outcome is ``insert`` or ``update``
        so subsequent calls with the same hash return ``skip``.

        Implements FR-24 (aggregate-level change detection).
        """
        tracked = await self.tracked_identity_repo.get(request.tracked_identity_uuid)
        if tracked is None:
            raise LookupError(f"TrackedIdentity {request.tracked_identity_uuid} not found")

        previous_hash = tracked.content_hash

        if previous_hash is None:
            outcome = ChangeOutcome.INSERT
        elif previous_hash == request.content_hash:
            outcome = ChangeOutcome.SKIP
        else:
            outcome = ChangeOutcome.UPDATE

        if outcome != ChangeOutcome.SKIP:
            await self.tracked_identity_repo.update_content_hash(request.tracked_identity_uuid, request.content_hash)
            logger.debug(
                f"detect_change: {outcome.value} for tracked={request.tracked_identity_uuid} "
                f"(prev={previous_hash!r}, new={request.content_hash!r})"
            )

        return ChangeDetectionResult(
            tracked_identity_uuid=request.tracked_identity_uuid,
            outcome=outcome,
            previous_hash=previous_hash,
        )

    # ------------------------------------------------------------------
    # Lookup helpers (used by API layer)
    # ------------------------------------------------------------------

    async def get_binding_set(self, binding_set_uuid: UUID) -> BindingSetResponse | None:
        """Return a BindingSetResponse for the given UUID, or None."""
        binding_set = await self.binding_set_repo.get(binding_set_uuid)
        if binding_set is None:
            return None
        bindings = await self.binding_repo.list_by_set(binding_set_uuid)
        return _to_binding_set_response(binding_set, binding_count=len(bindings))

    async def list_scopes(self) -> list[SourceScope]:
        return await self.scope_repo.list_all()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _signals_to_dict(request: ResolutionRequest) -> dict | None:
    """Serialise all identity signals from a ResolutionRequest into a JSONB-compatible dict."""
    signals: dict = {
        "primary": {
            "identity_type": request.primary_signal.identity_type.value,
            "identity_value": request.primary_signal.identity_value,
        }
    }
    if request.primary_signal.signals:
        signals["primary"]["signals"] = request.primary_signal.signals
    if request.additional_signals:
        signals["additional"] = [
            {
                "identity_type": s.identity_type.value,
                "identity_value": s.identity_value,
                **({"signals": s.signals} if s.signals else {}),
            }
            for s in request.additional_signals
        ]
    return signals


def _infer_method_from_match(source: SourceIdentity | None) -> BindingMethod:
    """Determine the binding method from the source identity's identity type."""
    if source is None:
        return BindingMethod.BUSINESS_KEY
    try:
        id_type = IdentityType(source.identity_type)
    except ValueError:
        return BindingMethod.BUSINESS_KEY
    if id_type == IdentityType.UUID:
        return BindingMethod.UUID_ACCEPTED
    if id_type == IdentityType.AUTHORITY_KEY:
        return BindingMethod.EXACT_MATCH
    return BindingMethod.BUSINESS_KEY


def _to_binding_set_response(binding_set: BindingSet, binding_count: int) -> BindingSetResponse:
    return BindingSetResponse(
        binding_set_uuid=binding_set.binding_set_uuid,
        submission_uuid=binding_set.submission_uuid,
        lifecycle_state=binding_set.lifecycle_state,
        change_request_name=binding_set.change_request_name,
        binding_count=binding_count,
        created_at=binding_set.created_at,
        confirmed_at=binding_set.confirmed_at,
    )
