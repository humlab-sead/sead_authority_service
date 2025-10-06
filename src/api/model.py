# models_openrefine.py
from typing import Any, Dict, List, Mapping, Optional, Union

from pydantic import BaseModel, Field
from typing_extensions import Literal

# ---------- Common ----------


class TypeRef(BaseModel):
    id: str
    name: str


JsonScalar = Union[str, int, float, bool, None]
JsonValue = Union[JsonScalar, List["JsonValue"], Dict[str, "JsonValue"]]  # recursive
# pydantic resolves forward refs at bottom


# ---------- /reconcile (queries & results) ----------


class ReconPropertyConstraint(BaseModel):
    """Property constraint in a query: property id + value."""

    pid: str = Field(..., description="Property ID (e.g., 'P31')")
    v: JsonValue = Field(..., description="Constraint value (scalar or JSON object)")


class ReconQuery(BaseModel):
    """A single reconciliation query."""

    query: str
    type: Optional[str] = Field(None, description="Entity/type ID to bias results")
    type_strict: Optional[Literal["should", "all", "any"]] = Field(None, description="Type matching policy")
    limit: Optional[int] = Field(None, description="Max candidates to return")
    properties: Optional[List[ReconPropertyConstraint]] = None
    lang: Optional[str] = Field(None, description="BCP47 language code for labels")


class ReconBatchRequest(BaseModel):
    """
    Batch queries: OpenRefine posts a JSON object mapping arbitrary keys to ReconQuery.
    Example:
      {
        "q0": { "query": "Uppsala", "type": "Q515" },
        "q1": { "query": "Uppland" }
      }
    """

    __root__: Mapping[str, ReconQuery]


class ReconCandidate(BaseModel):
    """Candidate entity returned by reconciliation."""

    id: str
    name: str
    type: List[TypeRef] = []
    score: Optional[float] = None
    match: Optional[bool] = None
    description: Optional[str] = None  # optional, but useful
    # You may also return extra keys like 'uri', 'notable', etc., if you want.


class ReconQueryResult(BaseModel):
    result: List[ReconCandidate]


class ReconBatchResponse(BaseModel):
    """Batch response mirrors request keys -> {result: [...] }."""

    __root__: Mapping[str, ReconQueryResult]


# ---------- /reconcile (service manifest, GET with no params) ----------


class ViewTemplate(BaseModel):
    """How OpenRefine can view a resource (usually an entity page)."""

    url: str  # e.g., "https://example.org/entity/{{id}}"


class PreviewTemplate(BaseModel):
    """Preview (iframe) settings."""

    url: str  # HTML endpoint returning a small preview for an entity
    width: int = 430
    height: int = 300


class SuggestSubservice(BaseModel):
    """
    Suggest endpoint descriptor. OpenRefine expects at least:
      { "service_url": "https://...", "service_path": "/suggest/entity" }
    """

    service_url: str
    service_path: str


class SuggestDescriptor(BaseModel):
    entity: Optional[SuggestSubservice] = None
    type: Optional[SuggestSubservice] = None
    property: Optional[SuggestSubservice] = None
    flyout: Optional[SuggestSubservice] = None  # optional; some tools use this


class ExtendDescriptor(BaseModel):
    """Data extension endpoint descriptor."""

    service_url: str
    service_path: str


class ReconServiceManifest(BaseModel):
    """
    The JSON object OpenRefine reads from GET /reconcile (no params).
    Include capabilities your service supports.
    """

    name: str
    identifierSpace: str
    schemaSpace: str
    defaultTypes: List[TypeRef] = []

    view: Optional[ViewTemplate] = None
    preview: Optional[PreviewTemplate] = None
    suggest: Optional[SuggestDescriptor] = None
    extend: Optional[ExtendDescriptor] = None

    # Optional extras:
    versions: Optional[List[str]] = None  # e.g., ["0.2", "0.3"]
    homepage: Optional[str] = None
    logo: Optional[str] = None
    # You can add 'proposeProperties', 'feature_view', etc., if needed.


# ---------- /suggest/* (entity/property/type) ----------


class SuggestEntityItem(BaseModel):
    id: str
    name: str
    type: List[TypeRef] = []
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
    result: List[SuggestEntityItem]


class SuggestPropertyResponse(BaseModel):
    result: List[SuggestPropertyItem]


class SuggestTypeResponse(BaseModel):
    result: List[SuggestTypeItem]


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
    """
    One value in an extension cell. OpenRefine accepts several shapes:
      - string-only: {"str": "Uppsala"}
      - linked entity: {"id":"Q123","name":"Uppsala"}
      - typed/URL values: {"str":"https://...","url":"https://..."}
    """

    str: Optional[str] = None
    lang: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None


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


# Resolve forward refs for JsonValue
JsonValue.update_forward_refs()
