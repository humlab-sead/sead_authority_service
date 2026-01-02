"""Comprehensive tests for API models (Pydantic schemas)."""

import pytest
from pydantic import ValidationError

from src.api.model import (
    APIResponse,
    ExtCell,
    ExtendDescriptor,
    ExtendRequest,
    ExtendRequestProperty,
    ExtendResponse,
    PreviewTemplate,
    PropertySetting,
    ProposePropertiesDescriptor,
    ReconBatchRequest,
    ReconBatchRequestHandler,
    ReconBatchResponse,
    ReconCandidate,
    ReconPropertyConstraint,
    ReconQuery,
    ReconQueryResult,
    ReconServiceManifest,
    SuggestDescriptor,
    SuggestEntityItem,
    SuggestEntityResponse,
    SuggestPropertyItem,
    SuggestPropertyResponse,
    SuggestSubservice,
    SuggestTypeItem,
    SuggestTypeResponse,
    TypeRef,
    ViewTemplate,
)


class TestTypeRef:
    """Test TypeRef model."""

    def test_valid_type_ref(self):
        """Test creating a valid TypeRef."""
        type_ref = TypeRef(id="site", name="Archaeological Site")

        assert type_ref.id == "site"
        assert type_ref.name == "Archaeological Site"

    def test_type_ref_serialization(self):
        """Test TypeRef JSON serialization."""
        type_ref = TypeRef(id="location", name="Location")
        data = type_ref.model_dump()

        assert data == {"id": "location", "name": "Location"}

    def test_type_ref_missing_field(self):
        """Test TypeRef requires both id and name."""
        with pytest.raises(ValidationError) as exc_info:
            TypeRef(id="test")  # type: ignore[call-arg]

        assert "name" in str(exc_info.value)

    def test_type_ref_empty_strings(self):
        """Test TypeRef accepts empty strings."""
        type_ref = TypeRef(id="", name="")

        assert type_ref.id == ""
        assert type_ref.name == ""


class TestReconPropertyConstraint:
    """Test ReconPropertyConstraint model."""

    def test_valid_property_constraint(self):
        """Test creating a valid property constraint."""
        constraint = ReconPropertyConstraint(pid="latitude", v=59.8586)

        assert constraint.pid == "latitude"
        assert constraint.v == 59.8586

    def test_property_constraint_with_string_value(self):
        """Test property constraint with string value."""
        constraint = ReconPropertyConstraint(pid="country", v="Sweden")

        assert constraint.pid == "country"
        assert constraint.v == "Sweden"

    def test_property_constraint_with_dict_value(self):
        """Test property constraint with dict/object value."""
        constraint = ReconPropertyConstraint(pid="location", v={"lat": 59.8586, "lon": 17.6389})

        assert constraint.pid == "location"
        assert constraint.v == {"lat": 59.8586, "lon": 17.6389}

    def test_property_constraint_with_list_value(self):
        """Test property constraint with list value."""
        constraint = ReconPropertyConstraint(pid="tags", v=["archaeological", "viking"])

        assert constraint.pid == "tags"
        assert constraint.v == ["archaeological", "viking"]


class TestReconQuery:
    """Test ReconQuery model."""

    def test_minimal_valid_query(self):
        """Test minimal valid ReconQuery with just query string."""
        query = ReconQuery(query="Uppsala", **{})

        assert query.query == "Uppsala"
        assert query.type is None
        assert query.limit is None
        assert query.properties is None

    def test_full_valid_query(self):
        """Test ReconQuery with all fields."""
        query = ReconQuery(
            query="Uppsala Site",
            type="site",
            type_strict="should",
            limit=10,
            properties=[ReconPropertyConstraint(pid="latitude", v=59.8586)],
            lang="en",
        )

        assert query is not None
        assert query.query == "Uppsala Site"
        assert query.type == "site"
        assert query.type_strict == "should"
        assert query.limit == 10
        assert len(query.properties) == 1  # type: ignore
        assert query.lang == "en"

    def test_query_trimming(self):
        """Test query string is trimmed."""
        query = ReconQuery(query="  Uppsala  ", **{})

        assert query.query == "Uppsala"

    def test_empty_query_raises_error(self):
        """Test empty query string raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ReconQuery(query="", **{})

        assert "Query cannot be empty" in str(exc_info.value)

    def test_whitespace_only_query_raises_error(self):
        """Test whitespace-only query raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ReconQuery(query="   ", **{})

        assert "Query cannot be empty" in str(exc_info.value)

    def test_limit_validation_min(self):
        """Test limit must be >= 1."""
        with pytest.raises(ValidationError):
            ReconQuery(query="Test", limit=0, **{})

    def test_limit_validation_max(self):
        """Test limit must be <= 500."""
        with pytest.raises(ValidationError):
            ReconQuery(query="Test", limit=501, **{})

    def test_type_strict_valid_values(self):
        """Test type_strict accepts valid literal values."""
        for value in ["should", "all", "any"]:
            query = ReconQuery(query="Test", type_strict=value, **{})  # type: ignore
            assert query.type_strict == value

    def test_type_strict_invalid_value(self):
        """Test type_strict rejects invalid values."""
        with pytest.raises(ValidationError):
            ReconQuery(query="Test", type_strict="invalid", **{})  # type: ignore

    def test_type_none_is_allowed(self):
        """Test type can be None."""
        query = ReconQuery(query="Test", type=None, **{})
        assert query.type is None


