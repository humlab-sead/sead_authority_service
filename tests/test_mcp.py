"""
Tests for SEAD MCP Server

Comprehensive tests for the embedded MCP implementation including:
- Server initialization and configuration
- Tools (search_lookup, get_by_id, rerank)
- Resources (server_info, list_tables, get_rows)
- Models (validation, serialization)
- Error handling and edge cases
"""

import os
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.configuration import get_connection
from src.configuration.config import ConfigFactory
from src.configuration.interface import ConfigLike
from src.configuration.provider import MockConfigProvider
from src.configuration.resolve import ConfigValue
from src.configuration.setup import _setup_connection_factory
from src.mcp import (
    Candidate,
    GetByIdParams,
    GetByIdResult,
    LookupTable,
    SEADMCPServer,
    SearchLookupParams,
    SearchLookupResult,
)
from src.mcp.config import DEFAULT_MCP_CONFIG, MCPConfig, MCPRetrievalConfig, MCPTableConfig
from src.mcp.models import MCPError, RawScores, RerankParams, ServerInfo
from src.mcp.resources import MCPResources
from src.mcp.tools import MCPTools
from tests.decorators import with_test_config

# pylint: disable=redefined-outer-name, unused-argument


@pytest.mark.asyncio
class TestMCPServer:
    """Tests for SEADMCPServer"""

    @with_test_config
    def test_simple_test(self, test_provider: MockConfigProvider) -> None:
        """A simple test to ensure pytest is working"""
        value = ConfigValue("mcp").resolve()
        assert value is not None

    @pytest.mark.asyncio
    @with_test_config
    async def test_server_initialization(self, test_provider):
        """Test MCP server can be initialized"""
        mock_conn = AsyncMock()

        server = SEADMCPServer(mock_conn, version="0.1.0")

        assert server.version == "0.1.0"
        assert server.connection == mock_conn
        assert server.tools is not None
        assert server.resources is not None

    @with_test_config
    async def test_get_server_info(self, test_provider):
        """Test server info returns expected metadata"""
        mock_conn = AsyncMock()
        server = SEADMCPServer(mock_conn)

        info = await server.get_server_info()

        assert info.server == "sead.pg"
        assert info.version == "0.1.0"
        assert "search_lookup" in info.features
        assert "get_by_id" in info.features

    @with_test_config
    async def test_search_lookup_with_fallback(self, test_provider):
        """Test search_lookup using fallback fuzzy function"""

        mock_rows = [
            (1, "Radiocarbon dating", 0.95),
            (2, "Carbon dating", 0.88),
        ]
        test_provider.create_connection_mock(fetchall=mock_rows, execute=None)

        server = SEADMCPServer(test_provider.connection_mock)

        params = SearchLookupParams(
            entity_type="method",
            query="radiocarbon",
            k_final=10,
        )

        result = await server.search_lookup(params)

        assert result["entity_type"] == "method"
        assert result["query"] == "radiocarbon"
        assert len(result["candidates"]) == 2
        assert result["candidates"][0]["id"] == "1"
        assert result["candidates"][0]["value"] == "Radiocarbon dating"
        assert result["elapsed_ms"] > 0

    @with_test_config
    async def test_search_lookup_invalid_entity_type(self, test_provider):
        """Test search_lookup with unsupported entity_type"""
        test_provider.create_connection_mock(fetchall=[], execute=None)

        server = SEADMCPServer(test_provider.connection_mock)

        params = SearchLookupParams(
            entity_type="invalid_entity_type",
            query="test",
            k_final=10,
        )

        with pytest.raises(ValueError, match="Unsupported entity type: invalid_entity_type"):
            await server.search_lookup(params)

    @with_test_config
    async def test_get_by_id(self, test_provider):
        """Test fetching single entry by ID"""
        mock_row = (1, "Radiocarbon dating")
        test_provider.create_connection_mock(fetchone=mock_row, execute=None)

        server = SEADMCPServer(test_provider.connection_mock)

        params = GetByIdParams(entity_type="method", id="1")
        result = await server.get_by_id(params)

        assert result["id"] == "1"
        assert result["value"] == "Radiocarbon dating"

    @with_test_config
    async def test_get_by_id_not_found(self, test_provider):
        """Test get_by_id with non-existent ID"""

        test_provider.create_connection_mock(fetchone=None, execute=None)

        server = SEADMCPServer(test_provider.connection_mock)

        params = GetByIdParams(entity_type="method", id="999")

        with pytest.raises(ValueError, match="not found"):
            await server.get_by_id(params)

    @with_test_config
    async def test_rerank_not_implemented(self, test_provider):
        """Test that rerank raises NotImplementedError (Phase 4)"""
        mock_conn = AsyncMock()
        server = SEADMCPServer(mock_conn)

        with pytest.raises(NotImplementedError):
            await server.rerank("test", [], k=5)

    @with_test_config
    async def test_list_lookup_tables(self, test_provider):
        """Test listing available lookup tables"""

        mock_rows = [
            ("method_id", "bigint"),
            ("method_name", "text"),
        ]
        test_provider.create_connection_mock(fetchall=mock_rows, execute=None)

        server = SEADMCPServer(test_provider.connection_mock)

        tables = await server.list_lookup_tables()

        assert len(tables) > 0
        assert any(t["table"] == "method" for t in tables)


