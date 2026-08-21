# Graph Report - sead_authority_service  (2026-08-21)

## Corpus Check
- 242 files · ~194,197 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4424 nodes · 8637 edges · 260 communities (224 shown, 36 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 519 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ed17dc46`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- MockConfigProvider
- ValueError
- with_test_config
- BaseRepository
- TestClient
- test_service.py
- GeoNamesReconciliationStrategy
- TestDotNotationUtilities
- GeoNamesProxy
- IdentityPolicy
- TestClient
- test_config_extended.py
- AdministrativeRegionReconciliationStrategy
- test_suggest.py
- router.py
- FeatureTypeReconciliationStrategy
- test_repository.py
- IdentityService
- reset_config_provider
- _parse_list_expression
- ResolutionRequest
- TranslationService
- PostgreSQL Authority Schema
- _make_service
- model.py
- SEADMCPServer
- GeoNamesRepository
- TestListOperations
- _make_service_mock
- TrackedIdentity
- render_preview
- OllamaProvider
- ReconQuery
- TestReplaceReferences
- MCPTools
- replace_env_vars
- test_mcp.py
- LLMModificationTypeReconciliationStrategy
- LLMReconciliationStrategy
- 01_tables.sql
- ReconCandidate
- .fetch_all
- TestMCPModels
- ConfigFactory
- 04_views.sql
- test_llm_input_format.py
- ExtendRequestProperty
- SuggestEntityResponse
- BibliographicReferenceRepository
- TestMultipleRepository
- TranslationCache
- format_rows_for_llm
- TestUtilityFunctions
- strategies/test_strategy.py
- .as_candidate
- TestRegistry
- EmbeddingPopulator
- asyncio
- main
- TestStrategyRegistry
- BibliographicReferenceReconciliationStrategy
- tests/test_utility.py
- What You Must Do When Invoked
- TestMCPConfig
- TestAdministrativeRegionDistinctionFromCountry
- TestTranslationCacheGet
- create_schema.sh
- PropertySetting
- get_reconcile_properties
- reconcile_queries
- TestMarkdownFormatter
- patch
- recursive_filter_dict
- TestTranslationCacheEdgeCases
- asyncio
- What You Must Do When Invoked
- TestTranslationCacheIntegration
- Entity Schema Definitions
- Binding Set
- Identity Policy
- public.tbl_physical_samples
- test_translation_cache.py
- Any
- .find_candidates
- LLMProvider
- public.tbl_taxa_tree_master
- TestExtCell
- test_model.py
- ModificationTypeRepository
- TestModelSerialization
- TestMCPResources
- Project README
- TaxonReconciliationStrategy
- authority.get_embedding_status
- TypeRef
- TestAPIResponse
- TestEdgeCases
- TestConfigFactoryEdgeCases
- TestReplaceReferencesPublicAPI
- public.tbl_methods
- EntityPolicy
- Summary
- ReconPropertyConstraint
- configuration/test_utility.py
- TestFormatterRegistry
- .test_real_database_multiple_queries
- normalize_text
- SIMS (SEAD Identity Management System)
- authority.location
- sead_identity.bindings
- Section Guidance
- CHANGELOG.md
- TestConfigUpdate
- test_router.py
- patch
- Identifier Intake Requirements (FR-6..11)
- authority.taxa_synonym
- authority.taxa_tree_family
- authority.taxa_tree_genus
- authority.taxa_tree_master
- authority.taxa_tree_order
- fix_imports_in_file
- .test_whoami_returns_host_and_port
- TestViewTemplate
- dotset
- TestMultipleReconciliationStrategy
- test_provider
- .test_is_alive
- .__init__
- authority.bibliographic_reference
- authority.data_type_group
- authority.data_type
- authority.dating_uncertainty
- authority.feature_type
- authority.feature
- authority.method_group
- authority.method
- authority.modification_type
- authority.relative_age_type
- authority.relative_age
- authority.sample_description_type
- authority.sample_group_description_type
- authority.sampling_context
- authority.sample_location_type
- authority.sample_type
- authority.taxa_tree_author
- authority.taxonomic_order_system
- authority.taxonomy_note
- authority.location_type
- authority.record_type
- sead_identity.source_identity_keys
- sead_identity.submission_source_identities
- find_import_inconsistencies
- ConfigStore
- ._make_repo
- Taxa Tree Family Entity
- ConfigLike
- .__init__
- authority.fuzzy_site
- build.sh
- sead_identity.source_scopes
- sead_identity.submissions
- sead_identity.source_identities
- sead_identity.binding_sets
- .get_lookup_rows
- _StubConfigValue
- graphify reference: extra exports and benchmark
- Identity Model Requirements (FR-1..5)
- graphify reference: extra exports and benchmark
- 005_tracked_identities.sql
- test-ci.sh
- GeoNames Resource
- tests/identity/__init__.py
- Submission and Traceability Requirements (FR-21..23)
- Writing Style Instructions
- OpenRefine
- authority-service
- Taxon Resource
- Identity Configuration
- test_ollama.py
- public.tbl_locations
- TestSafeLoaderIgnoreUnknown
- graphify reference: query, path, explain
- graphify reference: query, path, explain
- OpenAIProvider
- asyncio
- public.tbl_dimensions
- Copilot Instructions: Phase Plans
- test_router_extended.py
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- Any
- .codex/skills/graphify/references/extraction-spec.md
- .copilot/skills/graphify/references/extraction-spec.md
- TestSuggestEntityEndpoint
- TestSuggestPropertyEndpoint
- public.tbl_abundances
- public.tbl_analysis_values
- Proposal Writing Guide
- patch
- Any
- TestPreviewEndpoint
- Design Docs
- Operations Docs
- README Instructions
- Testing Docs
- SIMS Target ID Contract Proposal
- public.tbl_sites
- TestSuggestTypeEndpoint
- .test_suggest_entity_response_model
- TestReconcileEndpoint
- TestGeoNamesEdgeCases
- public.tbl_value_classes
- Development Docs
- Proposal Document Structure
- .test_reconcile_successful_query
- SIMS/proposals/README.md
- coding-practices.instructions.md
- diagrams.instructions.md
- github-workflow.instructions.md
- python.instructions.md
- public.tbl_temperatures
- public.tbl_updates_log
- public.tbl_years_types

## God Nodes (most connected - your core abstractions)
1. `with_test_config()` - 305 edges
2. `MockConfigProvider` - 195 edges
3. `ExtendedMockConfigProvider` - 153 edges
4. `Config` - 117 edges
5. `ConfigValue` - 90 edges
6. `ConfigFactory` - 77 edges
7. `ConfigLike` - 59 edges
8. `BaseRepository` - 59 edges
9. `ReconciliationStrategy` - 59 edges
10. `IdentityService` - 57 edges

## Surprising Connections (you probably didn't know these)
- `TestModelSerialization` --uses--> `TypeRef`  [INFERRED]
  tests/api/test_model.py → src/api/model.py
- `TestReconCandidate` --uses--> `TypeRef`  [INFERRED]
  tests/api/test_model.py → src/api/model.py
- `TestReconServiceManifest` --uses--> `TypeRef`  [INFERRED]
  tests/api/test_model.py → src/api/model.py
- `TestSuggestEntityItem` --uses--> `TypeRef`  [INFERRED]
  tests/api/test_model.py → src/api/model.py
- `TestReconQuery` --uses--> `ReconPropertyConstraint`  [INFERRED]
  tests/api/test_model.py → src/api/model.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Hybrid Retrieval Pipeline** — src_mcp_readme_pgtrgm, src_mcp_readme_pgvector, src_mcp_readme_searchlookup, src_mcp_readme_mcp_tools, src_mcp_readme_hybrid_retrieval [EXTRACTED 0.90]
- **MCP Server Core Components** — src_mcp_readme_seadmcpserverserver, src_mcp_readme_searchlookup, src_mcp_readme_getbyid, src_mcp_readme_listlookuptables, src_mcp_readme_searchlookupparams [EXTRACTED 0.95]
- **SIMS Entity Subtype Classification** — docs_sims_tracked_entities_provider_owned, docs_sims_tracked_entities_shared_metadata, docs_sims_tracked_entities_relationship, docs_sims_implementation_view_identity_policy [EXTRACTED 0.95]
- **SIMS Identity Resolution Lifecycle** — sims_source_scope, sims_submission, sims_source_identity, sims_tracked_identity, sims_binding, sims_binding_set, sims_change_request [EXTRACTED 0.95]
- **Taxonomic Tree Hierarchy** — tests_config_entities_taxa_tree_order, tests_config_entities_taxa_tree_family, tests_config_entities_taxa_tree_genus, tests_config_entities_taxa_tree_master [EXTRACTED 0.95]
- **SIMS Core Storage Tables** — sims_source_scope, sims_submission, sims_source_identity, sims_tracked_identity, docs_sims_implementation_view_binding, sims_binding_set [EXTRACTED 1.00]
- **SIMS Three-Step Decision Flow** — docs_sims_implementation_view_identity_resolution, sims_binding_set, sims_change_request [EXTRACTED 1.00]

## Communities (260 total, 36 thin omitted)

### Community 0 - "MockConfigProvider"
Cohesion: 0.03
Nodes (104): ConfigProvider, Config, Create a deep copy of the configuration., Container for configuration elements., ConfigProvider, MockConfigProvider, ABC, Abstract configuration provider for dependency injection (+96 more)

### Community 1 - "ValueError"
Cohesion: 0.06
Nodes (40): shutdown(), startup(), on_event, main(), Return exit code: 0 = OK, 1 = error or missing scopes (verify mode)., _seed(), get_config_dep(), get_config_dependency() (+32 more)

### Community 2 - "with_test_config"
Cohesion: 0.05
Nodes (61): register, Boost scores based on place name context, Site-specific reconciliation with place names and coordinates, SiteReconciliationStrategy, SiteRepository, ExtendedMockConfigProvider, Get the mock connection object for assertions, Extended MockConfigProvider that allows setting config after initialization (+53 more)

### Community 3 - "BaseRepository"
Cohesion: 0.04
Nodes (71): DataTypeReconciliationStrategy, DataTypeRepository, BaseRepository, register, StrategySpecification, Data Type-specific reconciliation with data type names and descriptions, Data Type-specific query proxy, DimensionReconciliationStrategy (+63 more)

### Community 4 - "TestClient"
Cohesion: 0.12
Nodes (13): TestClient, Extended tests for reconcile endpoint edge cases., Test reconcile with JSON content type., Test reconcile with double-encoded JSON string., Test reconcile with empty request body., Test reconcile adds default type when missing., Test reconcile validates query fields., Test reconcile handles multiple queries. (+5 more)

### Community 5 - "test_service.py"
Cohesion: 0.06
Nodes (59): datetime, get_identity_service(), FastAPI dependency — returns a fresh IdentityService per request. The service…, SIMS identity management module. Provides identity policy, UUID allocation, and…, Binding, BindingSet, BindingSetResponse, BindRequest (+51 more)

### Community 6 - "GeoNamesReconciliationStrategy"
Cohesion: 0.06
Nodes (28): GeoNamesReconciliationStrategy, register, Location-specific reconciliation with place names and coordinates, Test GeoNamesReconciliationStrategy functionality, Test initialization with default specification, Test initialization with a provided repository instance, Test initialization with custom specification, Test initialization with strategy options from config (+20 more)

### Community 7 - "TestDotNotationUtilities"
Cohesion: 0.05
Nodes (27): dget(), dotexpand(), Expands paths with ',' and ':'., Tests for dot notation utility functions., Test dotexpand with simple path., Test dotexpand with colon notation., Test dotexpand with comma-separated paths., Test dotexpand with mixed notation. (+19 more)

### Community 8 - "GeoNamesProxy"
Cohesion: 0.05
Nodes (42): Response, GeoNamesProxy, NotSupportedError, Any, Self, Fetch details for a specific geonameId., Minimal async proxy around the GeoNames API using httpx. Usage: async with…, Internal GET helper with basic GeoNames error normalization. (+34 more)

### Community 9 - "IdentityPolicy"
Cohesion: 0.07
Nodes (26): IdentityPolicy, Path, Re-read the YAML file (useful after hot-reloading config)., Return the policy file path, honouring the IDENTITY_POLICY_FILE env var., Raise ValueError on a malformed policy file. Called once on load., Loaded identity policy. Instantiate once and re-use. Parameters ----------…, Return the policy for *entity_type*, falling back to defaults., Return entity types explicitly listed in the policy file. (+18 more)

### Community 10 - "TestClient"
Cohesion: 0.12
Nodes (13): TestClient, Test property suggestion endpoint, Test getting all properties without filter - returns properties from all…, Test filtering properties by query string, Test filtering properties by name, Test filtering properties by description, Test query with no matches, Test filtering properties by site entity type (+5 more)

### Community 11 - "test_config_extended.py"
Cohesion: 0.04
Nodes (45): BaseResolver, is_config_path(), is_path_to_existing_file(), LoadResolver, Any, Path, Save configuration to the YAML file. This method preserves the raw YAML…, Resolve configuration directives in self.data. (+37 more)

### Community 12 - "AdministrativeRegionReconciliationStrategy"
Cohesion: 0.04
Nodes (43): AdministrativeRegionReconciliationStrategy, register, Administrative region-specific reconciliation, Test getting display name., Test inherited methods from LocationReconciliationStrategy., Test get_id_path returns strategy key., Test getting properties metadata., Test basic initialization and registration of administrative region strategy. (+35 more)

### Community 13 - "test_suggest.py"
Cohesion: 0.06
Nodes (57): FastAPI, Any, OpenRefine Suggest API implementation for autocomplete and inline previews.…, Suggest entity types based on prefix. Args: prefix: Optional prefix to filter…, Suggest properties based on prefix and optional entity type. Args: prefix:…, Generate compact HTML preview for OpenRefine flyout/tooltip. Returns JSON with…, Suggest entities based on prefix (autocomplete). Args: prefix: The text prefix…, render_flyout_preview() (+49 more)

### Community 14 - "router.py"
Cohesion: 0.16
Nodes (21): JSONResponse, Request, flyout_entity(), is_alive(), meta(), get, post, Property suggestion endpoint for OpenRefine. Returns available properties that… (+13 more)

### Community 15 - "FeatureTypeReconciliationStrategy"
Cohesion: 0.05
Nodes (34): FeatureTypeReconciliationStrategy, Any, BaseRepository, register, StrategySpecification, Feature-specific reconciliation with feature names and descriptions, Fetch details for a specific site., create_connection_mock() (+26 more)

### Community 16 - "test_repository.py"
Cohesion: 0.12
Nodes (25): BindingRepository, CRUD for sead_identity.source_scopes., CRUD for sead_identity.submissions., CRUD for sead_identity.source_identities and source_identity_keys. Idempotency:…, CRUD for sead_identity.tracked_identities., CRUD for sead_identity.bindings., SourceIdentityRepository, SourceScopeRepository (+17 more)

### Community 17 - "IdentityService"
Cohesion: 0.06
Nodes (39): associate_change_request(), AssociateChangeRequestBody, confirm_binding_set(), detect_change(), get_binding_set(), list_scopes(), BaseModel, get (+31 more)

### Community 18 - "reset_config_provider"
Cohesion: 0.13
Nodes (17): Reset to the default singleton provider, Reset singleton - useful for testing, reset_config_provider(), Fixture to reset Config Store and provider before each test, Restore production configuration provider, reset_config(), restore_production_config(), fixture (+9 more)

### Community 19 - "_parse_list_expression"
Cohesion: 0.05
Nodes (34): _parse_list_expression(), Any, Parse and evaluate list expressions with "@value:" directives and list…, Helper function for replace_references, Recursively searches dict for values matching @value directives optionally with…, _replace_references(), dotget(), Gets element from dict. Path can be x.y.y or x_y_y or x:y:y. if path is x:y:y… (+26 more)

### Community 20 - "ResolutionRequest"
Cohesion: 0.09
Nodes (32): ChangeDetectionRequest, IdentitySignal, An identity signal submitted for resolution., Input to the Resolve Identity operation. Represents one domain entity submitted…, Input to the Detect Change operation., ResolutionRequest, TestResolutionRequest, asyncio (+24 more)

### Community 21 - "TranslationService"
Cohesion: 0.16
Nodes (12): RuntimeError, LanguageDetection, Translation service using LLM, LLM-based translation service, Detect the language of input text, Translate text from source to target language, Simple heuristics to detect non-English text, TranslationService (+4 more)

### Community 22 - "PostgreSQL Authority Schema"
Cohesion: 0.05
Nodes (48): FastAPI, Feature Flags, get_by_id, Hybrid Retrieval, list_lookup_tables, MCPTools, MethodsRAGStrategy, nomic-embed-text (+40 more)

### Community 23 - "_make_service"
Cohesion: 0.15
Nodes (14): Output of a single entity resolution within a Resolve call., ResolutionOutcome, TestResolutionOutcome, _make_binding(), _make_binding_set(), _make_service(), _make_source_identity(), _make_tracked_identity() (+6 more)

### Community 24 - "model.py"
Cohesion: 0.07
Nodes (36): APIResponse, ExtendDescriptor, PreviewTemplate, BaseModel, How OpenRefine can view a resource (usually an entity page)., Preview (iframe) settings., Suggest endpoint descriptor. OpenRefine expects at least: { "service_url":…, Data extension endpoint descriptor. (+28 more)

### Community 25 - "SEADMCPServer"
Cohesion: 0.06
Nodes (27): Any, AsyncConnection, Optional cross-encoder reranking Not implemented in Phase 1 - returns…, Embedded MCP server for SEAD reconciliation This provides a clean MCP-compliant…, Initialize MCP server with database connection Args: connection: Active async…, List all available lookup tables with metadata, Browse paginated rows from a lookup table, Hybrid retrieval tool (core reconciliation operation) This is the primary MCP… (+19 more)

### Community 26 - "GeoNamesRepository"
Cohesion: 0.09
Nodes (16): GeoNamesRepository, BaseRepository, StrategySpecification, patch, Test find with custom configuration, Test get_details functionality, Test that fetch_by_alternate_identity raises NotImplementedError, Test GeoNamesRepository functionality (+8 more)

### Community 27 - "TestListOperations"
Cohesion: 0.05
Nodes (22): Tests for list operations with include directives., Test that simple include directive still works as before., Test prepending items to an included list., Test appending items to an included list., Test prepending and appending items to an included list., Test concatenating multiple included lists., Test complex expression with multiple includes and literals., Test include with nested path. (+14 more)

### Community 28 - "_make_service_mock"
Cohesion: 0.11
Nodes (13): _make_client(), _make_outcome(), _make_service_mock(), _make_submission(), TestClient, Build a TestClient with the given service mock injected., Return a MagicMock IdentityService with sensible async return values., TestAssociateChangeRequest (+5 more)

### Community 29 - "TrackedIdentity"
Cohesion: 0.12
Nodes (14): ModelT, SEAD-side identity anchor for a domain entity. tracked_identity_uuid IS the…, TrackedIdentity, BaseRepository, BindingSetRepository, _now(), Any, Idempotent upsert — returns existing identity if any key already matches. (+6 more)

### Community 30 - "render_preview"
Cohesion: 0.10
Nodes (25): HTMLResponse, preview(), Preview endpoint for OpenRefine reconciliation results, Provides a generic HTML preview for a given entity ID., render_preview(), mock_strategy_with_get_details(), asyncio, Test error when URI path has insufficient parts (+17 more)

### Community 31 - "OllamaProvider"
Cohesion: 0.10
Nodes (19): OllamaProvider, Any, register, Ollama local LLM provider, asyncio, skip, Test completion with custom options passed via kwargs, Test completion with explicit options dictionary (+11 more)

### Community 32 - "ReconQuery"
Cohesion: 0.07
Nodes (27): field_validator, A single reconciliation query., Batch queries: OpenRefine posts a JSON object mapping arbitrary keys to…, ReconBatchRequest, ReconQuery, Test ReconQuery model., Test minimal valid ReconQuery with just query string., Test ReconQuery with all fields. (+19 more)

### Community 33 - "TestReplaceReferences"
Cohesion: 0.05
Nodes (20): Test replace_references leaves non-reference strings unchanged., Test replace_references with nested dict structure., Test replace_references with list containing references., Test replace_references with mixed list and dict structures., Test replace_references with reference pointing to another reference., Test replace_references with reference pointing to dict., Test replace_references with reference pointing to list., Test replace_references with multiple references to same path. (+12 more)

### Community 34 - "MCPTools"
Cohesion: 0.09
Nodes (23): Candidate, GetByIdParams, Parameters for hybrid search_lookup tool, Parameters for get_by_id tool, SearchLookupParams, MCPTools, Any, AsyncConnection (+15 more)

### Community 35 - "replace_env_vars"
Cohesion: 0.08
Nodes (20): Replaces recursively values in `data` that matches `${ENV_VAR}` with…, replace_env_vars(), Tests for replace_env_vars function., Test replace_env_vars with simple environment variable., Test replace_env_vars with nonexistent environment variable., Test replace_env_vars with regular string (no replacement)., Test replace_env_vars with partial patterns (no replacement)., Test replace_env_vars with empty variable name. (+12 more)

### Community 36 - "test_mcp.py"
Cohesion: 0.13
Nodes (26): SEAD MCP Server - Embedded Model Context Protocol implementation Provides a…, Candidate, GetByIdResult, LookupTable, MCPError, BaseModel, MCP data models for SEAD reconciliation These models follow the MCP tool…, A single lookup candidate with scores (+18 more)

### Community 37 - "LLMModificationTypeReconciliationStrategy"
Cohesion: 0.11
Nodes (11): Exception, LLMModificationTypeReconciliationStrategy, register, LLM-powered modification type reconciliation strategy, Test general error handling, asyncio, Test fetching lookup data from database, Test formatting lookup data for LLM prompt (+3 more)

### Community 39 - "LLMReconciliationStrategy"
Cohesion: 0.13
Nodes (12): LLMReconciliationStrategy, Any, BaseRepository, StrategySpecification, Convert LLM response to reconciliation candidate format, Find candidates using LLM-powered reconciliation, Base class for LLM-powered reconciliation strategies, Return a description of the lookup domain for the LLM context (+4 more)

### Community 40 - "01_tables.sql"
Cohesion: 0.01
Nodes (136): tbl_abundance_elements, tbl_abundance_ident_levels, tbl_abundance_modifications, tbl_abundance_properties, tbl_abundances, tbl_activity_types, tbl_age_types, tbl_alt_ref_types (+128 more)

### Community 41 - "ReconCandidate"
Cohesion: 0.09
Nodes (21): Candidate entity returned by reconciliation., Batch response mirrors request keys -> {result: [...] }., ReconBatchResponse, ReconCandidate, ReconQueryResult, Test ReconCandidate model., Test minimal candidate with required fields only., Test candidate with all fields. (+13 more)

### Community 42 - ".fetch_all"
Cohesion: 0.10
Nodes (14): DictRow, Params, Any, Return the SQL query for fetching detailed information for a given entity ID., Fetch details for a specific location., Perform fuzzy name search, Fetch entity by alternate identity, Perform (possibly) fuzzy name search (+6 more)

### Community 43 - "TestMCPModels"
Cohesion: 0.07
Nodes (16): Raw retrieval scores from different channels, RawScores, Tests for MCP data models, Test Candidate model validation, Test Candidate without raw_scores, Test SearchLookupParams with defaults, Test SearchLookupParams with custom values, Test SearchLookupParams validation (+8 more)

### Community 44 - "ConfigFactory"
Cohesion: 0.03
Nodes (61): ConfigFactory, Factory for creating Config instances., Path, Test loading sub-config with relative path, Test CSV data loading feature using @load: notation, Test loading CSV data using direct file path with @load: notation, Test loading TSV (tab-separated) data using @load: notation, Test loading CSV with explicit comma delimiter option (+53 more)

### Community 45 - "04_views.sql"
Cohesion: 0.09
Nodes (33): public.master_set_reference, public.taxon_view, public.typed_analysis_values, public.view_bibliography_references, public.view_chronometric_ages, public.view_identified_by, public.view_occurrence_ids, public.view_physical_abundances (+25 more)

### Community 46 - "test_llm_input_format.py"
Cohesion: 0.06
Nodes (21): CSVFormatter, JSONFormatter, register, Unit tests for LLM input formatting functionality., Test CSVFormatter functionality, Test formatting with empty columns, Test formatting a single row, Test formatting with custom separator (+13 more)

### Community 47 - "ExtendRequestProperty"
Cohesion: 0.10
Nodes (20): ExtCell, ExtendRequest, ExtendRequestProperty, ExtendResponse, Property asked for in extension; name is optional convenience., OpenRefine POSTs: { "ids": ["Q1","Q2"], "properties":…, Extension cell value with proper field handling, Response: { "meta": [{"id":"P31","name":"instance of"}], "rows": { "Q1": {… (+12 more)

### Community 48 - "SuggestEntityResponse"
Cohesion: 0.17
Nodes (11): SuggestEntityItem, SuggestEntityResponse, Test SuggestEntityItem model., Test minimal entity item., Test entity item with all fields., Test SuggestEntityResponse model., Test entity response with multiple results., Test empty entity response. (+3 more)

### Community 49 - "BibliographicReferenceRepository"
Cohesion: 0.13
Nodes (6): BibliographicReferenceRepository, BaseRepository, StrategySpecification, asyncio, MonkeyPatch, TestBibliographicReferenceRepository

### Community 50 - "TestMultipleRepository"
Cohesion: 0.21
Nodes (8): parametrize, Test getting details with invalid ID., Test getting details when not found., Tests for common logic in various Repository classes., Test fuzzy name search., Test fuzzy name search with default limit., Test getting details with valid ID., TestMultipleRepository

### Community 51 - "TranslationCache"
Cohesion: 0.12
Nodes (13): Simple file-based cache for translations, Generate cache key from text and target language, Get cached translation, TranslationCache, Test cache key is case sensitive., Test cache key handles unicode text., Test cache key with empty text., Test cache key generation. (+5 more)

### Community 52 - "format_rows_for_llm"
Cohesion: 0.09
Nodes (18): format_rows_for_llm(), Format SQL-style rows into markdown/csv/json for LLM use. Returns…, patch, Test main formatting function, Test basic formatting functionality, Test formatting with custom column mapping, Test automatic format selection, Test with minimal column map (id and label only) (+10 more)

### Community 53 - "TestUtilityFunctions"
Cohesion: 0.11
Nodes (15): _has_non_scalar(), _is_scalar(), _resolve_format(), Test utility functions, Test _is_scalar returns True for scalar types, Test _is_scalar returns False for non-scalar types, Test _has_non_scalar returns True when non-scalar values present, Test _has_non_scalar returns False when only scalars present (+7 more)

### Community 54 - "strategies/test_strategy.py"
Cohesion: 0.16
Nodes (16): _DummyRepoInstance, _FakeRepository, _NoRepoStrategy, Any, asyncio, MonkeyPatch, _StubConfigValue, test_as_candidate_includes_distance_and_threshold() (+8 more)

### Community 55 - ".as_candidate"
Cohesion: 0.25
Nodes (4): Return the ID field name for this entity type, Return the label field name for this entity type, Return the URL path segment for this entity type, Convert entity data to OpenRefine candidate format

### Community 56 - "TestRegistry"
Cohesion: 0.14
Nodes (11): T, Test that registered_class_hook is called during registration, Tests for Registry class., Clear registry before each test., Test registering a function., Test registering with function type (calls function)., Test registering without explicit key (uses function name)., Test getting nonexistent key raises ValueError. (+3 more)

### Community 57 - "EmbeddingPopulator"
Cohesion: 0.14
Nodes (12): Connection, EmbeddingPopulator, Any, Generate embeddings for a batch of texts using Ollama. Returns list of…, Upsert a batch of embeddings into the entity's embedding table. Returns number…, Populate embeddings for a single entity. Returns total number of embeddings…, Async wrapper for populate_entity to enable concurrent processing., Populate embeddings for all entities (or single entity if specified). Uses… (+4 more)

### Community 58 - "asyncio"
Cohesion: 0.12
Nodes (14): debug, asyncio, Test that connection errors are properly handled with rollback. This test…, Tests specifically for DatabaseRepository transaction handling, Test that fetch_all properly handles errors and rolls back the transaction.…, Test that fetch_one properly handles errors and rolls back the transaction., Special test for debugging the transaction error with a debugger. To use this…, Debug test to reproduce and step through the transaction error. SET BREAKPOINTS… (+6 more)

### Community 59 - "main"
Cohesion: 0.18
Nodes (19): Environment, filter_entities_with_embeddings(), generate_semantic_sql(), generate_trigram_sql(), get_trigram_config(), load_entities_config(), main(), Any (+11 more)

### Community 60 - "TestStrategyRegistry"
Cohesion: 0.04
Nodes (33): _get_default_types(), get_reconciliation_metadata(), Collects reconciliation metadata from all registered strategies., Collects default types from all registered strategies for OpenRefine., Any, BaseRepository, StrategySpecification, Find candidate matches for the given query This method should be implemented by… (+25 more)

### Community 61 - "BibliographicReferenceReconciliationStrategy"
Cohesion: 0.22
Nodes (6): BibliographicReferenceReconciliationStrategy, register, Reconcile bibliographic references using exact identifiers and fuzzy text., _FakeBiblioRepo, BaseRepository, TestBibliographicReferenceReconciliationStrategy

### Community 62 - "tests/test_utility.py"
Cohesion: 0.05
Nodes (37): argument, main(), command, option, Populate embedding tables for SEAD authority entities using Ollama nomic-embed-…, FormatterRegistry, configure_logging(), create_db_uri() (+29 more)

### Community 63 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 64 - "TestMCPConfig"
Cohesion: 0.13
Nodes (14): MCPConfig, MCPRetrievalConfig, MCPTableConfig, BaseModel, MCP Configuration Settings for the embedded MCP server, including: - Enabled…, Configuration for a single lookup table, Default retrieval parameters, Main MCP server configuration (+6 more)

### Community 65 - "TestAdministrativeRegionDistinctionFromCountry"
Cohesion: 0.22
Nodes (8): CountryReconciliationStrategy, register, Country-specific reconciliation, Test that administrative region is distinct from country strategy., Administrative region has different key than country., Both administrative_region and country are registered., Both strategies inherit from LocationReconciliationStrategy., TestAdministrativeRegionDistinctionFromCountry

### Community 66 - "TestTranslationCacheGet"
Cohesion: 0.11
Nodes (10): Test cache retrieval., Test retrieving translation from memory cache., Test retrieving translation from file cache., Test retrieving non-existent translation returns None., Test memory cache is checked before file cache., Test handling corrupted cache file returns None., Test cache file without translation key., Test cache file with null translation. (+2 more)

### Community 67 - "create_schema.sh"
Cohesion: 0.22
Nodes (17): cleanup(), deploy_schema(), g_deploy_sql_filename, g_root_dir, g_script_dir, generate_deploy_sql(), generate_entity_schema(), GREEN (+9 more)

### Community 68 - "PropertySetting"
Cohesion: 0.14
Nodes (14): PropertySetting, ProposePropertiesDescriptor, Propose properties endpoint descriptor., Property setting for OpenRefine., Test ProposePropertiesDescriptor model., Test creating propose properties descriptor., Test PropertySetting model., Test creating a property setting. (+6 more)

### Community 69 - "get_reconcile_properties"
Cohesion: 0.09
Nodes (17): _compile_property_settings(), _get_properties(), get_reconcile_properties(), Any, Collects property suggestions returned by the `/properties endpoint` for…, Collects properties from all registered strategies or a specific strategy if…, Collects property settings from all registered strategies for OpenRefine.…, DummyRegistry (+9 more)

### Community 70 - "reconcile_queries"
Cohesion: 0.25
Nodes (13): Any, reconcile_queries(), _ConfigProvider, Any, asyncio, MonkeyPatch, _RecordingStrategy, test_reconcile_queries_builds_properties_and_candidates() (+5 more)

### Community 71 - "TestMarkdownFormatter"
Cohesion: 0.11
Nodes (11): MarkdownFormatter, Test handling of None values, Test handling of missing columns in rows, Test formatting with columns but no rows, Test MarkdownFormatter functionality, Test formatting with empty columns, Test formatting a single row, Test formatting multiple rows (+3 more)

### Community 72 - "patch"
Cohesion: 0.15
Nodes (11): import_sub_modules(), patch, Tests for configure_logging function., Test configure_logging with no options - adds console and file handlers., Test configure_logging with stdout handler., Test configure_logging with file handler., Test configure_logging with handler missing sink - handler is skipped., Test configure_logging with options but no handlers. (+3 more)

### Community 73 - "recursive_filter_dict"
Cohesion: 0.15
Nodes (11): Recursively filters a dictionary to include only keys in the given set. Args: D…, recursive_filter_dict(), Test that non-dict values are returned as-is., Test that non-dict input is returned as-is., Test that default mode is exclude., Tests for recursive_filter_dict function., Test exclude mode with simple dictionary., Test keep mode with simple dictionary. (+3 more)

### Community 74 - "TestTranslationCacheEdgeCases"
Cohesion: 0.12
Nodes (9): Test edge cases and error handling., Test handling special characters in text., Test handling very long text., Test whitespace is preserved in translations., Test simulated concurrent access (memory cache doesn't conflict)., Test initialization with Path object., Test handling empty target language., Test translations with JSON special characters. (+1 more)

### Community 75 - "asyncio"
Cohesion: 0.14
Nodes (11): asyncio, Test set updates memory cache., Test set creates file cache., Test file cache has correct format., Test set overwrites existing cache entry., Test set with unicode translation., Test handling file write errors still updates memory cache., Test set with empty translation. (+3 more)

### Community 76 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 77 - "TestTranslationCacheIntegration"
Cohesion: 0.12
Nodes (9): Integration tests for cache workflow., Test setting and getting translation., Test storing multiple translations., Test cache persists across different cache instances., Test memory cache is populated when reading from file., Test same text translated to different languages., Test translations are isolated by language., Test cache handles large number of entries. (+1 more)

### Community 78 - "Entity Schema Definitions"
Cohesion: 0.20
Nodes (14): AI Coding Agent Instructions, Base Configuration, Entity Schema Definitions, LLM Prompt Templates, Docker Config Template, Architecture Design Document, Developer Guide, MCP Architecture Outline (+6 more)

### Community 79 - "Binding Set"
Cohesion: 0.14
Nodes (25): SIMS Identity Policy, SIMS Conceptual Model, Binding Set State Machine, Change Detection Flow, Manual Confirmation and Change Request Association, Re-Submission (Matched Identity) Flow, Submission Setup Flow, Tracked Identity State Machine (+17 more)

### Community 80 - "Identity Policy"
Cohesion: 0.19
Nodes (14): Allocation Blocked Flow, First Submission (New Identity) Flow, Identity Policy, Identity Resolution, Identity Service, sead_superset_model.yml, identity_policy.yml, Provider-Proposed Shared Metadata Proposal (+6 more)

### Community 81 - "public.tbl_physical_samples"
Cohesion: 0.09
Nodes (26): public.tbl_feature_types, public.tbl_features, public.tbl_sample_description_types, public.tbl_sample_group_description_types, public.tbl_sample_group_sampling_contexts, public.tbl_sample_location_types, public.tbl_sample_types, public.tbl_alt_ref_types (+18 more)

### Community 82 - "test_translation_cache.py"
Cohesion: 0.14
Nodes (8): Translation caching to avoid repeated API calls, Comprehensive tests for TranslationCache., Test TranslationCache initialization., Test default cache directory is created., Test custom cache directory is created., Test initialization with existing directory., Test memory cache is initialized as empty dict., TestTranslationCacheInitialization

### Community 83 - "Any"
Cohesion: 0.20
Nodes (5): load_resource_yaml(), Any, Loads a resource YAML file from the resources folder., Tests for resource YAML helpers., TestResourceYaml

### Community 84 - ".find_candidates"
Cohesion: 0.18
Nodes (7): Any, BaseRepository, Exact match by national site identifier, Return the site-specific query proxy, Find candidate sites based on name, identifier, and optional geographic context, Boost scores based on geographic proximity, Boost scores based on place name context

### Community 85 - "LLMProvider"
Cohesion: 0.18
Nodes (7): LLMProvider, ProviderRegistry, ABC, Any, LLM Client abstraction supporting multiple providers, Abstract base class for LLM providers, Return a list of supported option keys and their default values

### Community 86 - "public.tbl_taxa_tree_master"
Cohesion: 0.12
Nodes (24): public.tbl_analysis_taxon_counts, public.tbl_biblio, public.tbl_taxa_synonyms, public.tbl_taxa_tree_authors, public.tbl_taxa_tree_families, public.tbl_taxa_tree_genera, public.tbl_taxa_tree_master, public.tbl_taxonomic_order_systems (+16 more)

### Community 87 - "TestExtCell"
Cohesion: 0.15
Nodes (7): Test ExtCell with str value., Test ExtCell accepts 'str' alias., Test ExtCell with all fields., Test ExtCell trims string values., Test ExtCell converts empty strings to None., Test ExtCell accepts 'type' alias., TestExtCell

### Community 88 - "test_model.py"
Cohesion: 0.15
Nodes (16): SuggestPropertyItem, SuggestPropertyResponse, SuggestTypeItem, SuggestTypeResponse, Comprehensive tests for API models (Pydantic schemas)., Test SuggestPropertyItem model., Test minimal property item., Test property item with description. (+8 more)

### Community 89 - "ModificationTypeRepository"
Cohesion: 0.22
Nodes (7): ModificationTypeRepository, Any, BaseRepository, Find modification type candidates using LLM, Modification type-specific query proxy, Fetch all modification types for LLM lookup, Fetch modification type lookup data

### Community 90 - "TestModelSerialization"
Cohesion: 0.17
Nodes (7): Test model serialization/deserialization., Test ReconQuery serialization round trip., Test ReconCandidate serialization round trip., Test ExtCell serialization preserves aliases., Test SuggestEntityResponse includes example in schema., Test ReconServiceManifest has proper config., TestModelSerialization

### Community 91 - "TestMCPResources"
Cohesion: 0.17
Nodes (7): Tests for MCPResources, Test get_server_info returns correct metadata, Test list_lookup_tables returns table metadata, Test get_lookup_rows returns paginated data, Test get_lookup_rows with invalid entity type, Test get_lookup_rows with language parameter raises NotImplementedError, TestMCPResources

### Community 92 - "Project README"
Cohesion: 0.25
Nodes (11): Conventional Commits, Docker Compose Service Definition, Docker Deployment Guide, System Diagrams, Operations Guide, Testing Guide, Docker Build Workflow, Semantic Release Workflow (+3 more)

### Community 93 - "TaxonReconciliationStrategy"
Cohesion: 0.24
Nodes (7): Any, BaseRepository, register, Future taxon reconciliation strategy, Fetch details for a specific taxon (placeholder)., TaxonReconciliationStrategy, TaxonRepository

### Community 94 - "authority.get_embedding_status"
Cohesion: 0.20
Nodes (8): authority.%1$I, pg_attribute, pg_class, pg_constraint, pg_namespace, pg_tables, s, authority.get_embedding_status()

### Community 95 - "TypeRef"
Cohesion: 0.29
Nodes (6): TypeRef, Test creating a valid TypeRef., Test TypeRef JSON serialization., Test TypeRef requires both id and name., Test TypeRef accepts empty strings., TestTypeRef

### Community 96 - "TestAPIResponse"
Cohesion: 0.20
Nodes (6): Test APIResponse generic wrapper., Test successful API response with data., Test error API response., Test API response with complex data type., Test API response defaults to success=True., TestAPIResponse

### Community 97 - "TestEdgeCases"
Cohesion: 0.20
Nodes (6): Tests for edge cases and error conditions., Test handling of malformed list literal., Test handling of empty include path., Test string with plus operators but no lists or includes., Test that plus signs within list values don't break parsing., TestEdgeCases

### Community 98 - "TestConfigFactoryEdgeCases"
Cohesion: 0.20
Nodes (6): Test ConfigFactory with various edge cases., load should return ConfigLike instances unchanged., load with None source should create empty config., load should accept dict source directly., load with skip_resolve should not resolve directives., TestConfigFactoryEdgeCases

### Community 99 - "TestReplaceReferencesPublicAPI"
Cohesion: 0.20
Nodes (6): Test the public replace_references function., Public function should use input data as full_data context., Should handle top-level list input., Should handle top-level string input., Integration test with multiple reference patterns., TestReplaceReferencesPublicAPI

### Community 100 - "public.tbl_methods"
Cohesion: 0.12
Nodes (23): public.tbl_analysis_entities, public.tbl_datasets, public.tbl_dating_uncertainty, public.tbl_methods, public.tbl_analysis_entity_ages, public.tbl_analysis_entity_dimensions, public.tbl_analysis_entity_prep_methods, public.tbl_chronologies (+15 more)

### Community 101 - "EntityPolicy"
Cohesion: 0.23
Nodes (5): EntityPolicy, Immutable policy snapshot for one entity type., TestEntityPolicyProperties, _provider_owned_policy(), _shared_metadata_policy()

### Community 102 - "Summary"
Cohesion: 0.10
Nodes (20): 💡 Analogy, 🧩 Conceptually, How to read it (quick), Hybrid RAG + MCP Flow, Hybrid RAG + MCP — System Architecture (Mermaid), 🧠 In one line, Key differences (at a glance), ⚙️ **MCP in essence** (+12 more)

### Community 103 - "ReconPropertyConstraint"
Cohesion: 0.23
Nodes (8): Property constraint in a query: property id + value., ReconPropertyConstraint, Test ReconPropertyConstraint model., Test creating a valid property constraint., Test property constraint with string value., Test property constraint with dict/object value., Test property constraint with list value., TestReconPropertyConstraint

### Community 104 - "configuration/test_utility.py"
Cohesion: 0.25
Nodes (7): Tests for src.configuration.utility helpers., List operations should concatenate literal lists and referenced lists., Invalid nested list expressions should be returned unchanged., @value directive should copy referenced data., test_replace_references_ignores_nested_list_expression(), test_replace_references_list_operations(), test_replace_references_simple_include()

### Community 105 - "TestFormatterRegistry"
Cohesion: 0.25
Nodes (5): Test the formatter registry system, Test that FormatterRegistry inherits from Registry, Test that formatters are properly registered, Test getting formatters from registry, TestFormatterRegistry

### Community 106 - ".test_real_database_multiple_queries"
Cohesion: 0.29
Nodes (6): manual, skip, Manual tests that require a real database connection. These tests are marked…, Test against real database with a single query. Requires: - Valid database…, Test against real database with multiple queries. This will reveal if the…, TestManualDatabaseTesting

### Community 107 - "normalize_text"
Cohesion: 0.33
Nodes (4): normalize_text(), Normalize text to match PostgreSQL's authority.immutable_unaccent(lower(text)).…, Tests for normalize_text function., TestNormalizeText

### Community 108 - "SIMS (SEAD Identity Management System)"
Cohesion: 0.32
Nodes (8): FastAPI, PostgreSQL 16+, SIMS Deployment Process, SIMS (SEAD Identity Management System), Domain Modeling Requirements (FR-15..20), Provider-Owned Entities, Relationship Entities (Bridges), Shared Metadata Entities

### Community 109 - "authority.location"
Cohesion: 0.40
Nodes (5): tbl_location_types, authority.fuzzy_location(), authority.location, public.tbl_location_types, public.tbl_locations

### Community 110 - "sead_identity.bindings"
Cohesion: 0.33
Nodes (5): sead_identity.bindings, sead_identity, sead_identity.source_identities, sead_identity.binding_sets, sead_identity.tracked_identities

### Community 111 - "Section Guidance"
Cohesion: 0.11
Nodes (17): Assumptions — Optional, Copilot Instructions: Phase Task Plans, Default Structure, Definition Of Done — Essential, Deliverables — Recommended, Open Questions — Optional, Output, Phase Summary — Essential (+9 more)

### Community 112 - "CHANGELOG.md"
Cohesion: 0.12
Nodes (16): [1.1.0](https://github.com/humlab-sead/sead_authority_service/compare/v1.0.0...v1.1.0) (2025-10-24), [1.2.0](https://github.com/humlab-sead/sead_authority_service/compare/v1.1.0...v1.2.0) (2025-10-24), [1.3.0](https://github.com/humlab-sead/sead_authority_service/compare/v1.2.0...v1.3.0) (2026-01-02), [1.4.0](https://github.com/humlab-sead/sead_authority_service/compare/v1.3.0...v1.4.0) (2026-01-02), [1.4.1](https://github.com/humlab-sead/sead_authority_service/compare/v1.4.0...v1.4.1) (2026-01-02), [1.4.2](https://github.com/humlab-sead/sead_authority_service/compare/v1.4.1...v1.4.2) (2026-01-02), [1.5.0](https://github.com/humlab-sead/sead_authority_service/compare/v1.4.2...v1.5.0) (2026-01-02), Bug Fixes (+8 more)

### Community 113 - "TestConfigUpdate"
Cohesion: 0.25
Nodes (5): Test Config.update with various input formats., Update should accept single tuple., Update should accept list of tuples., Update should initialize data if None., TestConfigUpdate

### Community 114 - "test_router.py"
Cohesion: 0.15
Nodes (9): app(), client(), MockStrategy, fixture, Unit tests for the API router endpoints., Mock strategy class with get_properties_meta method, Test error handling across endpoints, Create FastAPI test app with router (+1 more)

### Community 115 - "patch"
Cohesion: 0.15
Nodes (10): patch, Test type suggestion handles errors., Test flyout entity preview endpoint., Test flyout entity with GET request., Test flyout entity with POST request., Test flyout entity with missing ID parameter., Test flyout entity with empty ID parameter., Test flyout entity with invalid ID. (+2 more)

### Community 117 - "authority.taxa_synonym"
Cohesion: 0.50
Nodes (4): authority.fuzzy_taxa_synonym(), authority.taxa_synonym, public.tbl_taxa_synonyms, public.tbl_taxa_tree_master

### Community 118 - "authority.taxa_tree_family"
Cohesion: 0.50
Nodes (4): authority.fuzzy_taxa_tree_family(), authority.taxa_tree_family, public.tbl_taxa_tree_families, public.tbl_taxa_tree_orders

### Community 119 - "authority.taxa_tree_genus"
Cohesion: 0.50
Nodes (4): authority.fuzzy_taxa_tree_genus(), authority.taxa_tree_genus, public.tbl_taxa_tree_families, public.tbl_taxa_tree_genera

### Community 120 - "authority.taxa_tree_master"
Cohesion: 0.50
Nodes (4): authority.fuzzy_taxa_tree_master(), authority.taxa_tree_master, public.tbl_taxa_tree_genera, public.tbl_taxa_tree_master

### Community 121 - "authority.taxa_tree_order"
Cohesion: 0.50
Nodes (4): authority.fuzzy_taxa_tree_order(), authority.taxa_tree_order, public.tbl_record_types, public.tbl_taxa_tree_orders

### Community 123 - "fix_imports_in_file"
Cohesion: 0.60
Nodes (4): fix_imports_in_file(), main(), Path, Fix imports in a single file.

### Community 124 - ".test_whoami_returns_host_and_port"
Cohesion: 0.40
Nodes (4): skip, Test whoami endpoint for service discovery., Test whoami endpoint returns host and port information., TestWhoAmIEndpoint

### Community 125 - "TestViewTemplate"
Cohesion: 0.33
Nodes (4): Test ViewTemplate model., Test creating a valid view template., Test view template with multiple parameters., TestViewTemplate

### Community 126 - "dotset"
Cohesion: 0.11
Nodes (11): dotset(), Sets element in dict using dot notation x.y.z or x:y:z, Test dotset with simple path., Test dotset with colon notation., Test dotset overwrites existing values., Test dotset extends existing structure., Integration tests combining multiple utility functions., Test dotset and dotget work together. (+3 more)

### Community 127 - "TestMultipleReconciliationStrategy"
Cohesion: 0.32
Nodes (5): parametrize, Test reconciliation strategy., Test getting entity ID field name., Test get_property_settings method returns location-specific settings., TestMultipleReconciliationStrategy

### Community 128 - "test_provider"
Cohesion: 0.40
Nodes (5): fixture, Provide TestConfigProvider with test configuration, Configure logging for all tests with DEBUG level., setup_test_logging(), test_provider()

### Community 129 - ".test_is_alive"
Cohesion: 0.50
Nodes (3): Test health check endpoint, Test the health check endpoint, TestHealthCheck

### Community 131 - "authority.bibliographic_reference"
Cohesion: 0.67
Nodes (3): authority.bibliographic_reference, authority.fuzzy_bibliographic_reference(), public.tbl_biblio

### Community 132 - "authority.data_type_group"
Cohesion: 0.67
Nodes (3): authority.data_type_group, authority.fuzzy_data_type_group(), public.tbl_data_type_groups

### Community 133 - "authority.data_type"
Cohesion: 0.67
Nodes (3): authority.data_type, authority.fuzzy_data_type(), public.tbl_data_types

### Community 134 - "authority.dating_uncertainty"
Cohesion: 0.67
Nodes (3): authority.dating_uncertainty, authority.fuzzy_dating_uncertainty(), public.tbl_dating_uncertainty

### Community 135 - "authority.feature_type"
Cohesion: 0.67
Nodes (3): authority.feature_type, authority.fuzzy_feature_type(), public.tbl_feature_types

### Community 136 - "authority.feature"
Cohesion: 0.67
Nodes (3): authority.feature, authority.fuzzy_feature(), public.tbl_features

### Community 137 - "authority.method_group"
Cohesion: 0.67
Nodes (3): authority.fuzzy_method_group(), authority.method_group, public.tbl_method_groups

### Community 138 - "authority.method"
Cohesion: 0.67
Nodes (3): authority.fuzzy_method(), authority.method, public.tbl_methods

### Community 139 - "authority.modification_type"
Cohesion: 0.67
Nodes (3): authority.fuzzy_modification_type(), authority.modification_type, public.tbl_modification_types

### Community 140 - "authority.relative_age_type"
Cohesion: 0.67
Nodes (3): authority.fuzzy_relative_age_type(), authority.relative_age_type, public.tbl_relative_age_types

### Community 141 - "authority.relative_age"
Cohesion: 0.67
Nodes (3): authority.fuzzy_relative_age(), authority.relative_age, public.tbl_relative_ages

### Community 142 - "authority.sample_description_type"
Cohesion: 0.67
Nodes (3): authority.fuzzy_sample_description_type(), authority.sample_description_type, public.tbl_sample_description_types

### Community 143 - "authority.sample_group_description_type"
Cohesion: 0.67
Nodes (3): authority.fuzzy_sample_group_description_type(), authority.sample_group_description_type, public.tbl_sample_group_description_types

### Community 144 - "authority.sampling_context"
Cohesion: 0.67
Nodes (3): authority.fuzzy_sampling_context(), authority.sampling_context, public.tbl_sample_group_sampling_contexts

### Community 145 - "authority.sample_location_type"
Cohesion: 0.67
Nodes (3): authority.fuzzy_sample_location_type(), authority.sample_location_type, public.tbl_sample_location_types

### Community 146 - "authority.sample_type"
Cohesion: 0.67
Nodes (3): authority.fuzzy_sample_type(), authority.sample_type, public.tbl_sample_types

### Community 147 - "authority.taxa_tree_author"
Cohesion: 0.67
Nodes (3): authority.fuzzy_taxa_tree_author(), authority.taxa_tree_author, public.tbl_taxa_tree_authors

### Community 148 - "authority.taxonomic_order_system"
Cohesion: 0.67
Nodes (3): authority.fuzzy_taxonomic_order_system(), authority.taxonomic_order_system, public.tbl_taxonomic_order_systems

### Community 149 - "authority.taxonomy_note"
Cohesion: 0.67
Nodes (3): authority.fuzzy_taxonomy_note(), authority.taxonomy_note, public.tbl_taxonomy_notes

### Community 150 - "authority.location_type"
Cohesion: 0.67
Nodes (3): authority.fuzzy_location_type(), authority.location_type, public.tbl_location_types

### Community 151 - "authority.record_type"
Cohesion: 0.67
Nodes (3): authority.fuzzy_record_type(), authority.record_type, public.tbl_record_types

### Community 152 - "sead_identity.source_identity_keys"
Cohesion: 0.50
Nodes (3): sead_identity.source_identity_keys, sead_identity, sead_identity.source_identities

### Community 153 - "sead_identity.submission_source_identities"
Cohesion: 0.50
Nodes (3): sead_identity.submission_source_identities, sead_identity.source_identities, sead_identity.submissions

### Community 154 - "find_import_inconsistencies"
Cohesion: 0.67
Nodes (3): find_import_inconsistencies(), main(), Find files that import the same module using different paths.

### Community 155 - "ConfigStore"
Cohesion: 0.03
Nodes (53): ConfigStore, Any, Self, Check if a config is currently loaded., Unload a config from memory., Force reload a config from disk., Check if configuration is available (uses provider layer), Get configuration (uses provider layer) (+45 more)

### Community 156 - "._make_repo"
Cohesion: 0.39
Nodes (5): Any, asyncio, BaseRepository, MonkeyPatch, TestBaseRepositoryUnit

### Community 157 - "Taxa Tree Family Entity"
Cohesion: 0.50
Nodes (4): Taxa Tree Family Entity, Taxa Tree Genus Entity, Taxa Tree Master Entity, Taxa Tree Order Entity

### Community 158 - "ConfigLike"
Cohesion: 0.05
Nodes (31): Loader, SequenceNode, yaml_path_join(), yaml_str_join(), ConfigFactoryLike, ConfigLike, Any, Protocol (+23 more)

### Community 168 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 170 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 203 - "test_ollama.py"
Cohesion: 0.40
Nodes (4): BaseModel, Unit tests for OllamaProvider LLM implementation., Test Pydantic model for typed responses, ResponseModel

### Community 204 - "public.tbl_locations"
Cohesion: 0.17
Nodes (13): public.tbl_location_types, public.tbl_locations, public.tbl_relative_age_types, public.tbl_relative_ages, public.tbl_activity_types, public.tbl_rdb, public.tbl_rdb_codes, public.tbl_rdb_systems (+5 more)

### Community 205 - "TestSafeLoaderIgnoreUnknown"
Cohesion: 0.11
Nodes (12): Ignore unknown tags silently, SafeLoaderIgnoreUnknown, Test YAML custom constructors and utility functions., Test !join constructor joins sequence elements into string., Test !path_join and !jj constructors join paths correctly., Test is_path_to_existing_file with various invalid inputs., Test custom YAML loader that ignores unknown tags., Test loader handles unknown scalar tags gracefully. (+4 more)

### Community 206 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 207 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 208 - "OpenAIProvider"
Cohesion: 0.33
Nodes (3): OpenAIProvider, Any, register

### Community 209 - "asyncio"
Cohesion: 0.15
Nodes (7): asyncio, Test find_candidates functionality, Test find_candidates with properties, Test that limit is properly applied to results, Test get_details functionality, Test get_details with filtered kwargs, Test find_candidates with no results

### Community 210 - "public.tbl_dimensions"
Cohesion: 0.18
Nodes (12): public.tbl_analysis_value_dimensions, public.tbl_method_groups, public.tbl_coordinate_method_dimensions, public.tbl_dimensions, public.tbl_measured_value_dimensions, public.tbl_measured_values, public.tbl_sample_coordinates, public.tbl_sample_dimensions (+4 more)

### Community 211 - "Copilot Instructions: Phase Plans"
Cohesion: 0.17
Nodes (11): Copilot Instructions: Phase Plans, Cross-Phase Rules, Current Position Guidance, Importance And Skip Rules, Output, Phase Plan Requirements, Quality Checklist, Rules (+3 more)

### Community 212 - "test_router_extended.py"
Cohesion: 0.15
Nodes (11): app(), client(), fixture, Extended comprehensive tests for API router endpoints - adds missing coverage., Create FastAPI test app with router, Test config dependency injection., Test config dependency sets up store when not configured., Test various content type handling scenarios. (+3 more)

### Community 214 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 215 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 216 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 217 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 218 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 219 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 224 - "Any"
Cohesion: 0.17
Nodes (6): Any, Protocol, RowFormatter, _total_chars(), Test _total_chars calculation, Test _total_chars with empty rows

### Community 227 - "TestSuggestEntityEndpoint"
Cohesion: 0.17
Nodes (7): Test entity suggestion handles errors., Test entity suggestion returns multiple results., Test entity suggestion endpoint., Test entity suggestion returns results., Test entity suggestion with type filter., Test entity suggestion with empty prefix., TestSuggestEntityEndpoint

### Community 228 - "TestSuggestPropertyEndpoint"
Cohesion: 0.17
Nodes (7): Test property suggestion endpoint., Test property suggestion returns results., Test property suggestion with prefix filter., Test property suggestion with type filter., Test property suggestion with prefix and type filters., Test property suggestion handles errors., TestSuggestPropertyEndpoint

### Community 229 - "public.tbl_abundances"
Cohesion: 0.18
Nodes (11): public.tbl_abundances, public.tbl_modification_types, public.tbl_record_types, public.tbl_taxa_tree_orders, public.tbl_abundance_elements, public.tbl_abundance_ident_levels, public.tbl_abundance_modifications, public.tbl_abundance_properties (+3 more)

### Community 230 - "public.tbl_analysis_values"
Cohesion: 0.25
Nodes (11): public.tbl_analysis_boolean_values, public.tbl_analysis_dating_ranges, public.tbl_analysis_identifiers, public.tbl_analysis_integer_ranges, public.tbl_analysis_integer_values, public.tbl_analysis_notes, public.tbl_analysis_numerical_ranges, public.tbl_analysis_numerical_values (+3 more)

### Community 231 - "Proposal Writing Guide"
Cohesion: 0.18
Nodes (10): Proposal Template, Default Standard, Naming, Practical Rule Of Thumb, Proposal Writing Guide, Structure, Style, What A Proposal Should Do (+2 more)

### Community 233 - "patch"
Cohesion: 0.20
Nodes (8): patch, Test metadata endpoint includes property extensions, Integration tests for endpoint interactions, Test a complete reconciliation workflow, Test reconciliation metadata endpoint, Test metadata endpoint returns correct structure, TestEndpointIntegration, TestMetaEndpoint

### Community 236 - "Any"
Cohesion: 0.27
Nodes (4): Any, Fetch details for a specific entity., Convert Geonames data to OpenRefine candidate format, Find candidate matches for the given query This method should be implemented by…

### Community 237 - "TestPreviewEndpoint"
Cohesion: 0.20
Nodes (6): Test preview endpoint, Test preview with valid ID, Test preview with invalid ID format, Test preview with insufficient path parts, Test preview with too many path parts, TestPreviewEndpoint

### Community 238 - "Design Docs"
Cohesion: 0.22
Nodes (8): Common failure modes, Design Docs, Purpose, Scope boundaries, Size expectations, Sources to trust, What belongs, Writing rules

### Community 239 - "Operations Docs"
Cohesion: 0.22
Nodes (8): Concision and size expectations, Operations Docs, Purpose, Scope boundaries, Sources to trust, What belongs in `docs/OPERATIONS.md`, What does not belong in `docs/OPERATIONS.md`, Writing rules

### Community 240 - "README Instructions"
Cohesion: 0.22
Nodes (8): Concision and size expectations, Purpose, README Instructions, Scope boundaries, Sources to trust, What belongs in `README.md`, What does not belong in `README.md`, Writing rules

### Community 241 - "Testing Docs"
Cohesion: 0.22
Nodes (8): Concision and size expectations, Purpose, Scope boundaries, Sources to trust, Testing Docs, What belongs in `docs/TESTING.md`, What does not belong in `docs/TESTING.md`, Writing rules

### Community 242 - "SIMS Target ID Contract Proposal"
Cohesion: 0.36
Nodes (7): Current Status, Documents, Overview, Proposal Backlog, SIMS Target ID Contract Proposal, Target ID Contract Issue Draft, Target ID Contract PR Draft

### Community 243 - "public.tbl_sites"
Cohesion: 0.25
Nodes (8): public.tbl_site_natgridrefs, public.tbl_site_preservation_status, public.tbl_site_properties, public.tbl_site_references, public.tbl_site_site_types, public.tbl_site_type_groups, public.tbl_site_types, public.tbl_sites

### Community 244 - "TestSuggestTypeEndpoint"
Cohesion: 0.25
Nodes (5): Test type suggestion endpoint., Test type suggestion returns results., Test type suggestion with prefix filter., Test type suggestion with empty result., TestSuggestTypeEndpoint

### Community 245 - ".test_suggest_entity_response_model"
Cohesion: 0.25
Nodes (5): Test response model validation., Test entity suggestion response matches model., Test type suggestion response matches model., Test property suggestion response matches model., TestResponseModels

### Community 246 - "TestReconcileEndpoint"
Cohesion: 0.25
Nodes (5): Test reconciliation endpoint, Test when queries parameter is a JSON string, Test error when queries are missing, Test error when request contains invalid JSON, TestReconcileEndpoint

### Community 248 - "TestGeoNamesEdgeCases"
Cohesion: 0.25
Nodes (5): Test edge cases and error conditions, Test get_details when entity is not found, Test as_candidate handles various data types properly, Test score calculation with edge values, TestGeoNamesEdgeCases

### Community 249 - "public.tbl_value_classes"
Cohesion: 0.38
Nodes (7): public.tbl_analysis_categorical_values, public.tbl_data_type_groups, public.tbl_data_types, public.tbl_property_types, public.tbl_value_classes, public.tbl_value_type_items, public.tbl_value_types

### Community 250 - "Development Docs"
Cohesion: 0.29
Nodes (6): Development Docs, Purpose, Scope boundaries, Sources to trust, What belongs in `docs/DEVELOPMENT.md`, Writing rules

### Community 251 - "Proposal Document Structure"
Cohesion: 0.29
Nodes (6): Before Finishing, Cross-Document Rules, Document Type, Phase Shape, Proposal Document Structure, Structures

### Community 253 - ".test_reconcile_successful_query"
Cohesion: 0.40
Nodes (3): MockStrategies, Test successful reconciliation query, Mock Strategies class for testing

## Knowledge Gaps
- **378 isolated node(s):** `tbl_abundances`, `tbl_abundance_elements`, `tbl_abundance_ident_levels`, `tbl_abundance_modifications`, `tbl_activity_types` (+373 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `with_test_config()` connect `with_test_config` to `MockConfigProvider`, `.test_is_alive`, `ValueError`, `BaseRepository`, `TestClient`, `GeoNamesReconciliationStrategy`, `TestClient`, `AdministrativeRegionReconciliationStrategy`, `test_suggest.py`, `FeatureTypeReconciliationStrategy`, `TranslationService`, `SEADMCPServer`, `GeoNamesRepository`, `render_preview`, `OllamaProvider`, `MCPTools`, `test_mcp.py`, `LLMModificationTypeReconciliationStrategy`, `TestMultipleRepository`, `strategies/test_strategy.py`, `asyncio`, `TestStrategyRegistry`, `BibliographicReferenceReconciliationStrategy`, `TestAdministrativeRegionDistinctionFromCountry`, `test_ollama.py`, `asyncio`, `test_router_extended.py`, `TestMCPResources`, `TestSuggestEntityEndpoint`, `TestSuggestPropertyEndpoint`, `patch`, `TestPreviewEndpoint`, `test_router.py`, `patch`, `TestSuggestTypeEndpoint`, `.test_suggest_entity_response_model`, `TestReconcileEndpoint`, `TestGeoNamesEdgeCases`, `.test_whoami_returns_host_and_port`, `.test_reconcile_successful_query`, `TestMultipleReconciliationStrategy`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Why does `ConfigLike` connect `ConfigLike` to `MockConfigProvider`, `ValueError`, `BaseRepository`, `test_mcp.py`, `.test_real_database_multiple_queries`, `test_config_extended.py`, `ConfigFactory`, `router.py`, `IdentityService`, `SEADMCPServer`, `ConfigStore`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Why does `ConfigValue` connect `MockConfigProvider` to `ValueError`, `.__init__`, `BaseRepository`, `GeoNamesReconciliationStrategy`, `test_suggest.py`, `router.py`, `TranslationService`, `SEADMCPServer`, `GeoNamesRepository`, `render_preview`, `ConfigLike`, `OllamaProvider`, `MCPTools`, `test_mcp.py`, `LLMReconciliationStrategy`, `.as_candidate`, `TestStrategyRegistry`, `tests/test_utility.py`, `OpenAIProvider`, `.find_candidates`, `LLMProvider`?**
  _High betweenness centrality (0.082) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `MockConfigProvider` (e.g. with `ConfigLike` and `TestMockConfigProvider`) actually correct?**
  _`MockConfigProvider` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `ExtendedMockConfigProvider` (e.g. with `TestDatabaseRepositoryTransactionHandling` and `TestReconcileIntegration`) actually correct?**
  _`ExtendedMockConfigProvider` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `Config` (e.g. with `ConfigStore` and `TestConfigClone`) actually correct?**
  _`Config` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `ConfigValue` (e.g. with `ConfigLike` and `ConfigProvider`) actually correct?**
  _`ConfigValue` has 14 INFERRED edges - model-reasoned connections that need verification._