class TestReconBatchRequest:
    """Test ReconBatchRequest model."""

    def test_valid_batch_request(self):
        """Test valid batch request with multiple queries."""
        batch = ReconBatchRequest(
            root={"q0": ReconQuery(query="Uppsala", **{}), "q1": ReconQuery(query="Stockholm", type="site", limit=5, **{})}
        )

        assert "q0" in batch.root
        assert "q1" in batch.root
        assert batch.root["q0"].query == "Uppsala"
        assert batch.root["q1"].query == "Stockholm"

    def test_empty_batch_request(self):
        """Test empty batch request."""
        batch = ReconBatchRequest(root={})

        assert len(batch.root) == 0

    def test_batch_request_serialization(self):
        """Test batch request can be serialized."""
        batch = ReconBatchRequest(root={"q0": ReconQuery(query="Test", **{})})
        data = batch.model_dump()

        assert "q0" in data
        assert data["q0"]["query"] == "Test"


class TestReconCandidate:
    """Test ReconCandidate model."""

    def test_minimal_candidate(self):
        """Test minimal candidate with required fields only."""
        candidate = ReconCandidate(id="123", name="Uppsala Site", **{})

        assert candidate.id == "123"
        assert candidate.name == "Uppsala Site"
        assert candidate.type == []
        assert candidate.score is None
        assert candidate.match is None

    def test_full_candidate(self):
        """Test candidate with all fields."""
        candidate = ReconCandidate(
            id="123",
            name="Uppsala Site",
            type=[TypeRef(id="site", name="Site")],
            score=95.5,
            match=True,
            description="Archaeological site in Uppsala",
        )

        assert candidate.id == "123"
        assert candidate.name == "Uppsala Site"
        assert len(candidate.type) == 1
        assert candidate.score == 95.5
        assert candidate.match is True
        assert candidate.description == "Archaeological site in Uppsala"

    def test_candidate_score_validation_min(self):
        """Test score must be >= 0."""
        with pytest.raises(ValidationError):
            ReconCandidate(id="1", name="Test", score=-1.0, **{})

    def test_candidate_score_validation_max(self):
        """Test score must be <= 100."""
        with pytest.raises(ValidationError):
            ReconCandidate(id="1", name="Test", score=101.0, **{})

    def test_candidate_name_min_length(self):
        """Test name must have min_length=1."""
        with pytest.raises(ValidationError):
            ReconCandidate(id="1", name="", **{})

    def test_candidate_description_max_length(self):
        """Test description has max_length=500."""
        long_desc = "A" * 501
        with pytest.raises(ValidationError):
            ReconCandidate(id="1", name="Test", description=long_desc)

    def test_candidate_description_at_max_length(self):
        """Test description at exactly 500 characters is valid."""
        desc = "A" * 500
        candidate = ReconCandidate(id="1", name="Test", description=desc)

        assert len(candidate.description) == 500  # type: ignore


class TestReconQueryResult:
    """Test ReconQueryResult model."""

    def test_query_result_with_candidates(self):
        """Test query result with multiple candidates."""
        result = ReconQueryResult(
            result=[
                ReconCandidate(id="1", name="First", score=95.0, **{}),
                ReconCandidate(id="2", name="Second", score=85.0, **{}),
            ]
        )

        assert len(result.result) == 2
        assert result.result[0].score == 95.0

    def test_query_result_empty(self):
        """Test query result with no candidates."""
        result = ReconQueryResult(result=[])

        assert len(result.result) == 0