@pytest.mark.asyncio
class TestMCPModels:
    """Tests for MCP data models"""

    def test_candidate_model(self):
        """Test Candidate model validation"""
        candidate = Candidate(
            id="123",
            value="Test Value",
            language="en",
            raw_scores=RawScores(trgm=0.9, sem=0.85, blend=0.875),
        )

        assert candidate.id == "123"
        assert candidate.value == "Test Value"

        assert candidate.raw_scores is not None
        assert candidate.raw_scores.blend == 0.875  # pylint: disable=no-member

    def test_candidate_without_scores(self):
        """Test Candidate without raw_scores"""
        candidate = Candidate(id="456", value="Another Value", language="en")

        assert candidate.id == "456"
        assert candidate.raw_scores is None
        # assert candidate.language is None

    def test_raw_scores_model(self):
        """Test RawScores model"""
        scores = RawScores(trgm=0.95, sem=0.88, blend=0.915)

        assert scores.trgm == 0.95
        assert scores.sem == 0.88
        assert scores.blend == 0.915

    def test_search_params_defaults(self):
        """Test SearchLookupParams with defaults"""
        params = SearchLookupParams(entity_type="method", query="test")

        assert params.k_fuzzy == 30
        assert params.k_sem == 30
        assert params.k_final == 20
        assert params.return_raw_scores is True

    def test_search_params_custom_values(self):
        """Test SearchLookupParams with custom values"""
        params = SearchLookupParams(
            entity_type="method",
            query="test",
            k_fuzzy=50,
            k_sem=40,
            k_final=15,
            language="en",
            return_raw_scores=False,
        )

        assert params.k_fuzzy == 50
        assert params.k_sem == 40
        assert params.k_final == 15
        assert params.language == "en"
        assert params.return_raw_scores is False

    def test_search_params_validation(self):
        """Test SearchLookupParams validation"""
        with pytest.raises(ValueError):
            # k_final > 50 should fail
            SearchLookupParams(entity_type="method", query="test", k_final=100)

    def test_search_params_validation_negative(self):
        """Test SearchLookupParams with negative values"""
        with pytest.raises(ValueError):
            SearchLookupParams(entity_type="method", query="test", k_fuzzy=-1)

    def test_search_result_model(self):
        """Test SearchLookupResult model"""
        result = SearchLookupResult(
            entity_type="method",
            query="radiocarbon",
            candidates=[Candidate(id="1", value="Radiocarbon dating")],
            limits={"k_fuzzy": 30, "k_sem": 30, "k_final": 20},
            elapsed_ms=42.5,
        )

        assert result.entity_type == "method"
        assert result.query == "radiocarbon"
        assert len(result.candidates) == 1
        assert result.elapsed_ms == 42.5
        assert result.schema_version == "0.1"

    def test_get_by_id_params(self):
        """Test GetByIdParams model"""
        params = GetByIdParams(entity_type="method", id="123")

        assert params.entity_type == "method"
        assert params.id == "123"

    def test_get_by_id_result(self):
        """Test GetByIdResult model"""
        result = GetByIdResult(
            id="123",
            value="Test Method",
            aliases=["alt1", "alt2"],
            language="en",
            provenance={"source": "test"},
        )

        assert result.id == "123"
        assert result.value == "Test Method"
        assert result.aliases is not None
        assert len(result.aliases) == 2
        assert result.schema_version == "0.1"

    def test_lookup_table_model(self):
        """Test LookupTable model"""
        table = LookupTable(
            table="methods",
            domain="methods",
            languages=["en", "sv"],
            columns={"method_id": "integer", "method_name": "text"},
        )

        assert table.table == "methods"
        assert len(table.languages) == 2
        assert "method_id" in table.columns

    def test_server_info_model(self):
        """Test ServerInfo model"""
        info = ServerInfo(
            server="sead.pg",
            version="0.1.0",
            emb_model="nomic-embed-text",
            pgvector_dim=768,
            features=["search_lookup", "get_by_id"],
        )

        assert info.server == "sead.pg"
        assert info.pgvector_dim == 768
        assert len(info.features) == 2

    def test_rerank_params_model(self):
        """Test RerankParams model"""
        params = RerankParams(
            query="test",
            candidates=[{"id": "1", "value": "test1"}],
            k=5,
        )

        assert params.query == "test"
        assert len(params.candidates) == 1
        assert params.k == 5

    def test_mcp_error_model(self):
        """Test MCPError model"""
        error = MCPError(
            code="NOT_FOUND",
            message="Entity not found",
            details={"entity_id": "123"},
        )

        assert error.code == "NOT_FOUND"
        assert error.message == "Entity not found"
        assert isinstance(error.details, dict)
        assert error.details["entity_id"] == "123"  # pylint: disable=unsubscriptable-object


