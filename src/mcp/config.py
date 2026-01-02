"""
MCP Configuration

Settings for the embedded MCP server, including:
- Enabled tables
- Retrieval parameters (K values)
- Scoring weights
- Feature flags
"""

from typing import Optional

from pydantic import BaseModel, Field


class MCPTableConfig(BaseModel):
    """Configuration for a single lookup table"""

    table_key: str = Field(description="MCP table key (e.g., 'methods')")
    db_table: str = Field(description="Actual database table/view name")
    id_column: str = Field(description="Primary key column")
    label_column: str = Field(description="Display label column")
    norm_column: Optional[str] = Field(default=None, description="Normalized text column for fuzzy search")
    emb_column: Optional[str] = Field(default=None, description="Embedding vector column")
    language_column: Optional[str] = Field(default=None, description="Language code column")
    fuzzy_function: Optional[str] = Field(default=None, description="Authority schema fuzzy function name")
    hybrid_function: Optional[str] = Field(default=None, description="Authority schema hybrid function name (Phase 3)")


class MCPRetrievalConfig(BaseModel):
    """Default retrieval parameters"""

    k_fuzzy: int = Field(default=30, description="Top-K from trigram search", ge=1, le=100)
    k_sem: int = Field(default=30, description="Top-K from semantic search", ge=1, le=100)
    k_final: int = Field(default=20, description="Final union size", ge=1, le=50)
    blend_weight_trgm: float = Field(default=0.5, description="Weight for trigram score", ge=0.0, le=1.0)
    blend_weight_sem: float = Field(default=0.5, description="Weight for semantic score", ge=0.0, le=1.0)
    min_score_threshold: float = Field(default=0.6, description="Minimum score to return matches", ge=0.0, le=1.0)


class MCPConfig(BaseModel):
    """Main MCP server configuration"""

    version: str = Field(default="0.1.0", description="MCP server version")
    enabled: bool = Field(default=False, description="Global MCP enable flag")

    # Table configurations
    tables: dict[str, MCPTableConfig] = Field(
        default_factory=lambda: {
            "methods": MCPTableConfig(
                table_key="methods",
                db_table="tbl_methods",
                id_column="method_id",
                label_column="method_name",
                norm_column=None,
                emb_column=None,
                language_column=None,
                fuzzy_function="authority.fuzzy_method",
                hybrid_function=None,
            ),
            "modification_type": MCPTableConfig(
                table_key="modification_type",
                db_table="tbl_modification_types",
                id_column="modification_type_id",
                label_column="modification_type_name",
                norm_column=None,
                emb_column=None,
                language_column=None,
                fuzzy_function="authority.fuzzy_modification_type",
                hybrid_function=None,
            ),
            "sites": MCPTableConfig(
                table_key="sites",
                db_table="tbl_sites",
                id_column="site_id",
                label_column="site_name",
                norm_column=None,
                emb_column=None,
                language_column=None,
                fuzzy_function="authority.fuzzy_site",
                hybrid_function=None,
            ),
        }
    )

    # Retrieval defaults
    retrieval: MCPRetrievalConfig = Field(
        default_factory=lambda: MCPRetrievalConfig(
            k_fuzzy=30,
            k_sem=30,
            k_final=20,
            blend_weight_trgm=0.5,
            blend_weight_sem=0.5,
            min_score_threshold=0.6,
        )
    )

    # Feature flags
    enable_reranking: bool = Field(default=False, description="Enable cross-encoder reranking (Phase 4)")
    enable_caching: bool = Field(default=True, description="Enable Redis candidate caching")
    cache_ttl_seconds: int = Field(default=86400, description="Cache TTL (24 hours default)")

    # Observability
    log_queries: bool = Field(default=True, description="Log all search_lookup calls")
    log_scores: bool = Field(default=True, description="Include raw scores in logs")


# Default configuration instance
DEFAULT_MCP_CONFIG = MCPConfig(
    version="0.1.0",
    enabled=False,
    enable_reranking=False,
    enable_caching=True,
    cache_ttl_seconds=86400,
    log_queries=True,
    log_scores=True,
)