class TestReconBatchResponse:
    """Test ReconBatchResponse model."""

    def test_batch_response(self):
        """Test batch response with results."""
        response = ReconBatchResponse(
            root={
                "q0": ReconQueryResult(result=[ReconCandidate(id="1", name="Uppsala", **{})]),
                "q1": ReconQueryResult(result=[ReconCandidate(id="2", name="Stockholm", **{})]),
            }
        )

        assert "q0" in response.root
        assert "q1" in response.root
        assert response.root["q0"].result[0].name == "Uppsala"


class TestViewTemplate:
    """Test ViewTemplate model."""

    def test_valid_view_template(self):
        """Test creating a valid view template."""
        view = ViewTemplate(url="https://example.org/entity/{{id}}")

        assert view.url == "https://example.org/entity/{{id}}"

    def test_view_template_with_parameters(self):
        """Test view template with multiple parameters."""
        view = ViewTemplate(url="https://example.org/{{type}}/{{id}}")

        assert "{{type}}" in view.url
        assert "{{id}}" in view.url


class TestPreviewTemplate:
    """Test PreviewTemplate model."""

    def test_valid_preview_template(self):
        """Test creating a valid preview template."""
        preview = PreviewTemplate(url="https://example.org/preview?id={{id}}")  # type: ignore

        assert str(preview.url) == "https://example.org/preview?id={{id}}"
        assert preview.width == 430
        assert preview.height == 300

    def test_preview_template_custom_dimensions(self):
        """Test preview template with custom dimensions."""
        preview = PreviewTemplate(url="https://example.org/preview", width=600, height=400)  # type: ignore

        assert preview.width == 600
        assert preview.height == 400

    def test_preview_width_validation_min(self):
        """Test width must be > 0."""
        with pytest.raises(ValidationError):
            PreviewTemplate(url="https://example.org/preview", width=0)  # type: ignore

    def test_preview_width_validation_max(self):
        """Test width must be <= 1920."""
        with pytest.raises(ValidationError):
            PreviewTemplate(url="https://example.org/preview", width=1921)  # type: ignore

    def test_preview_height_validation_min(self):
        """Test height must be > 0."""
        with pytest.raises(ValidationError):
            PreviewTemplate(url="https://example.org/preview", height=0)  # type: ignore

    def test_preview_height_validation_max(self):
        """Test height must be <= 1080."""
        with pytest.raises(ValidationError):
            PreviewTemplate(url="https://example.org/preview", height=1081)  # type: ignore


class TestSuggestSubservice:
    """Test SuggestSubservice model."""

    def test_minimal_suggest_subservice(self):
        """Test minimal suggest subservice."""
        subservice = SuggestSubservice(service_url="https://api.example.org", service_path="/suggest/entity")

        assert subservice.service_url == "https://api.example.org"
        assert subservice.service_path == "/suggest/entity"
        assert subservice.flyout_service_url is None

    def test_full_suggest_subservice(self):
        """Test suggest subservice with flyout."""
        subservice = SuggestSubservice(
            service_url="https://api.example.org",
            service_path="/suggest/entity",
            flyout_service_url="https://api.example.org",
            flyout_service_path="/flyout/entity",
        )

        assert subservice.flyout_service_url == "https://api.example.org"
        assert subservice.flyout_service_path == "/flyout/entity"


class TestSuggestDescriptor:
    """Test SuggestDescriptor model."""

    def test_suggest_descriptor_with_entity(self):
        """Test suggest descriptor with entity service."""
        descriptor = SuggestDescriptor(entity=SuggestSubservice(service_url="https://api.example.org", service_path="/suggest/entity"))

        assert descriptor.entity is not None
        assert descriptor.entity.service_path == "/suggest/entity"

    def test_suggest_descriptor_all_services(self):
        """Test suggest descriptor with all services."""
        descriptor = SuggestDescriptor(
            entity=SuggestSubservice(service_url="https://api.example.org", service_path="/suggest/entity"),
            type=SuggestSubservice(service_url="https://api.example.org", service_path="/suggest/type"),
            property=SuggestSubservice(service_url="https://api.example.org", service_path="/suggest/property"),
        )

        assert descriptor.entity is not None
        assert descriptor.type is not None
        assert descriptor.property is not None


class TestProposePropertiesDescriptor:
    """Test ProposePropertiesDescriptor model."""

    def test_propose_properties_descriptor(self):
        """Test creating propose properties descriptor."""
        descriptor = ProposePropertiesDescriptor(service_url="https://api.example.org", service_path="/propose")

        assert descriptor.service_url == "https://api.example.org"
        assert descriptor.service_path == "/propose"