@pytest.mark.asyncio
class TestMCPConfig:
    """Tests for MCP configuration"""

    def test_mcp_table_config(self):
        """Test MCPTableConfig model"""
        config = MCPTableConfig(
            table_key="methods",
            db_table="tbl_methods",
            id_column="method_id",
            label_column="method_name",
            fuzzy_function="authority.fuzzy_method",
        )

        assert config.table_key == "methods"
        assert config.db_table == "tbl_methods"
        assert config.fuzzy_function == "authority.fuzzy_method"

    def test_mcp_retrieval_config(self):
        """Test MCPRetrievalConfig model"""
        config = MCPRetrievalConfig(
            k_fuzzy=40,
            k_sem=35,
            k_final=25,
            blend_weight_trgm=0.6,
            blend_weight_sem=0.4,
        )

        assert config.k_fuzzy == 40
        assert config.blend_weight_trgm == 0.6

    def test_default_mcp_config(self):
        """Test DEFAULT_MCP_CONFIG instance"""
        assert DEFAULT_MCP_CONFIG.version == "0.1.0"
        assert DEFAULT_MCP_CONFIG.enabled is False
        assert DEFAULT_MCP_CONFIG.enable_reranking is False
        assert "methods" in DEFAULT_MCP_CONFIG.tables

    def test_mcp_config_feature_flags(self):
        """Test MCP config feature flags"""
        config = MCPConfig(
            version="0.2.0",
            enabled=True,
            enable_reranking=True,
            enable_caching=False,
        )

        assert config.enabled is True
        assert config.enable_reranking is True
        assert config.enable_caching is False


