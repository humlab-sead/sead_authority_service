# models_openrefine.py
from typing import Dict, List, Mapping, Optional, Union, Any, Generic, TypeVar
from typing import ForwardRef

from pydantic import BaseModel, Field, RootModel, ConfigDict, field_validator, HttpUrl
from typing_extensions import Literal
from typing import Annotated

# ---------- Common ----------


class TypeRef(BaseModel):
    id: str
    name: str


# Fix recursive type definition
JsonScalar = Union[str, int, float, bool, None]

# Use ForwardRef for recursive definition
JsonValue = Union[JsonScalar, List[ForwardRef('JsonValue')], Dict[str, ForwardRef('JsonValue')]]


# ---------- /reconcile (queries & results) ----------


class ReconPropertyConstraint(BaseModel):
    """Property constraint in a query: property id + value."""

    pid: str = Field(..., description="Property ID (e.g., 'P31')")
    v: Any = Field(..., description="Constraint value (scalar or JSON object)")  # Use Any instead of JsonValue


class ReconQuery(BaseModel):
    """A single reconciliation query."""

    query: str = Field(..., description="Search query string", examples=["Uppsala"])
    type: Optional[str] = Field(None, description="Entity/type ID to bias results", examples=["site"])
    type_strict: Optional[Literal["should", "all", "any"]] = Field(None, description="Type matching policy")
    limit: Optional[int] = Field(None, description="Max candidates to return", ge=1, le=500)
    properties: Optional[List[ReconPropertyConstraint]] = None
    lang: Optional[str] = Field(None, description="BCP47 language code for labels", examples=["en", "sv"])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "Uppsala",
                "type": "site", 
                "limit": 10
            }
        }
    )

    @field_validator('query', mode='before')
    @classmethod
    def validate_query(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError('Query cannot be empty')
        return v

    @field_validator('type', mode='before')
    @classmethod 
    def validate_type_list(cls, v):
        if isinstance(v, list) and len(v) == 0:
            return []
        return v


class ReconBatchRequest(RootModel[Mapping[str, ReconQuery]]):
    """
    Batch queries: OpenRefine posts a JSON object mapping arbitrary keys to ReconQuery.
    Example:
      {
        "q0": { "query": "Uppsala", "type": "Q515" },
        "q1": { "query": "Uppland" }
      }
    """
    root: Mapping[str, ReconQuery]


class ReconCandidate(BaseModel):
    """Candidate entity returned by reconciliation."""

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., min_length=1, description="Display name")
    type: List[TypeRef] = Field(default_factory=list)
    score: Optional[Annotated[float, Field(ge=0.0, le=100.0)]] = None
    match: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=500)  # optional, but useful
    # You may also return extra keys like 'uri', 'notable', etc., if you want.


class ReconQueryResult(BaseModel):
    result: List[ReconCandidate]


class ReconBatchResponse(RootModel[Mapping[str, ReconQueryResult]]):
    """Batch response mirrors request keys -> {result: [...] }."""
    root: Mapping[str, ReconQueryResult]


# ---------- /reconcile (service manifest, GET with no params) ----------


class ViewTemplate(BaseModel):
    """How OpenRefine can view a resource (usually an entity page)."""

    url: str  # e.g., "https://example.org/entity/{{id}}"


class PreviewTemplate(BaseModel):
    """Preview (iframe) settings."""

    url: HttpUrl = Field(..., description="HTML endpoint returning a small preview")
    width: Annotated[int, Field(gt=0, le=1920)] = 430
    height: Annotated[int, Field(gt=0, le=1080)] = 300


class SuggestSubservice(BaseModel):
    """
    Suggest endpoint descriptor. OpenRefine expects at least:
      { "service_url": "https://...", "service_path": "/suggest/entity" }
    For entity suggest, may also include flyout service details.
    """

    service_url: str
    service_path: str
    flyout_service_url: Optional[str] = None
    flyout_service_path: Optional[str] = None


class SuggestDescriptor(BaseModel):
    entity: Optional[SuggestSubservice] = None
    type: Optional[SuggestSubservice] = None
    property: Optional[SuggestSubservice] = None
    flyout: Optional[SuggestSubservice] = None  # optional; some tools use this


class ProposePropertiesDescriptor(BaseModel):
    """Propose properties endpoint descriptor."""
    service_url: str
    service_path: str

class PropertySetting(BaseModel):
    """Property setting for OpenRefine."""
    name: str
    label: str
    type: str
    help_text: str
    entity_types: List[str]
    settings: Optional[Dict[str, Any]] = None