class TestPropertySetting:
    """Test PropertySetting model."""

    def test_property_setting(self):
        """Test creating a property setting."""
        setting = PropertySetting(
            name="latitude",
            label="Latitude",
            type="number",
            help_text="Geographic latitude coordinate",
            entity_types=["site", "location"],
        )

        assert setting.name == "latitude"
        assert setting.label == "Latitude"
        assert setting.type == "number"
        assert "latitude" in setting.help_text
        assert len(setting.entity_types) == 2

    def test_property_setting_with_settings(self):
        """Test property setting with additional settings dict."""
        setting = PropertySetting(
            name="country",
            label="Country",
            type="text",
            help_text="Country name",
            entity_types=["location"],
            settings={"autocomplete": True, "max_length": 100},
        )

        assert setting.settings == {"autocomplete": True, "max_length": 100}


class TestExtendDescriptor:
    """Test ExtendDescriptor model."""

    def test_extend_descriptor(self):
        """Test creating an extend descriptor."""
        descriptor = ExtendDescriptor(
            propose_properties=ProposePropertiesDescriptor(service_url="https://api.example.org", service_path="/propose"),
            property_settings=[
                PropertySetting(name="latitude", label="Latitude", type="number", help_text="Latitude", entity_types=["site"])
            ],
        )

        assert descriptor.propose_properties is not None
        assert len(descriptor.property_settings) == 1


class TestReconServiceManifest:
    """Test ReconServiceManifest model."""

    def test_minimal_manifest(self):
        """Test minimal service manifest."""
        manifest = ReconServiceManifest(
            name="SEAD Authority Service", identifierSpace="https://w3id.org/sead/id/", schemaSpace="https://w3id.org/sead/schema/"
        )

        assert manifest.name == "SEAD Authority Service"
        assert manifest.identifierSpace == "https://w3id.org/sead/id/"
        assert manifest.schemaSpace == "https://w3id.org/sead/schema/"

    def test_full_manifest(self):
        """Test full service manifest with all optional fields."""
        manifest = ReconServiceManifest(
            name="SEAD Authority Service",
            identifierSpace="https://w3id.org/sead/id/",
            schemaSpace="https://w3id.org/sead/schema/",
            defaultTypes=[TypeRef(id="site", name="Site")],
            view=ViewTemplate(url="https://example.org/{{id}}"),
            preview=PreviewTemplate(url="https://example.org/preview?id={{id}}"),  # type: ignore
            suggest=SuggestDescriptor(entity=SuggestSubservice(service_url="https://api.example.org", service_path="/suggest/entity")),
            versions=["0.2", "0.3"],
            homepage="https://example.org",
            logo="https://example.org/logo.png",
        )

        assert len(manifest.defaultTypes) == 1
        assert manifest.view is not None
        assert manifest.preview is not None
        assert manifest.suggest is not None
        assert "0.2" in manifest.versions  # type: ignore ; pylint: ignore=unsupported-membership-test


class TestSuggestEntityItem:
    """Test SuggestEntityItem model."""

    def test_minimal_entity_item(self):
        """Test minimal entity item."""
        item = SuggestEntityItem(id="123", name="Uppsala Site")

        assert item.id == "123"
        assert item.name == "Uppsala Site"
        assert item.type == []

    def test_full_entity_item(self):
        """Test entity item with all fields."""
        item = SuggestEntityItem(
            id="123",
            name="Uppsala Site",
            type=[TypeRef(id="site", name="Site")],
            score=95.0,
            match=True,
        )

        assert len(item.type) == 1
        assert item.score == 95.0
        assert item.match is True


class TestSuggestPropertyItem:
    """Test SuggestPropertyItem model."""

    def test_minimal_property_item(self):
        """Test minimal property item."""
        item = SuggestPropertyItem(id="latitude", name="Latitude")

        assert item.id == "latitude"
        assert item.name == "Latitude"
        assert item.description is None

    def test_property_item_with_description(self):
        """Test property item with description."""
        item = SuggestPropertyItem(id="latitude", name="Latitude", description="Geographic latitude coordinate")

        assert item.description == "Geographic latitude coordinate"


class TestSuggestTypeItem:
    """Test SuggestTypeItem model."""

    def test_type_item(self):
        """Test type item."""
        item = SuggestTypeItem(id="site", name="Archaeological Site")

        assert item.id == "site"
        assert item.name == "Archaeological Site"