@pytest.mark.asyncio
class TestMCPResources:
    """Tests for MCPResources"""

    @with_test_config
    async def test_get_server_info(self, test_provider):
        """Test get_server_info returns correct metadata"""
        mock_conn = AsyncMock()
        resources = MCPResources(mock_conn, version="0.1.0")

        info = await resources.get_server_info()

        assert info.server == "sead.pg"
        assert info.version == "0.1.0"
        assert "search_lookup" in info.features
        assert "get_by_id" in info.features

    @with_test_config
    async def test_list_lookup_tables(self, test_provider):
        """Test list_lookup_tables returns table metadata"""
        mock_rows = [
            ("method_id", "integer"),
            ("method_name", "text"),
        ]
        test_provider.create_connection_mock(fetchall=mock_rows, execute=None)

        resources = MCPResources(test_provider.connection_mock, version="0.1.0")

        tables = await resources.list_lookup_tables()

        assert len(tables) > 0
        assert all(isinstance(t, LookupTable) for t in tables)

    @with_test_config
    async def test_get_lookup_rows(self, test_provider):
        """Test get_lookup_rows returns paginated data"""
        mock_rows = [
            (1, "Method 1", True),
            (2, "Method 2", True),
        ]
        test_provider.create_connection_mock(fetchall=mock_rows, execute=None)

        resources = MCPResources(test_provider.connection_mock)

        result = await resources.get_lookup_rows("method", offset=0, limit=10)

        assert "rows" in result
        assert "next_offset" in result
        assert len(result["rows"]) == 2
        assert result["next_offset"] == 2

    @with_test_config
    async def test_get_lookup_rows_invalid_entity(self, test_provider):
        """Test get_lookup_rows with invalid entity type"""
        test_provider.create_connection_mock(fetchall=[], execute=None)

        resources = MCPResources(test_provider.connection_mock)

        with pytest.raises(ValueError, match="not in allowed list"):
            await resources.get_lookup_rows("invalid_entity")

    @with_test_config
    async def test_get_lookup_rows_language_not_implemented(self, test_provider):
        """Test get_lookup_rows with language parameter raises NotImplementedError"""
        test_provider.create_connection_mock(fetchall=[], execute=None)

        resources = MCPResources(test_provider.connection_mock)

        with pytest.raises(NotImplementedError, match="Language filtering"):
            await resources.get_lookup_rows("method", language="sv")


