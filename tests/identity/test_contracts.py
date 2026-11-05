"""Unit tests for provider-scope business-key contract rules.

No database and no live config store are required. Config-dependent tests swap
in ``MockConfigProvider`` and restore the default provider afterwards.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from pydantic import ValidationError

from src.configuration import (
    ConfigFactory,
    MockConfigProvider,
    get_config_provider,
    reset_config_provider,
    set_config_provider,
)
from src.identity.contracts import (
    ContractAuthorizationError,
    ContractCaller,
    ContractRegistrationPolicy,
    IdentityContractConflict,
    IdentityContractRequired,
    is_provider_scope,
    require_provider_scope,
)
from src.identity.models import EntityContractConflict, EntityContractDeclaration

CALLER = ContractCaller(name="shape-shifter", token="s3cret", scope_prefixes=("provider://",))


@pytest.fixture
def configured_provider(request) -> Iterator[MockConfigProvider]:
    """Install a mock provider for one config payload and restore the default after."""
    payload = getattr(request, "param", {})
    provider = MockConfigProvider(ConfigFactory().load(source=payload))
    previous = set_config_provider(provider)
    try:
        yield provider
    finally:
        set_config_provider(previous)


# ---------------------------------------------------------------------------
# Scope rules
# ---------------------------------------------------------------------------


class TestScopeRules:
    def test_provider_scope_prefix_is_detected(self) -> None:
        assert is_provider_scope("provider://gbif/occurrence") is True

    def test_internal_scope_is_not_a_provider_scope(self) -> None:
        assert is_provider_scope("sead://admin") is False

    def test_provider_scope_detection_ignores_surrounding_spaces(self) -> None:
        assert is_provider_scope("  provider://gbif/occurrence  ") is True

    def test_require_provider_scope_returns_trimmed_name(self) -> None:
        assert require_provider_scope("  provider://gbif/occurrence ") == "provider://gbif/occurrence"

    def test_require_provider_scope_rejects_internal_scope(self) -> None:
        with pytest.raises(ValueError, match="provider scopes only"):
            require_provider_scope("sead://reconciliation")

    def test_require_provider_scope_rejects_blank_name(self) -> None:
        with pytest.raises(ValueError, match="must not be blank"):
            require_provider_scope("   ")


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


class TestContractRegistrationPolicy:
    def test_authorized_caller_is_accepted(self) -> None:
        policy = ContractRegistrationPolicy(callers=(CALLER,))

        caller = policy.authorize("shape-shifter", "s3cret", "provider://gbif/occurrence")

        assert caller == "shape-shifter"

    def test_no_configured_callers_rejects_every_request(self) -> None:
        policy = ContractRegistrationPolicy()

        with pytest.raises(ContractAuthorizationError, match="No contract registration callers"):
            policy.authorize("shape-shifter", "s3cret", "provider://gbif/occurrence")

    def test_unknown_caller_is_rejected(self) -> None:
        policy = ContractRegistrationPolicy(callers=(CALLER,))

        with pytest.raises(ContractAuthorizationError, match="not authorized"):
            policy.authorize("other-client", "s3cret", "provider://gbif/occurrence")

    def test_missing_caller_header_is_rejected(self) -> None:
        policy = ContractRegistrationPolicy(callers=(CALLER,))

        with pytest.raises(ContractAuthorizationError, match="not authorized"):
            policy.authorize(None, "s3cret", "provider://gbif/occurrence")

    def test_wrong_token_is_rejected(self) -> None:
        policy = ContractRegistrationPolicy(callers=(CALLER,))

        with pytest.raises(ContractAuthorizationError, match="invalid registration token"):
            policy.authorize("shape-shifter", "wrong", "provider://gbif/occurrence")

    def test_missing_token_header_is_rejected(self) -> None:
        policy = ContractRegistrationPolicy(callers=(CALLER,))

        with pytest.raises(ContractAuthorizationError, match="invalid registration token"):
            policy.authorize("shape-shifter", None, "provider://gbif/occurrence")

    def test_caller_without_configured_token_is_rejected(self) -> None:
        policy = ContractRegistrationPolicy(callers=(ContractCaller("shape-shifter", "", ("provider://",)),))

        with pytest.raises(ContractAuthorizationError, match="no registration token configured"):
            policy.authorize("shape-shifter", "", "provider://gbif/occurrence")

    def test_scope_outside_caller_prefixes_is_rejected(self) -> None:
        policy = ContractRegistrationPolicy(callers=(ContractCaller("shape-shifter", "s3cret", ("provider://gbif/",)),))

        with pytest.raises(ContractAuthorizationError, match="not authorized for scope"):
            policy.authorize("shape-shifter", "s3cret", "provider://other/occurrence")

    @pytest.mark.parametrize(
        "configured_provider",
        [
            {
                "identity": {
                    "contract_registration": {
                        "callers": [
                            {"name": "shape-shifter", "token": "s3cret", "scope_prefixes": ["provider://"]},
                            {"name": "", "token": "x", "scope_prefixes": ["provider://"]},
                            {"name": "no-prefixes", "token": "x", "scope_prefixes": []},
                            "not-a-mapping",
                        ]
                    }
                }
            }
        ],
        indirect=True,
    )
    def test_from_config_keeps_only_usable_callers(self, configured_provider: MockConfigProvider) -> None:
        policy = ContractRegistrationPolicy.from_config()

        assert [caller.name for caller in policy.callers] == ["shape-shifter"]
        assert policy.authorize("shape-shifter", "s3cret", "provider://gbif/occurrence") == "shape-shifter"

    @pytest.mark.parametrize("configured_provider", [{}], indirect=True)
    def test_from_config_without_callers_keeps_registration_closed(self, configured_provider: MockConfigProvider) -> None:
        policy = ContractRegistrationPolicy.from_config()

        assert policy.callers == ()
        with pytest.raises(ContractAuthorizationError, match="No contract registration callers"):
            policy.authorize("shape-shifter", "s3cret", "provider://gbif/occurrence")

    def test_from_config_without_config_store_keeps_registration_closed(self) -> None:
        previous = get_config_provider()
        reset_config_provider()
        try:
            policy = ContractRegistrationPolicy.from_config()
        finally:
            set_config_provider(previous)

        assert policy.callers == ()


# ---------------------------------------------------------------------------
# Contract declarations
# ---------------------------------------------------------------------------


class TestEntityContractDeclaration:
    def test_key_names_are_trimmed_and_order_is_kept(self) -> None:
        declaration = EntityContractDeclaration(entity_type=" site ", business_keys=[" site_name ", "country"])

        assert declaration.entity_type == "site"
        assert declaration.business_keys == ["site_name", "country"]

    def test_blank_entity_type_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="entity_type must not be blank"):
            EntityContractDeclaration(entity_type="  ", business_keys=["site_name"])

    def test_empty_key_list_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EntityContractDeclaration(entity_type="site", business_keys=[])

    def test_blank_key_name_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="business key names must not be blank"):
            EntityContractDeclaration(entity_type="site", business_keys=["site_name", " "])

    def test_repeated_key_name_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="business key names must be unique"):
            EntityContractDeclaration(entity_type="site", business_keys=["site_name", "site_name"])


# ---------------------------------------------------------------------------
# Error payloads
# ---------------------------------------------------------------------------


class TestContractErrors:
    def test_conflict_lists_registered_and_submitted_keys(self) -> None:
        conflict = EntityContractConflict(
            entity_type="site",
            registered=["site_name", "country"],
            submitted=["country", "site_name"],
        )

        error = IdentityContractConflict("provider://gbif/occurrence", [conflict])

        assert error.scope_name == "provider://gbif/occurrence"
        assert error.conflicts == [conflict]
        assert "registered" in str(error)
        assert "submitted" in str(error)

    def test_required_error_lists_missing_entity_types(self) -> None:
        error = IdentityContractRequired("provider://gbif/occurrence", ["site", "sample_group"])

        assert error.missing_entity_types == ["site", "sample_group"]
        assert "site, sample_group" in str(error)