class ExtendDescriptor(BaseModel):
    """Data extension endpoint descriptor."""
    propose_properties: ProposePropertiesDescriptor
    property_settings: List[PropertySetting]


class ReconServiceManifest(BaseModel):
    """Service manifest with proper caching hints"""

    name: str
    identifierSpace: str  # Changed from HttpUrl to str to handle the format from metadata
    schemaSpace: str  # Changed from HttpUrl to str
    defaultTypes: List[TypeRef] = Field(default_factory=list)

    view: Optional[ViewTemplate] = None
    preview: Optional[PreviewTemplate] = None
    suggest: Optional[SuggestDescriptor] = None
    extend: Optional[ExtendDescriptor] = None

    # Optional extras:
    versions: Optional[List[str]] = None  # e.g., ["0.2", "0.3"]
    homepage: Optional[str] = None
    logo: Optional[str] = None
    # You can add 'proposeProperties', 'feature_view', etc., if needed.

    model_config = ConfigDict(
        # Enable faster serialization
        validate_assignment=True,
        use_enum_values=True,
        # Add caching hints for FastAPI
        json_schema_extra={
            "cache_control": "public, max-age=3600"
        }
    )


# ---------- /suggest/* (entity/property/type) ----------


class SuggestEntityItem(BaseModel):
    id: str
    name: str
    type: List[TypeRef] = Field(default_factory=list)
    score: Optional[float] = None
    match: Optional[bool] = None
    # Optional: 'description' is not in the strict spec, but clients tolerate it.


class SuggestPropertyItem(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    # Some services also return 'type' here; OpenRefine doesn't require it.


class SuggestTypeItem(BaseModel):
    id: str
    name: str


class SuggestEntityResponse(BaseModel):
    result: List[SuggestEntityItem] = Field(default_factory=list)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "result": [
                    {
                        "id": "https://w3id.org/sead/id/site/123",
                        "name": "Uppsala Site",
                        "type": [{"id": "site", "name": "Site"}],
                        "score": 95.0
                    }
                ]
            }
        }
    )


class SuggestPropertyResponse(BaseModel):
    result: List[SuggestPropertyItem] = Field(default_factory=list)


class SuggestTypeResponse(BaseModel):
    result: List[SuggestTypeItem] = Field(default_factory=list)


# ---------- /reconcile/extend (data extension) ----------


class ExtendRequestProperty(BaseModel):
    """Property asked for in extension; name is optional convenience."""

    id: str
    name: Optional[str] = None


class ExtendRequest(BaseModel):
    """
    OpenRefine POSTs:
      { "ids": ["Q1","Q2"], "properties": [{"id":"P31","name":"instance of"}] }
    """

    ids: List[str]
    properties: List[ExtendRequestProperty]


class ExtCell(BaseModel):
    """Extension cell value with proper field handling"""

    str_value: Optional[str] = Field(None, alias="str")
    lang: Optional[str] = None
    id: Optional[str] = None  
    name: Optional[str] = None
    type_ref: Optional[str] = Field(None, alias="type")
    url: Optional[HttpUrl] = None

    model_config = ConfigDict(
        populate_by_name=True,  # Allow both 'str' and 'str_value'
        validate_assignment=True
    )

    @field_validator('str_value', 'name', mode='before')
    @classmethod
    def validate_strings(cls, v):
        if v is not None and isinstance(v, str):
            return v.strip() if v.strip() else None
        return v


class ExtendResponse(BaseModel):
    """
    Response:
    {
      "meta": [{"id":"P31","name":"instance of"}],
      "rows": {
        "Q1": { "P31": [ {"id":"Q5","name":"human"} ] },
        "Q2": { "P31": [ {"id":"Q515","name":"city"} ] }
      }
    }
    """

    meta: List[ExtendRequestProperty]
    rows: Dict[str, Dict[str, List[ExtCell]]]


T = TypeVar('T')

class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper"""
    success: bool = True
    data: Optional[T] = None
    error: Optional[str] = None


# Handle both dict and RootModel for batch requests
ReconBatchRequestType = Union[Dict[str, ReconQuery], ReconBatchRequest]

class ReconBatchRequestHandler(BaseModel):
    """Flexible handler for batch requests"""
    
    @classmethod
    def parse_batch(cls, data: Union[dict, ReconBatchRequest]) -> Dict[str, ReconQuery]:
        if isinstance(data, dict):
            return {k: ReconQuery.model_validate(v) for k, v in data.items()}
        return data.root