@pytest.mark.asyncio
class TestMCPTools:
    """Tests for MCPTools"""

    @with_test_config
    async def test_search_lookup(self, test_provider):
        """Test search_lookup basic functionality"""
        mock_rows = [
            (1, "Radiocarbon dating", 0.95),
            (2, "Carbon dating", 0.88),
        ]
        test_provider.create_connection_mock(fetchall=mock_rows, execute=None)

        tools = MCPTools(test_provider.connection_mock)

        params = SearchLookupParams(
            entity_type="method",
            query="radiocarbon",
            k_final=10,
        )

        result = await tools.search_lookup(params)

        assert result.entity_type == "method"
        assert result.query == "radiocarbon"
        assert len(result.candidates) == 2
        assert result.candidates[0].id == "1"
        assert result.elapsed_ms > 0

    @with_test_config
    async def test_search_lookup_with_scores(self, test_provider):
        """Test search_lookup includes raw scores"""
        mock_rows = [(1, "Test", 0.9)]
        test_provider.create_connection_mock(fetchall=mock_rows, execute=None)

        tools = MCPTools(test_provider.connection_mock)

        params = SearchLookupParams(
            entity_type="method",
            query="test",
            return_raw_scores=True,
        )

        result = await tools.search_lookup(params)

        assert result.candidates[0].raw_scores is not None
        assert result.candidates[0].raw_scores.trgm > 0

    @with_test_config
    async def test_search_lookup_without_scores(self, test_provider):
        """Test search_lookup without raw scores"""
        mock_rows = [(1, "Test", 0.9)]
        test_provider.create_connection_mock(fetchall=mock_rows, execute=None)

        tools = MCPTools(test_provider.connection_mock)

        params = SearchLookupParams(
            entity_type="method",
            query="test",
            return_raw_scores=False,
        )

        result = await tools.search_lookup(params)

        assert result.candidates[0].raw_scores is None

    @with_test_config
    async def test_search_lookup_invalid_entity(self, test_provider):
        """Test search_lookup with invalid entity type"""
        test_provider.create_connection_mock(fetchall=[], execute=None)

        tools = MCPTools(test_provider.connection_mock)

        params = SearchLookupParams(
            entity_type="nonexistent_table",
            query="test",
        )

        with pytest.raises(ValueError, match="Unsupported entity type"):
            await tools.search_lookup(params)

    @with_test_config
    async def test_search_lookup_empty_results(self, test_provider):
        """Test search_lookup with no matches"""
        test_provider.create_connection_mock(fetchall=[], execute=None)

        tools = MCPTools(test_provider.connection_mock)

        params = SearchLookupParams(
            entity_type="method",
            query="nonexistent query xyz",
        )

        result = await tools.search_lookup(params)

        assert len(result.candidates) == 0

    @with_test_config
    async def test_get_by_id(self, test_provider):
        """Test get_by_id retrieves single entity"""
        mock_row = (1, "Radiocarbon dating")
        test_provider.create_connection_mock(fetchone=mock_row, execute=None)

        tools = MCPTools(test_provider.connection_mock)

        params = GetByIdParams(entity_type="method", id="1")
        result = await tools.get_by_id(params)

        assert result.id == "1"
        assert result.value == "Radiocarbon dating"

    @with_test_config
    async def test_get_by_id_not_found(self, test_provider):
        """Test get_by_id with non-existent ID"""
        test_provider.create_connection_mock(fetchone=None, execute=None)

        tools = MCPTools(test_provider.connection_mock)

        params = GetByIdParams(entity_type="method", id="999")

        with pytest.raises(ValueError, match="not found"):
            await tools.get_by_id(params)

    @with_test_config
    async def test_get_by_id_invalid_entity(self, test_provider):
        """Test get_by_id with invalid entity type"""
        test_provider.create_connection_mock(fetchone=None, execute=None)

        tools = MCPTools(test_provider.connection_mock)

        params = GetByIdParams(entity_type="invalid_type", id="1")

        with pytest.raises(ValueError, match="Unknown entity type 'invalid_type'"):
            await tools.get_by_id(params)

    @with_test_config
    async def test_rerank_not_implemented(self, test_provider):
        """Test that rerank raises NotImplementedError"""
        tools = MCPTools(test_provider.connection_mock)

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            await tools.rerank("test", [], k=5)


# Integration test (requires actual database connection)
@pytest.mark.integration
@pytest.mark.asyncio
@with_test_config
async def test_search_lookup_integration(test_provider):
    """
    Integration test with real database

    Requires:
    - PostgreSQL running
    - authority.fuzzy_method() function exists
    - Test data in tbl_methods
    """
    os.environ["CONFIG_FILE"] = "./config/config.yml"
    os.environ["ENV_FILE"] = ".env"

    config: ConfigLike = ConfigFactory().load(source="./config/config.yml", env_prefix="SEAD_AUTHORITY", env_filename=".env")
    test_provider.set_config(config)
    await _setup_connection_factory(config, "options:database")

    async with await get_connection() as conn:
        server = SEADMCPServer(conn)

        params = SearchLookupParams(
            entity_type="method",
            query="radiocarbon",
            k_final=5,
        )

        result: dict[str, Any] = await server.search_lookup(params)

        assert result["entity_type"] == "method"
        assert len(result["candidates"]) <= 5
        assert result["elapsed_ms"] > 0

        if result["candidates"]:
            top = result["candidates"][0]
            assert "id" in top
            assert "value" in top
            assert top["raw_scores"]["blend"] > 0