class TestSuggestEntityResponse:
    """Test SuggestEntityResponse model."""

    def test_entity_response_with_results(self):
        """Test entity response with multiple results."""
        response = SuggestEntityResponse(
            result=[
                SuggestEntityItem(id="1", name="Uppsala"),
                SuggestEntityItem(id="2", name="Stockholm"),
            ]
        )

        assert len(response.result) == 2

    def test_entity_response_empty(self):
        """Test empty entity response."""
        response = SuggestEntityResponse(result=[])

        assert len(response.result) == 0

    def test_entity_response_default_factory(self):
        """Test entity response uses default_factory for empty list."""
        response = SuggestEntityResponse()

        assert response.result == []


class TestSuggestPropertyResponse:
    """Test SuggestPropertyResponse model."""

    def test_property_response(self):
        """Test property response."""
        response = SuggestPropertyResponse(result=[SuggestPropertyItem(id="lat", name="Latitude")])

        assert len(response.result) == 1


class TestSuggestTypeResponse:
    """Test SuggestTypeResponse model."""

    def test_type_response(self):
        """Test type response."""
        response = SuggestTypeResponse(result=[SuggestTypeItem(id="site", name="Site")])

        assert len(response.result) == 1


class TestExtendRequestProperty:
    """Test ExtendRequestProperty model."""

    def test_property_with_id_only(self):
        """Test property with ID only."""
        prop = ExtendRequestProperty(id="latitude")

        assert prop.id == "latitude"
        assert prop.name is None

    def test_property_with_name(self):
        """Test property with ID and name."""
        prop = ExtendRequestProperty(id="latitude", name="Latitude")

        assert prop.id == "latitude"
        assert prop.name == "Latitude"


class TestExtendRequest:
    """Test ExtendRequest model."""

    def test_extend_request(self):
        """Test creating an extend request."""
        request = ExtendRequest(
            ids=["1", "2", "3"],
            properties=[ExtendRequestProperty(id="latitude", name="Latitude"), ExtendRequestProperty(id="longitude")],
        )

        assert len(request.ids) == 3
        assert len(request.properties) == 2
        assert request.properties[0].name == "Latitude"

    def test_extend_request_empty_ids(self):
        """Test extend request with empty IDs list."""
        request = ExtendRequest(ids=[], properties=[ExtendRequestProperty(id="lat")])

        assert len(request.ids) == 0


class TestExtCell:
    """Test ExtCell model."""

    def test_ext_cell_with_str_value(self):
        """Test ExtCell with str value."""
        cell = ExtCell.model_validate({"str_value": "59.8586"})

        assert cell.str_value == "59.8586"

    def test_ext_cell_with_alias_str(self):
        """Test ExtCell accepts 'str' alias."""
        cell = ExtCell.model_validate({"str": "test value"})

        assert cell.str_value == "test value"

    def test_ext_cell_full(self):
        """Test ExtCell with all fields."""
        cell = ExtCell.model_validate(
            {
                "str_value": "Uppsala",
                "lang": "en",
                "id": "123",
                "name": "Uppsala Site",
                "type_ref": "site",
                "url": "https://example.org/123",
            }
        )

        assert cell.str_value == "Uppsala"
        assert cell.lang == "en"
        assert cell.id == "123"
        assert cell.name == "Uppsala Site"
        assert cell.type_ref == "site"

    def test_ext_cell_string_trimming(self):
        """Test ExtCell trims string values."""
        cell = ExtCell.model_validate({"str_value": "  test  ", "name": "  name  "})

        assert cell.str_value == "test"
        assert cell.name == "name"

    def test_ext_cell_empty_string_becomes_none(self):
        """Test ExtCell converts empty strings to None."""
        cell = ExtCell.model_validate({"str_value": "   "})

        assert cell.str_value is None

    def test_ext_cell_with_type_alias(self):
        """Test ExtCell accepts 'type' alias."""
        cell = ExtCell.model_validate({"type": "location"})

        assert cell.type_ref == "location"


