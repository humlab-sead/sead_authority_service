"""
MCP data models for SEAD reconciliation

These models follow the MCP tool specification from the architecture doc.
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class RawScores(BaseModel):
    """Raw retrieval scores from different channels"""

    trgm: float = Field(description="Trigram similarity score [0,1]")
    sem: float = Field(description="Semantic similarity score [0,1]")
    blend: float = Field(description="Blended score (weighted combination)")


class Candidate(BaseModel):
    """A single lookup candidate with scores"""

    id: str = Field(description="Canonical ID from authority table")
    value: str = Field(description="Display value (label)")
    language: Optional[str] = Field(None, description="ISO 639-1 language code")
    active: bool = Field(True, description="Whether this entry is active")
    raw_scores: Optional[RawScores] = Field(None, description="Detailed scoring breakdown")


class SearchLookupParams(BaseModel):
    """Parameters for hybrid search_lookup tool"""

    entity_type: str = Field(description="Lookup entity type (e.g., 'method', 'modification_type')")
    query: str = Field(description="Free-text query to reconcile")
    k_fuzzy: int = Field(30, description="Top-K from trigram/fuzzy search", ge=1, le=100)
    k_sem: int = Field(30, description="Top-K from semantic search", ge=1, le=100)
    k_final: int = Field(20, description="Final candidate count after union", ge=1, le=50)
    language: Optional[str] = Field(None, description="Prefer/filter by language")
    active_only: bool = Field(True, description="Only return active entries")
    return_raw_scores: bool = Field(True, description="Include raw_scores in response")


class SearchLookupResult(BaseModel):
    """Response from search_lookup tool"""

    entity_type: str
    query: str
    candidates: list[Candidate]
    limits: dict[str, int] = Field(description="Applied K limits")
    elapsed_ms: float
    schema_version: str = Field("0.1", description="MCP schema version")


class RerankParams(BaseModel):
    """Parameters for cross-encoder reranking tool"""

    query: str
    candidates: list[dict[str, Any]] = Field(description="Candidates with at least {id, value}")
    k: int = Field(5, description="Number of top results to return", ge=1, le=20)


class RerankResult(BaseModel):
    """Response from rerank tool"""

    query: str
    results: list[Candidate]
    elapsed_ms: float
    model: str = Field(description="Reranker model identifier")
    schema_version: str = Field("0.1", description="MCP schema version")


class GetByIdParams(BaseModel):
    """Parameters for get_by_id tool"""

    entity_type: str
    id: str


class GetByIdResult(BaseModel):
    """Response from get_by_id tool"""

    id: str
    value: str
    aliases: Optional[list[str]] = None
    language: Optional[str] = None
    active: bool
    provenance: Optional[dict[str, Any]] = None
    schema_version: str = Field("0.1", description="MCP schema version")


class LookupTable(BaseModel):
    """Metadata about an available lookup table"""

    table: str = Field(description="Table/view name in authority schema")
    domain: str = Field(description="Domain/category (e.g., 'taxonomy', 'methods')")
    languages: list[str] = Field(description="Available language codes")
    active_only_default: bool = Field(True)
    columns: dict[str, str] = Field(description="Column name -> type mapping")


class ServerInfo(BaseModel):
    """MCP server metadata"""

    server: str = Field("sead.pg", description="Server identifier")
    version: str = Field(description="Semver version")
    emb_model: Optional[str] = Field(None, description="Embedding model identifier")
    pgvector_dim: Optional[int] = Field(None, description="Vector dimension")
    features: list[str] = Field(description="Available tools/resources")


class MCPError(BaseModel):
    """Uniform error model"""

    code: Literal[
        "BAD_REQUEST",
        "UNAUTHORIZED",
        "FORBIDDEN",
        "NOT_FOUND",
        "UNSUPPORTED_TABLE",
        "INVALID_PARAM",
        "SERVER_ERROR",
        "TIMEOUT",
    ]
    message: str
    details: Optional[dict[str, Any]] = None
