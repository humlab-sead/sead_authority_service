"""
SEAD MCP Server - Embedded Model Context Protocol implementation

Provides a thin MCP facade over SEAD's authority database for:
- Hybrid retrieval (trigram + semantic search)
- Candidate reranking (optional)
- Lookup table metadata and browsing

This is an internal implementation that follows MCP protocol conventions
but runs in-process with the FastAPI service.
"""

from .models import (
    Candidate,
    GetByIdParams,
    GetByIdResult,
    LookupTable,
    RerankParams,
    RerankResult,
    SearchLookupParams,
    SearchLookupResult,
)
from .resources import MCPResources
from .server import SEADMCPServer
from .tools import MCPTools

__all__ = [
    "SEADMCPServer",
    "MCPTools",
    "MCPResources",
    "SearchLookupParams",
    "SearchLookupResult",
    "Candidate",
    "RerankParams",
    "RerankResult",
    "LookupTable",
    "GetByIdParams",
    "GetByIdResult",
]

__version__ = "0.1.0"