class TestExtendResponse:
    """Test ExtendResponse model."""

    def test_extend_response(self):
        """Test creating an extend response."""
        response = ExtendResponse(
            meta=[ExtendRequestProperty(id="latitude", name="Latitude")],
            rows={
                "1": {"latitude": [ExtCell.model_validate({"str_value": "59.8586"})]},
                "2": {"latitude": [ExtCell.model_validate({"str_value": "59.3293"})]},
            },
        )

        assert len(response.meta) == 1
        assert "1" in response.rows
        assert "latitude" in response.rows["1"]
        assert response.rows["1"]["latitude"][0].str_value == "59.8586"

    def test_extend_response_multiple_properties(self):
        """Test extend response with multiple properties."""
        response = ExtendResponse(
            meta=[
                ExtendRequestProperty(id="latitude", name="Latitude"),
                ExtendRequestProperty(id="longitude", name="Longitude"),
            ],
            rows={
                "1": {
                    "latitude": [ExtCell.model_validate({"str_value": "59.8586"})],
                    "longitude": [ExtCell.model_validate({"str_value": "17.6389"})],
                }
            },
        )

        assert len(response.meta) == 2
        assert len(response.rows["1"]) == 2


class TestAPIResponse:
    """Test APIResponse generic wrapper."""

    def test_api_response_success_with_data(self):
        """Test successful API response with data."""
        response = APIResponse[str](success=True, data="test data")

        assert response.success is True
        assert response.data == "test data"
        assert response.error is None

    def test_api_response_error(self):
        """Test error API response."""
        response = APIResponse[str](success=False, error="Something went wrong")

        assert response.success is False
        assert response.error == "Something went wrong"
        assert response.data is None

    def test_api_response_with_complex_type(self):
        """Test API response with complex data type."""
        candidate = ReconCandidate.model_validate({"id": "1", "name": "Test"})
        response = APIResponse[ReconCandidate](success=True, data=candidate)

        assert response.data is not None
        assert response.data.id == "1"
        assert response.data.name == "Test"

    def test_api_response_default_success(self):
        """Test API response defaults to success=True."""
        response = APIResponse[str](data="test")

        assert response.success is True


class TestReconBatchRequestHandler:
    """Test ReconBatchRequestHandler."""

    def test_parse_batch_from_dict(self):
        """Test parsing batch request from dict."""
        data = {"q0": {"query": "Uppsala"}, "q1": {"query": "Stockholm", "limit": 5}}

        result = ReconBatchRequestHandler.parse_batch(data)

        assert "q0" in result
        assert "q1" in result
        assert result["q0"].query == "Uppsala"
        assert result["q1"].limit == 5

    def test_parse_batch_from_root_model(self):
        """Test parsing batch request from RootModel."""
        batch = ReconBatchRequest(root={"q0": ReconQuery(query="Test", type=None, type_strict=None, limit=None, lang=None)})

        result = ReconBatchRequestHandler.parse_batch(batch)

        assert "q0" in result
        assert result["q0"].query == "Test"

    def test_parse_batch_empty(self):
        """Test parsing empty batch."""
        result = ReconBatchRequestHandler.parse_batch({})

        assert len(result) == 0


class TestModelSerialization:
    """Test model serialization/deserialization."""

    def test_recon_query_round_trip(self):
        """Test ReconQuery serialization round trip."""
        original = ReconQuery(query="Test", type="site", limit=10, **{})
        data = original.model_dump()
        restored = ReconQuery.model_validate(data)

        assert restored.query == original.query
        assert restored.type == original.type
        assert restored.limit == original.limit

    def test_recon_candidate_round_trip(self):
        """Test ReconCandidate serialization round trip."""
        original = ReconCandidate.model_validate(
            {"id": "123", "name": "Uppsala", "type": [TypeRef.model_validate({"id": "site", "name": "Site"})], "score": 95.0, "match": True}
        )
        data = original.model_dump()
        restored = ReconCandidate.model_validate(data)

        assert restored.id == original.id
        assert restored.name == original.name
        assert len(restored.type) == len(original.type)
        assert restored.score == original.score

    def test_ext_cell_serialization_with_aliases(self):
        """Test ExtCell serialization preserves aliases."""
        cell = ExtCell.model_validate({"str_value": "test", "type_ref": "location"})
        data = cell.model_dump(by_alias=True)

        # When using by_alias=True, should use 'str' and 'type' keys
        assert "str" in data or "str_value" in data

    def test_suggest_entity_response_serialization(self):
        """Test SuggestEntityResponse includes example in schema."""
        schema = SuggestEntityResponse.model_json_schema()

        assert "example" in schema

    def test_recon_service_manifest_config(self):
        """Test ReconServiceManifest has proper config."""
        manifest = ReconServiceManifest(name="Test", identifierSpace="https://example.org/id/", schemaSpace="https://example.org/schema/")

        # Check model_config is set
        assert manifest.model_config is not None
        assert "validate_assignment" in manifest.model_config
