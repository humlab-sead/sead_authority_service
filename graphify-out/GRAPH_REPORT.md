# Graph Report - sead_authority_service  (2026-08-25)

## Corpus Check
- 243 files · ~194,945 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4483 nodes · 8780 edges · 271 communities (234 shown, 37 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 530 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `aa7f01bd`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- 01_tables.sql
- router.py
- Functional Requirements
- BaseRepository
- TestClient
- AdministrativeRegionReconciliationStrategy
- service.py
- MockConfigProvider
- GeoNamesProxy
- LLMProvider
- with_test_config
- test_suggest.py
- test_repository.py
- ExtendedMockConfigProvider
- IdentityPolicy
- FeatureTypeReconciliationStrategy
- TestStrategyRegistry
- IdentityService
- ResolutionRequest
- ConfigFactory
- ReconQuery
- test_service.py
- test_model.py
- configuration/config.py
- GeoNamesRepository
- TestListOperations
- _make_service_mock
- _parse_list_expression
- SEADMCPServer
- BibliographicReferenceRepository
- ._fetchone
- OllamaProvider
- render_preview
- TestConfigFactoryReferences
- TestReplaceReferences
- MCPTools
- SEAD MCP Server - Embedded Implementation
- .get_instance
- test_mcp.py
- config_fixtures.py
- 04_views.sql
- AbstractRepository
- TestRecursiveFilterDict
- ReconCandidate
- MockStrategy
- TestMCPModels
- ExtendRequestProperty
- metadata.py
- Provider-Proposed Shared Metadata Proposal
- public.tbl_physical_samples
- TestUtilityFunctions
- SuggestEntityResponse
- TranslationCache
- format_rows_for_llm
- LLMReconciliationStrategy
- normalize_text
- strategies/test_strategy.py
- public.tbl_methods
- public.tbl_taxa_tree_master
- LoadResolver
- TestConfigFactorySubConfigs
- .get_repository
- TestRegistry
- EmbeddingPopulator
- main
- SourceScope
- TestTranslationCacheSet
- AGENTS.md - AI Coding Agent Instructions
- TranslationService
- TestMCPConfig
- TestMarkdownFormatter
- sample (Aggregate Root)
- create_schema.sh
- TestPropertySetting
- .find_candidates
- TestCSVFormatter
- ModificationTypeRepository
- TestConfigFactoryLoadDirective
- asyncio
- SIMS Conceptual Model and Systems Design
- TestRecursiveUpdate
- SIMS Identity Policy Configuration
- ._make_repo
- TestTranslationCacheIntegration
- TestTranslationCacheEdgeCases
- reconcile_queries
- Dimension Details SQL
- test_translation_cache.py
- TestEnv2Dict
- public.tbl_locations
- .as_candidate
- TestExtCell
- public.tbl_analysis_values
- public.tbl_dimensions
- SuggestPropertyItem
- EntityPolicy
- TestModelSerialization
- TestMCPResources
- graphify reference: extra exports and benchmark
- SEAD Authority Service Main Configuration
- FastAPI Application
- public.tbl_abundances
- ReconPropertyConstraint
- TaxonReconciliationStrategy
- authority.get_embedding_status
- SEAD Authority Service Docker Assets README
- BaseRepository
- PostgreSQL (SEAD Database)
- graphify reference: extra exports and benchmark
- SubConfigResolver
- TestAPIResponse
- TestEdgeCases
- test_utility_extended.py
- TestJSONFormatter
- ConfigValue
- SEAD Authority Service - AI Coding Instructions
- SamplingContextReconciliationStrategy
- resolve_specification
- SEAD MCP Server (sead.pg)
- public.tbl_value_classes
- Config
- Design
- _replace_references
- configuration/test_utility.py
- test_llm_input_format.py
- TestPreviewTemplate
- check_imports.py
- LLM Config
- RAGHybridReconciliationStrategy
- public.tbl_sites
- graphify reference: add a URL and watch a folder
- RuntimeError
- Proposal Document Structure Instructions
- authority.location
- sead_identity.bindings
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: add a URL and watch a folder
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- graphify reference: GitHub clone and cross-repo merge
- .test_reference_to_non_list_appends_value
- TestDatabaseUtilities
- extraction-spec.md
- Graphify Skill (Codex)
- graphify Knowledge Graph Pipeline
- asyncio
- Identity Router
- ReconciliationStrategy
- authority.taxa_synonym
- authority.taxa_tree_family
- authority.taxa_tree_genus
- authority.taxa_tree_master
- authority.taxa_tree_order
- fix_imports_in_file
- Countries Resource
- test_config_extended.py
- LLM Configuration
- Any
- SIMS Identity Module
- TestConfigStoreClassMethods
- authority.bibliographic_reference
- authority.data_type
- authority.data_type_group
- authority.dating_uncertainty
- authority.feature
- authority.feature_type
- authority.location_type
- authority.method
- authority.method_group
- authority.modification_type
- authority.record_type
- authority.relative_age
- authority.relative_age_type
- authority.sample_description_type
- authority.sample_group_description_type
- authority.sample_location_type
- authority.sample_type
- authority.sampling_context
- authority.taxa_tree_author
- authority.taxonomic_order_system
- authority.taxonomy_note
- sead_identity.source_identity_keys
- sead_identity.submission_source_identities
- Path
- authority.feature_type
- Core Concepts
- ChangeDetectionResult
- authority.fuzzy_site
- build.sh
- site_location (Bridge)
- create_connection_mock
- sead_identity.source_scopes
- sead_identity.submissions
- sead_identity.source_identities
- sead_identity.binding_sets
- .get_lookup_rows
- .test_get_entity_id_field
- TestYAMLHelpers
- Test Configuration
- TestSafeLoaderIgnoreUnknown
- Relative Age Entity
- SIMS Proposals Directory
- dataset (Shared Metadata)
- 005_tracked_identities.sql
- test-ci.sh
- TestMultipleRepository
- Sampling Context Resource
- SIMS Diagrams
- .fetch_all
- TestViewTemplate
- tests/identity/__init__.py
- CHANGELOG.md - Version History
- Makefile
- Scoring Config
- project (Shared Metadata)
- authority-service
- public.tbl_temperatures
- public.tbl_updates_log
- public.tbl_years_types
- GeoNames Places Resource
- Taxon Resource (Empty)
- SIMS — SEAD Identity Management System
- TypeRef
- TestSuggestSubservice
- TestConfigSaveErrors
- Storage Design
- TestConfigResolveReferences
- Requirements Docs
- Constraints
- SIMS target_id Contract Proposal
- Canonical Use Cases
- ._cache_key
- .detect_language
- .get_details
- test_provider
- OpenAIProvider
- TestBaseResolver
- .test_whoami_returns_host_and_port
- .__init__
- configuration/provider.py
- .__init__
- .__init__
- _StubConfigValue

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
- `Docker Entity Table Specifications` --semantically_similar_to--> `Entity Table Specifications`  [EXTRACTED] [semantically similar]
  docker/config/entities.yml → config/entities.yml
- `Docker Configuration Template` --semantically_similar_to--> `SEAD Authority Service Main Configuration`  [INFERRED] [semantically similar]
  docker/config/config.yml → config/config.yml
- `Graphify Skill (Copilot)` --semantically_similar_to--> `Graphify Skill (Codex)`  [INFERRED] [semantically similar]
  .copilot/skills/graphify/SKILL.md → .codex/skills/graphify/SKILL.md
- `Embedded MCP Server` --semantically_similar_to--> `RAG Hybrid Strategy`  [INFERRED] [semantically similar]
  README.md → AGENTS.md
- `SIMS Identity Module (README)` --semantically_similar_to--> `SIMS Identity Module`  [INFERRED] [semantically similar]
  README.md → AGENTS.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Proposal and Planning Document Family** — _github_instructions_proposal_writing_guide_instructions, _github_instructions_proposal_document_structure_instructions, _github_instructions_phase_plan_instructions, _github_instructions_task_plan_instructions, concept_proposal_planning_docs [EXTRACTED 0.85]
- **Docker Build and Deployment Pipeline** — docker_readme, docker_docker_compose, docker_config_config, docker_dockerfile, docker_build_sh, ghcr_io_humlab_sead_sead_authority_service [EXTRACTED 0.90]
- **graphify Skill Reference Set** — _copilot_skills_graphify_references_hooks, _copilot_skills_graphify_references_query, _copilot_skills_graphify_references_transcribe, _copilot_skills_graphify_references_update, concept_graphify_pipeline [EXTRACTED 0.90]
- **RAG Hybrid Strategy Components** — docs_design_rag_hybrid_reconciliation_strategy, docs_design_mcp_server, docs_design_llm_integration, docs_design_pg_trgm, docs_design_pgvector, docker_config_prompts_reconciliation [EXTRACTED 0.90]
- **Multilingual Reconciliation Pipeline Prompts** — tests_config_prompts_language_detection, tests_config_prompts_translation, tests_config_prompts_abbreviation, tests_config_prompts_reconciliation [EXTRACTED 0.90]
- **Resource Definition Pattern (key, id_field, label_field, sql_queries)** — src_resources_location, src_resources_method, src_resources_sampling_context, src_resources_site [EXTRACTED 0.90]
- **SEAD Documentation Scope Boundaries** — _github_instructions_design_instructions, _github_instructions_development_instructions, _github_instructions_operations_instructions, _github_instructions_testing_instructions, _github_instructions_readme_instructions, concept_docs_scope_boundaries [EXTRACTED 0.90]
- **SEAD Authority Service Main Configuration** — config_config, config_entities, config_prompts, config_identity_policy [EXTRACTED 0.95]
- **MCP Server API Surface** — docs_mcp_server_sead_reconciliation_via_mcp_architecture_doc_outline_mcp_server, docs_mcp_server_sead_reconciliation_via_mcp_architecture_doc_outline_search_lookup, docs_mcp_server_sead_reconciliation_via_mcp_architecture_doc_outline_rerank, docs_mcp_server_sead_reconciliation_via_mcp_architecture_doc_outline_get_by_id [EXTRACTED 0.95]
- **Reconciliation Request Flow Participants** — docs_design_openrefine, docs_design_reconciliation_router, docs_design_reconciliation_orchestrator, docs_design_strategy_registry, docs_design_base_repository, docs_design_postgresql [EXTRACTED 0.95]
- **SIMS Aggregate Roots and Their Children** — docs_sims_tracked_entities_analysis_entity, docs_sims_tracked_entities_sample, docs_sims_tracked_entities_abundance, docs_sims_tracked_entities_taxa_tree_master, docs_sims_tracked_entities_aggregate_boundaries [EXTRACTED 0.95]
- **target_id Contract Proposal Artifacts** — docs_proposals_sims_target_id_contract, docs_proposals_sims_target_id_contract_issue, docs_proposals_sims_target_id_contract_pr, docs_proposals_sims_target_id_contract_target_id, docs_proposals_sims_target_id_contract_resolution_outcome [EXTRACTED 0.95]
- **Taxonomic Classification Hierarchy** — config_entities_taxa_tree_master, config_entities_taxa_tree_genus, config_entities_taxa_tree_family, config_entities_taxa_tree_order, config_entities_taxa_synonym, config_entities_record_type [EXTRACTED 0.95]
- **Taxonomic Hierarchy (Order → Family → Genus → Species)** — config_entities_taxa_tree_order, config_entities_taxa_tree_family, config_entities_taxa_tree_genus, config_entities_taxa_tree_master [EXTRACTED 0.95]
- **Graphify Skill Reference Documents** — _codex_skills_graphify_skill, _codex_skills_graphify_references_extraction_spec, _codex_skills_graphify_references_query, _codex_skills_graphify_references_update [EXTRACTED 1.00]
- **Reconciliation Request Flow** — src_api_router, src_reconcile, src_strategies_strategy, agents_strategy_registry_pattern [EXTRACTED 1.00]
- **SIMS Identity Module Components** — src_identity, src_api_identity_router, agents_sims_identity_module, docs_sims [EXTRACTED 1.00]
- **Details SQL Queries** — src_resources_country_details_sql, src_resources_data_type_details_sql, src_resources_dimension_details_sql, src_resources_feature_type_details_sql [INFERRED 0.75]
- **Fuzzy Search SQL Queries** — src_resources_country_fuzzy_find_sql, src_resources_data_type_fuzzy_find_sql, src_resources_dimension_fuzzy_find_sql, src_resources_feature_type_fuzzy_find_sql [INFERRED 0.75]
- **Resource Definitions** — src_resources_country_country, src_resources_data_type_data_type, src_resources_dimension_dimension, src_resources_feature_type_feature_type, src_resources_geonames_geonames [INFERRED 0.80]
- **SIMS Identity and Binding Set Lifecycle** — src_identity_readme_tracked_identity, src_identity_readme_binding_set, src_identity_readme_identity_service, docs_sims_proposals_provider_proposed_shared_metadata_proposal_workflow, docs_sims_proposals_provider_proposed_shared_metadata_fr28 [INFERRED 0.80]

## Communities (271 total, 37 thin omitted)

### Community 0 - "01_tables.sql"
Cohesion: 0.01
Nodes (136): tbl_abundance_elements, tbl_abundance_ident_levels, tbl_abundance_modifications, tbl_abundance_properties, tbl_abundances, tbl_activity_types, tbl_age_types, tbl_alt_ref_types (+128 more)

### Community 1 - "router.py"
Cohesion: 0.12
Nodes (26): HTMLResponse, JSONResponse, Request, Batch response mirrors request keys -> {result: [...] }., ReconBatchResponse, flyout_entity(), is_alive(), meta() (+18 more)

### Community 2 - "Functional Requirements"
Cohesion: 0.06
Nodes (35): API non-goals at this stage, API-visible concepts, Binding set requirements, Change Request completeness requirements, Conceptual model alignment, Core identity concepts, Domain Concepts, Domain modeling requirements (+27 more)

### Community 3 - "BaseRepository"
Cohesion: 0.05
Nodes (49): src/configuration/ - Config Provider Pattern, DataTypeReconciliationStrategy, DataTypeRepository, BaseRepository, register, StrategySpecification, Data Type-specific reconciliation with data type names and descriptions, Data Type-specific query proxy (+41 more)

### Community 4 - "TestClient"
Cohesion: 0.04
Nodes (58): app(), client(), fixture, patch, TestClient, Extended comprehensive tests for API router endpoints - adds missing coverage., Test entity suggestion handles errors., Test entity suggestion returns multiple results. (+50 more)

### Community 5 - "AdministrativeRegionReconciliationStrategy"
Cohesion: 0.03
Nodes (51): AdministrativeRegionReconciliationStrategy, register, Administrative region-specific reconciliation, CountryReconciliationStrategy, register, Country-specific reconciliation, Test getting display name., Test inherited methods from LocationReconciliationStrategy. (+43 more)

### Community 6 - "service.py"
Cohesion: 0.07
Nodes (46): datetime, SIMS identity management module. Provides identity policy, UUID allocation, and…, Binding, BindRequest, BaseModel, Domain models for the SIMS identity module. Maps directly to the CM concepts…, One source-to-tracked identity correspondence within a Binding Set., Input to the Bind operation: resolution outcomes to package into a Binding Set. (+38 more)

### Community 7 - "MockConfigProvider"
Cohesion: 0.05
Nodes (39): MockConfigProvider, Test config provider with controllable configuration. Note that the context…, GeoNamesReconciliationStrategy, Any, register, Fetch details for a specific entity., Location-specific reconciliation with place names and coordinates, Convert Geonames data to OpenRefine candidate format (+31 more)

### Community 8 - "GeoNamesProxy"
Cohesion: 0.05
Nodes (42): Response, GeoNamesProxy, NotSupportedError, Any, Self, Fetch details for a specific geonameId., Minimal async proxy around the GeoNames API using httpx. Usage: async with…, Internal GET helper with basic GeoNames error normalization. (+34 more)

### Community 9 - "LLMProvider"
Cohesion: 0.16
Nodes (8): LLMProvider, ProviderRegistry, ABC, Any, LLM Client abstraction supporting multiple providers, Abstract base class for LLM providers, Return a list of supported option keys and their default values, Registry

### Community 10 - "with_test_config"
Cohesion: 0.04
Nodes (50): app(), client(), MockStrategies, fixture, patch, TestClient, Unit tests for the API router endpoints., Test metadata endpoint includes property extensions (+42 more)

### Community 11 - "test_suggest.py"
Cohesion: 0.08
Nodes (56): FastAPI, Any, OpenRefine Suggest API implementation for autocomplete and inline previews.…, Suggest entity types based on prefix. Args: prefix: Optional prefix to filter…, Suggest properties based on prefix and optional entity type. Args: prefix:…, Generate compact HTML preview for OpenRefine flyout/tooltip. Returns JSON with…, Suggest entities based on prefix (autocomplete). Args: prefix: The text prefix…, render_flyout_preview() (+48 more)

### Community 12 - "test_repository.py"
Cohesion: 0.14
Nodes (19): BindingRepository, CRUD for sead_identity.source_scopes., CRUD for sead_identity.bindings., SourceScopeRepository, _fake_get_connection(), _make_conn(), _make_cursor(), _patch_connection() (+11 more)

### Community 13 - "ExtendedMockConfigProvider"
Cohesion: 0.04
Nodes (60): register, Boost scores based on place name context, Site-specific reconciliation with place names and coordinates, SiteReconciliationStrategy, SiteRepository, ExtendedMockConfigProvider, Get the mock connection object for assertions, Get the mock cursor object for assertions (+52 more)

### Community 14 - "IdentityPolicy"
Cohesion: 0.07
Nodes (26): IdentityPolicy, Path, Re-read the YAML file (useful after hot-reloading config)., Return the policy file path, honouring the IDENTITY_POLICY_FILE env var., Raise ValueError on a malformed policy file. Called once on load., Loaded identity policy. Instantiate once and re-use. Parameters ----------…, Return the policy for *entity_type*, falling back to defaults., Return entity types explicitly listed in the policy file. (+18 more)

### Community 15 - "FeatureTypeReconciliationStrategy"
Cohesion: 0.05
Nodes (34): Exception, FeatureTypeReconciliationStrategy, FeatureTypeRepository, Any, BaseRepository, register, StrategySpecification, Feature-specific reconciliation with feature names and descriptions (+26 more)

### Community 16 - "TestStrategyRegistry"
Cohesion: 0.06
Nodes (21): StrategyRegistry, Test retrieving a registered strategy, Test that getting unregistered strategy raises KeyError, Test is_registered returns True for registered strategy, Test is_registered returns False for unregistered strategy, Test suite for StrategyRegistry, Test registration with repository_cls argument, Set up clean registry state before each test (+13 more)

### Community 17 - "IdentityService"
Cohesion: 0.07
Nodes (46): associate_change_request(), AssociateChangeRequestBody, confirm_binding_set(), detect_change(), get_binding_set(), get_identity_service(), list_scopes(), BaseModel (+38 more)

### Community 18 - "ResolutionRequest"
Cohesion: 0.09
Nodes (32): ChangeDetectionRequest, IdentitySignal, An identity signal submitted for resolution., Input to the Resolve Identity operation. Represents one domain entity submitted…, Input to the Detect Change operation., ResolutionRequest, TestResolutionRequest, asyncio (+24 more)

### Community 19 - "ConfigFactory"
Cohesion: 0.04
Nodes (49): manual, main(), Return exit code: 0 = OK, 1 = error or missing scopes (verify mode)., _seed(), get_config_dep(), get_config_dependency(), ConfigFactory, Factory for creating Config instances. (+41 more)

### Community 20 - "ReconQuery"
Cohesion: 0.07
Nodes (27): field_validator, A single reconciliation query., Batch queries: OpenRefine posts a JSON object mapping arbitrary keys to…, ReconBatchRequest, ReconQuery, Test ReconQuery model., Test minimal valid ReconQuery with just query string., Test ReconQuery with all fields. (+19 more)

### Community 21 - "test_service.py"
Cohesion: 0.13
Nodes (21): Output of a single entity resolution within a Resolve call., One identity key associated with a Source Identity. A source identity may carry…, ResolutionOutcome, SourceIdentityKey, TestResolutionOutcome, _make_binding(), _make_binding_set(), _make_service() (+13 more)

### Community 22 - "test_model.py"
Cohesion: 0.08
Nodes (45): APIResponse, ExtendDescriptor, ExtendRequest, ExtendResponse, PreviewTemplate, PropertySetting, ProposePropertiesDescriptor, BaseModel (+37 more)

### Community 23 - "configuration/config.py"
Cohesion: 0.02
Nodes (83): configure_logging(), create_db_uri(), dget(), dotexists(), dotexpand(), dotget(), dotset(), env2dict() (+75 more)

### Community 24 - "GeoNamesRepository"
Cohesion: 0.07
Nodes (24): GeoNamesRepository, BaseRepository, StrategySpecification, asyncio, patch, Unit tests for GeoNames reconciliation strategy and query proxy., Test find with custom configuration, Test get_details functionality (+16 more)

### Community 25 - "TestListOperations"
Cohesion: 0.05
Nodes (22): Tests for list operations with include directives., Test that simple include directive still works as before., Test prepending items to an included list., Test appending items to an included list., Test prepending and appending items to an included list., Test concatenating multiple included lists., Test complex expression with multiple includes and literals., Test include with nested path. (+14 more)

### Community 26 - "_make_service_mock"
Cohesion: 0.11
Nodes (13): _make_client(), _make_outcome(), _make_service_mock(), _make_submission(), TestClient, Build a TestClient with the given service mock injected., Return a MagicMock IdentityService with sensible async return values., TestAssociateChangeRequest (+5 more)

### Community 27 - "_parse_list_expression"
Cohesion: 0.09
Nodes (17): _parse_list_expression(), Parse and evaluate list expressions with "@value:" directives and list…, Should return original on YAML parse error or accept valid YAML., Simple @value directive should be returned unchanged for later processing., Should return original expression if result would be empty., Should reject if referenced data contains nested lists., Should prepend literal list to referenced list., Should append literal list to referenced list. (+9 more)

### Community 28 - "SEADMCPServer"
Cohesion: 0.06
Nodes (27): Any, AsyncConnection, Optional cross-encoder reranking Not implemented in Phase 1 - returns…, Embedded MCP server for SEAD reconciliation This provides a clean MCP-compliant…, Initialize MCP server with database connection Args: connection: Active async…, List all available lookup tables with metadata, Browse paginated rows from a lookup table, Hybrid retrieval tool (core reconciliation operation) This is the primary MCP… (+19 more)

### Community 29 - "BibliographicReferenceRepository"
Cohesion: 0.08
Nodes (12): BibliographicReferenceReconciliationStrategy, BibliographicReferenceRepository, BaseRepository, register, StrategySpecification, Reconcile bibliographic references using exact identifiers and fuzzy text., _FakeBiblioRepo, asyncio (+4 more)

### Community 30 - "._fetchone"
Cohesion: 0.15
Nodes (9): ModelT, BaseRepository, BindingSetRepository, _now(), Any, Idempotent upsert — returns existing identity if any key already matches., CRUD for sead_identity.binding_sets., Generic base repository for Pydantic-backed row models. (+1 more)

### Community 31 - "OllamaProvider"
Cohesion: 0.08
Nodes (23): OllamaProvider, Any, register, Ollama local LLM provider, asyncio, BaseModel, skip, Unit tests for OllamaProvider LLM implementation. (+15 more)

### Community 32 - "render_preview"
Cohesion: 0.11
Nodes (22): Provides a generic HTML preview for a given entity ID., render_preview(), mock_strategy_with_get_details(), asyncio, Test error when URI path has insufficient parts, Test error when URI path has too many parts, Test error when entity is not found in database, Test that generated HTML has correct structure (+14 more)

### Community 33 - "TestConfigFactoryReferences"
Cohesion: 0.06
Nodes (17): Test internal reference replacement feature using @value: notation, Test simple internal reference replacement., Test reference to nested configuration path., Test reference using colon notation in path., Test reference pointing to entire dictionary., Test reference pointing to list., Test references within a list., Test that references pointing to other references are resolved. (+9 more)

### Community 34 - "TestReplaceReferences"
Cohesion: 0.05
Nodes (20): Test replace_references leaves non-reference strings unchanged., Test replace_references with nested dict structure., Test replace_references with list containing references., Test replace_references with mixed list and dict structures., Test replace_references with reference pointing to another reference., Test replace_references with reference pointing to dict., Test replace_references with reference pointing to list., Test replace_references with multiple references to same path. (+12 more)

### Community 35 - "MCPTools"
Cohesion: 0.09
Nodes (20): Candidate, Parameters for hybrid search_lookup tool, SearchLookupParams, MCPTools, Any, AsyncConnection, Optional cross-encoder reranking, Implements MCP tool operations over SEAD authority database (+12 more)

### Community 36 - "SEAD MCP Server - Embedded Implementation"
Cohesion: 0.04
Nodes (45): 1. Enable the Feature Flag, 2. Test the MCP Server, 3. Try It in Python REPL, 4. Integrate into a Strategy, 5. Enable and Test via OpenRefine, Connection errors, Feature flag not working, Getting Started (5 Minutes) (+37 more)

### Community 37 - ".get_instance"
Cohesion: 0.04
Nodes (39): Production config provider using Config Store singleton, SingletonConfigProvider, Path, Extended tests for src.configuration.provider module to improve coverage., unload_config should remove config from memory., reload_config should reload from disk., Test ConfigStore.consolidate error handling., consolidate should raise if context undefined. (+31 more)

### Community 38 - "test_mcp.py"
Cohesion: 0.13
Nodes (28): SEAD MCP Server - Embedded Model Context Protocol implementation Provides a…, Candidate, GetByIdParams, GetByIdResult, LookupTable, MCPError, BaseModel, MCP data models for SEAD reconciliation These models follow the MCP tool… (+20 more)

### Community 39 - "config_fixtures.py"
Cohesion: 0.09
Nodes (29): ConfigProvider, Reset singleton - useful for testing, config_context(), mock_config_context(), mock_connection(), patch_config_provider(), Any, fixture (+21 more)

### Community 40 - "04_views.sql"
Cohesion: 0.09
Nodes (33): public.master_set_reference, public.taxon_view, public.typed_analysis_values, public.view_bibliography_references, public.view_chronometric_ages, public.view_identified_by, public.view_occurrence_ids, public.view_physical_abundances (+25 more)

### Community 42 - "AbstractRepository"
Cohesion: 0.22
Nodes (7): AbstractRepository, ABC, Abstract base class for entity-specific query proxies, Return the unique key for this query proxy, Return the SQL queries defined in the specification, Return the SQL query defined in the specification for a given key., Return the SQL query for fuzzy finding entities

### Community 43 - "TestRecursiveFilterDict"
Cohesion: 0.12
Nodes (9): Test that non-dict values are returned as-is., Test that non-dict input is returned as-is., Test that default mode is exclude., Tests for recursive_filter_dict function., Test exclude mode with simple dictionary., Test keep mode with simple dictionary., Test exclude mode with nested dictionaries., Test keep mode with nested dictionaries. (+1 more)

### Community 44 - "ReconCandidate"
Cohesion: 0.10
Nodes (19): Candidate entity returned by reconciliation., ReconCandidate, ReconQueryResult, Test ReconCandidate model., Test minimal candidate with required fields only., Test candidate with all fields., Test score must be >= 0., Test score must be <= 100. (+11 more)

### Community 46 - "TestMCPModels"
Cohesion: 0.07
Nodes (16): Raw retrieval scores from different channels, RawScores, Tests for MCP data models, Test Candidate model validation, Test Candidate without raw_scores, Test SearchLookupParams with defaults, Test SearchLookupParams with custom values, Test SearchLookupParams validation (+8 more)

### Community 47 - "ExtendRequestProperty"
Cohesion: 0.11
Nodes (16): ExtCell, ExtendRequestProperty, Property asked for in extension; name is optional convenience., Extension cell value with proper field handling, Test ExtendRequestProperty model., Test property with ID only., Test property with ID and name., Test ExtendRequest model. (+8 more)

### Community 48 - "metadata.py"
Cohesion: 0.09
Nodes (21): _compile_property_settings(), _get_default_types(), _get_properties(), get_reconcile_properties(), get_reconciliation_metadata(), Any, Collects property suggestions returned by the `/properties endpoint` for…, Collects reconciliation metadata from all registered strategies. (+13 more)

### Community 49 - "Provider-Proposed Shared Metadata Proposal"
Cohesion: 0.31
Nodes (10): Provider-Proposed Shared Metadata Proposal, FR-20: Reject Unmatched Shared Metadata, FR-28: Provider-Proposed Shared Metadata, Proposal Workflow (Pending Materialization), BindingSet, IdentityService, models.py, ResolutionOutcome (DTO) (+2 more)

### Community 50 - "public.tbl_physical_samples"
Cohesion: 0.09
Nodes (26): public.tbl_feature_types, public.tbl_features, public.tbl_sample_description_types, public.tbl_sample_group_description_types, public.tbl_sample_group_sampling_contexts, public.tbl_sample_location_types, public.tbl_sample_types, public.tbl_alt_ref_types (+18 more)

### Community 51 - "TestUtilityFunctions"
Cohesion: 0.09
Nodes (15): _resolve_format(), Test utility functions, Test _is_scalar returns True for scalar types, Test _is_scalar returns False for non-scalar types, Test _has_non_scalar returns True when non-scalar values present, Test _has_non_scalar returns False when only scalars present, Test _has_non_scalar with empty rows, Test _total_chars calculation (+7 more)

### Community 52 - "SuggestEntityResponse"
Cohesion: 0.17
Nodes (11): SuggestEntityItem, SuggestEntityResponse, Test SuggestEntityItem model., Test minimal entity item., Test entity item with all fields., Test SuggestEntityResponse model., Test entity response with multiple results., Test empty entity response. (+3 more)

### Community 53 - "TranslationCache"
Cohesion: 0.13
Nodes (12): Translation caching to avoid repeated API calls, Simple file-based cache for translations, TranslationCache, Test cache key is case sensitive., Test cache key handles unicode text., Test cache key with empty text., Test cache key generation., Test cache key is MD5 hash of text:target_lang. (+4 more)

### Community 54 - "format_rows_for_llm"
Cohesion: 0.09
Nodes (18): format_rows_for_llm(), Format SQL-style rows into markdown/csv/json for LLM use. Returns…, patch, Test main formatting function, Test basic formatting functionality, Test formatting with custom column mapping, Test automatic format selection, Test with minimal column map (id and label only) (+10 more)

### Community 55 - "LLMReconciliationStrategy"
Cohesion: 0.13
Nodes (12): LLMReconciliationStrategy, Any, BaseRepository, StrategySpecification, Convert LLM response to reconciliation candidate format, Find candidates using LLM-powered reconciliation, Base class for LLM-powered reconciliation strategies, Return a description of the lookup domain for the LLM context (+4 more)

### Community 56 - "normalize_text"
Cohesion: 0.33
Nodes (4): normalize_text(), Normalize text to match PostgreSQL's authority.immutable_unaccent(lower(text)).…, Tests for normalize_text function., TestNormalizeText

### Community 57 - "strategies/test_strategy.py"
Cohesion: 0.16
Nodes (16): _DummyRepoInstance, _FakeRepository, _NoRepoStrategy, Any, asyncio, MonkeyPatch, _StubConfigValue, test_as_candidate_includes_distance_and_threshold() (+8 more)

### Community 58 - "public.tbl_methods"
Cohesion: 0.12
Nodes (23): public.tbl_analysis_entities, public.tbl_datasets, public.tbl_dating_uncertainty, public.tbl_methods, public.tbl_analysis_entity_ages, public.tbl_analysis_entity_dimensions, public.tbl_analysis_entity_prep_methods, public.tbl_chronologies (+15 more)

### Community 59 - "public.tbl_taxa_tree_master"
Cohesion: 0.12
Nodes (24): public.tbl_analysis_taxon_counts, public.tbl_biblio, public.tbl_taxa_synonyms, public.tbl_taxa_tree_authors, public.tbl_taxa_tree_families, public.tbl_taxa_tree_genera, public.tbl_taxa_tree_master, public.tbl_taxonomic_order_systems (+16 more)

### Community 60 - "LoadResolver"
Cohesion: 0.22
Nodes (9): LoadResolver, Path, Test LoadResolver for @load directives., LoadResolver should support custom delimiters., LoadResolver should return original string for missing files., LoadResolver should return original for unparseable files., LoadResolver should ignore non-dict options., LoadResolver should ignore options without filename. (+1 more)

### Community 61 - "TestConfigFactorySubConfigs"
Cohesion: 0.07
Nodes (16): Test loading sub-config with relative path, Test loading nested sub-configs (sub-config references another sub-config), Test loading multiple sub-configs in the same main config, Test sub-config containing lists, Test sub-config reference within a list, Test error handling when sub-config file doesn't exist, Test sub-config with environment variable substitution, Test sub-config with custom YAML constructors like !join and !path_join (+8 more)

### Community 62 - ".get_repository"
Cohesion: 0.15
Nodes (8): Any, BaseRepository, StrategySpecification, Find candidate matches for the given query This method should be implemented by…, Internal method to find candidates, can be overridden by subclasses, Fetch details for a specific entity., Return an instance of the query proxy for this strategy, Return OpenRefine-specific settings for properties (optional override for type-…

### Community 63 - "TestRegistry"
Cohesion: 0.14
Nodes (11): T, Test that registered_class_hook is called during registration, Tests for Registry class., Clear registry before each test., Test registering a function., Test registering with function type (calls function)., Test registering without explicit key (uses function name)., Test getting nonexistent key raises ValueError. (+3 more)

### Community 64 - "EmbeddingPopulator"
Cohesion: 0.14
Nodes (12): Connection, EmbeddingPopulator, Any, Generate embeddings for a batch of texts using Ollama. Returns list of…, Upsert a batch of embeddings into the entity's embedding table. Returns number…, Populate embeddings for a single entity. Returns total number of embeddings…, Async wrapper for populate_entity to enable concurrent processing., Populate embeddings for all entities (or single entity if specified). Uses… (+4 more)

### Community 65 - "main"
Cohesion: 0.18
Nodes (19): Environment, filter_entities_with_embeddings(), generate_semantic_sql(), generate_trigram_sql(), get_trigram_config(), load_entities_config(), main(), Any (+11 more)

### Community 66 - "SourceScope"
Cohesion: 0.21
Nodes (6): External namespace within which Source Identities are unique., SourceScope, Return the named scope, creating it if it does not exist., _make_source_scope(), TestSourceScope, TestGetOrCreateScope

### Community 67 - "TestTranslationCacheSet"
Cohesion: 0.12
Nodes (9): Test set updates memory cache., Test set creates file cache., Test file cache has correct format., Test set overwrites existing cache entry., Test set with unicode translation., Test handling file write errors still updates memory cache., Test set with empty translation., Test timestamp is in ISO format. (+1 more)

### Community 68 - "AGENTS.md - AI Coding Agent Instructions"
Cohesion: 0.15
Nodes (19): General Coding Practices Instructions, Python Architecture Instructions, AGENTS.md - AI Coding Agent Instructions, ConfigValue, Database Connection Singleton, OpenRefine Reconciliation API, RAG Hybrid Strategy, Schema Generation from Templates (+11 more)

### Community 69 - "TranslationService"
Cohesion: 0.23
Nodes (9): LanguageDetection, Translation service using LLM, LLM-based translation service, Translate text from source to target language, TranslationService, asyncio, TestTranslationServiceDetectLanguage, TestTranslationServiceHeuristics (+1 more)

### Community 70 - "TestMCPConfig"
Cohesion: 0.13
Nodes (14): MCPConfig, MCPRetrievalConfig, MCPTableConfig, BaseModel, MCP Configuration Settings for the embedded MCP server, including: - Enabled…, Configuration for a single lookup table, Default retrieval parameters, Main MCP server configuration (+6 more)

### Community 71 - "TestMarkdownFormatter"
Cohesion: 0.11
Nodes (10): Test handling of None values, Test handling of missing columns in rows, Test formatting with columns but no rows, Test MarkdownFormatter functionality, Test formatting with empty columns, Test formatting a single row, Test formatting multiple rows, Test that pipes are properly escaped (+2 more)

### Community 72 - "sample (Aggregate Root)"
Cohesion: 0.12
Nodes (18): abundance (Aggregate Root), abundance_ident_level (Bridge), abundance_modification (Bridge), abundance_property, Aggregate Boundaries, analysis_entity (Aggregate Root), citation (Shared Metadata), geochronology (+10 more)

### Community 73 - "create_schema.sh"
Cohesion: 0.22
Nodes (17): cleanup(), deploy_schema(), g_deploy_sql_filename, g_root_dir, g_script_dir, generate_deploy_sql(), generate_entity_schema(), GREEN (+9 more)

### Community 74 - "TestPropertySetting"
Cohesion: 0.33
Nodes (4): Test PropertySetting model., Test creating a property setting., Test property setting with additional settings dict., TestPropertySetting

### Community 75 - ".find_candidates"
Cohesion: 0.18
Nodes (7): Any, BaseRepository, Exact match by national site identifier, Return the site-specific query proxy, Find candidate sites based on name, identifier, and optional geographic context, Boost scores based on geographic proximity, Boost scores based on place name context

### Community 76 - "TestCSVFormatter"
Cohesion: 0.12
Nodes (10): CSVFormatter, Test CSVFormatter functionality, Test formatting with empty columns, Test formatting a single row, Test formatting with custom separator, Test CSV quoting when needed, Test handling of None values, Test handling of missing columns (+2 more)

### Community 77 - "ModificationTypeRepository"
Cohesion: 0.22
Nodes (7): ModificationTypeRepository, Any, BaseRepository, Find modification type candidates using LLM, Modification type-specific query proxy, Fetch all modification types for LLM lookup, Fetch modification type lookup data

### Community 78 - "TestConfigFactoryLoadDirective"
Cohesion: 0.07
Nodes (16): Test CSV data loading feature using @load: notation, Test loading CSV data using direct file path with @load: notation, Test that loading nonexistent CSV file returns the directive argument, Test that @load with path to non-dict value returns directive argument, Test loading multiple CSV files in the same config, Test @load directive within deeply nested configuration, Test @load directive within a list, Test loading an empty CSV file fails and returns filepath (+8 more)

### Community 79 - "asyncio"
Cohesion: 0.15
Nodes (11): asyncio, Test cache retrieval., Test retrieving translation from memory cache., Test retrieving translation from file cache., Test retrieving non-existent translation returns None., Test memory cache is checked before file cache., Test handling corrupted cache file returns None., Test cache file without translation key. (+3 more)

### Community 80 - "SIMS Conceptual Model and Systems Design"
Cohesion: 0.13
Nodes (15): 1. Value objects are aggregate state, not identity targets, 2. Canonical SEAD identity must remain distinct from aliasing identifiers, 3. A Change Request must not be applied until all referenced identities are resolved, Binding Set Lifecycle, Compact Summary, Decision Flow, Deferred Issues, Design Intent (+7 more)

### Community 81 - "TestRecursiveUpdate"
Cohesion: 0.17
Nodes (7): Tests for recursive_update function., Test simple dictionary update., Test that values are overwritten., Test recursive update of nested dictionaries., Test that non-dict values overwrite dict values., Test with empty dictionaries., TestRecursiveUpdate

### Community 82 - "SIMS Identity Policy Configuration"
Cohesion: 0.14
Nodes (16): Data Type Entity, Data Type Group Entity, Feature Entity, Feature Type Entity, Method Entity, Method Group Entity, Record Type Entity, Taxa Synonym Entity (+8 more)

### Community 83 - "._make_repo"
Cohesion: 0.39
Nodes (5): Any, asyncio, BaseRepository, MonkeyPatch, TestBaseRepositoryUnit

### Community 84 - "TestTranslationCacheIntegration"
Cohesion: 0.12
Nodes (9): Integration tests for cache workflow., Test setting and getting translation., Test storing multiple translations., Test cache persists across different cache instances., Test memory cache is populated when reading from file., Test same text translated to different languages., Test translations are isolated by language., Test cache handles large number of entries. (+1 more)

### Community 85 - "TestTranslationCacheEdgeCases"
Cohesion: 0.11
Nodes (10): Test edge cases and error handling., Test handling special characters in text., Test handling very long text., Test whitespace is preserved in translations., Test behavior when cache directory has permission issues., Test simulated concurrent access (memory cache doesn't conflict)., Test initialization with Path object., Test handling empty target language. (+2 more)

### Community 86 - "reconcile_queries"
Cohesion: 0.27
Nodes (13): Any, reconcile_queries(), _ConfigProvider, Any, asyncio, MonkeyPatch, _RecordingStrategy, test_reconcile_queries_builds_properties_and_candidates() (+5 more)

### Community 87 - "Dimension Details SQL"
Cohesion: 0.14
Nodes (15): authority.data_type, authority.immutable_unaccent, Data Types Resource, Data Type Details SQL, Data Type Fuzzy Find SQL, tbl_data_type_groups, tbl_data_types, Dimension Alternate Identity SQL (+7 more)

### Community 88 - "test_translation_cache.py"
Cohesion: 0.17
Nodes (7): Comprehensive tests for TranslationCache., Test TranslationCache initialization., Test default cache directory is created., Test custom cache directory is created., Test initialization with existing directory., Test memory cache is initialized as empty dict., TestTranslationCacheInitialization

### Community 89 - "TestEnv2Dict"
Cohesion: 0.11
Nodes (12): Loader, SequenceNode, yaml_path_join(), yaml_str_join(), Tests for env2dict function., Test env2dict with simple environment variables., Test env2dict with existing data dictionary., Test env2dict when no environment variables match prefix. (+4 more)

### Community 90 - "public.tbl_locations"
Cohesion: 0.17
Nodes (13): public.tbl_location_types, public.tbl_locations, public.tbl_relative_age_types, public.tbl_relative_ages, public.tbl_activity_types, public.tbl_rdb, public.tbl_rdb_codes, public.tbl_rdb_systems (+5 more)

### Community 91 - ".as_candidate"
Cohesion: 0.25
Nodes (4): Return the ID field name for this entity type, Return the label field name for this entity type, Return the URL path segment for this entity type, Convert entity data to OpenRefine candidate format

### Community 92 - "TestExtCell"
Cohesion: 0.15
Nodes (7): Test ExtCell with str value., Test ExtCell accepts 'str' alias., Test ExtCell with all fields., Test ExtCell trims string values., Test ExtCell converts empty strings to None., Test ExtCell accepts 'type' alias., TestExtCell

### Community 93 - "public.tbl_analysis_values"
Cohesion: 0.25
Nodes (11): public.tbl_analysis_boolean_values, public.tbl_analysis_dating_ranges, public.tbl_analysis_identifiers, public.tbl_analysis_integer_ranges, public.tbl_analysis_integer_values, public.tbl_analysis_notes, public.tbl_analysis_numerical_ranges, public.tbl_analysis_numerical_values (+3 more)

### Community 94 - "public.tbl_dimensions"
Cohesion: 0.18
Nodes (12): public.tbl_analysis_value_dimensions, public.tbl_method_groups, public.tbl_coordinate_method_dimensions, public.tbl_dimensions, public.tbl_measured_value_dimensions, public.tbl_measured_values, public.tbl_sample_coordinates, public.tbl_sample_dimensions (+4 more)

### Community 95 - "SuggestPropertyItem"
Cohesion: 0.23
Nodes (9): SuggestPropertyItem, SuggestPropertyResponse, Test SuggestPropertyItem model., Test minimal property item., Test property item with description., Test SuggestPropertyResponse model., Test property response., TestSuggestPropertyItem (+1 more)

### Community 96 - "EntityPolicy"
Cohesion: 0.29
Nodes (3): EntityPolicy, Immutable policy snapshot for one entity type., TestEntityPolicyProperties

### Community 97 - "TestModelSerialization"
Cohesion: 0.17
Nodes (7): Test model serialization/deserialization., Test ReconQuery serialization round trip., Test ReconCandidate serialization round trip., Test ExtCell serialization preserves aliases., Test SuggestEntityResponse includes example in schema., Test ReconServiceManifest has proper config., TestModelSerialization

### Community 98 - "TestMCPResources"
Cohesion: 0.17
Nodes (7): Tests for MCPResources, Test get_server_info returns correct metadata, Test list_lookup_tables returns table metadata, Test get_lookup_rows returns paginated data, Test get_lookup_rows with invalid entity type, Test get_lookup_rows with language parameter raises NotImplementedError, TestMCPResources

### Community 99 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 100 - "SEAD Authority Service Main Configuration"
Cohesion: 0.22
Nodes (11): SEAD Authority Service Main Configuration, Location Entity, Location Type Entity, Modification Type Entity, Site Entity, LLM Prompt Templates, Docker Configuration Template, Docker Entity Table Specifications (+3 more)

### Community 101 - "FastAPI Application"
Cohesion: 0.20
Nodes (11): FastAPI Application, OpenRefine, Reconciliation Orchestrator, Reconciliation Router, SEAD Authority Service, Strategy Registry, main.py, Reconciliation Request Flow (+3 more)

### Community 102 - "public.tbl_abundances"
Cohesion: 0.18
Nodes (11): public.tbl_abundances, public.tbl_modification_types, public.tbl_record_types, public.tbl_taxa_tree_orders, public.tbl_abundance_elements, public.tbl_abundance_ident_levels, public.tbl_abundance_modifications, public.tbl_abundance_properties (+3 more)

### Community 103 - "ReconPropertyConstraint"
Cohesion: 0.23
Nodes (8): Property constraint in a query: property id + value., ReconPropertyConstraint, Test ReconPropertyConstraint model., Test creating a valid property constraint., Test property constraint with string value., Test property constraint with dict/object value., Test property constraint with list value., TestReconPropertyConstraint

### Community 104 - "TaxonReconciliationStrategy"
Cohesion: 0.24
Nodes (7): Any, BaseRepository, register, Future taxon reconciliation strategy, Fetch details for a specific taxon (placeholder)., TaxonReconciliationStrategy, TaxonRepository

### Community 105 - "authority.get_embedding_status"
Cohesion: 0.20
Nodes (8): authority.%1$I, pg_attribute, pg_class, pg_constraint, pg_namespace, pg_tables, s, authority.get_embedding_status()

### Community 106 - "SEAD Authority Service Docker Assets README"
Cohesion: 0.24
Nodes (10): Docker Build Script, Docker Compose Service Definition, Dockerfile, Docker Environment Template, SEAD Authority Service Docker Assets README, SEAD Authority Service GHCR Image, Build and Push Docker Image Workflow, Deployment Runtime Config Directory (+2 more)

### Community 107 - "BaseRepository"
Cohesion: 0.22
Nodes (10): Authority Views (authority.*), BaseRepository, ConfigValue, config.yml, entities.yml, get_connection(), prompts.yml, Schema Generation (+2 more)

### Community 108 - "PostgreSQL (SEAD Database)"
Cohesion: 0.24
Nodes (10): pg_trgm, pgvector, PostgreSQL (SEAD Database), Cache Config, Embeddings Config, Retrieval Config, Authority Schema Prep, Embedding Ingestion (+2 more)

### Community 109 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 110 - "SubConfigResolver"
Cohesion: 0.22
Nodes (6): Recursively resolve sub-configurations referenced in the main configuration. A…, SubConfigResolver, Test SubConfigResolver for @include directives., SubConfigResolver should resolve relative paths., SubConfigResolver should handle absolute paths., TestSubConfigResolver

### Community 111 - "TestAPIResponse"
Cohesion: 0.20
Nodes (6): Test APIResponse generic wrapper., Test successful API response with data., Test error API response., Test API response with complex data type., Test API response defaults to success=True., TestAPIResponse

### Community 112 - "TestEdgeCases"
Cohesion: 0.20
Nodes (6): Tests for edge cases and error conditions., Test handling of malformed list literal., Test handling of empty include path., Test string with plus operators but no lists or includes., Test that plus signs within list values don't break parsing., TestEdgeCases

### Community 113 - "test_utility_extended.py"
Cohesion: 0.17
Nodes (7): Extended tests for src.configuration.utility to improve coverage., Test the public replace_references function., Public function should use input data as full_data context., Should handle top-level list input., Should handle top-level string input., Integration test with multiple reference patterns., TestReplaceReferencesPublicAPI

### Community 114 - "TestJSONFormatter"
Cohesion: 0.12
Nodes (10): JSONFormatter, register, Test JSONFormatter functionality, Test formatting empty rows, Test formatting a single row, Test formatting multiple rows, Test formatting with complex data structures, Test handling of Unicode characters (+2 more)

### Community 115 - "ConfigValue"
Cohesion: 0.04
Nodes (40): argument, ConfigValue, Any, T, A value that can be resolved from a configuration store., Create a field for a dataclass that will be resolved at creation time., Resolve all ConfigValue fields in the dataclass., main() (+32 more)

### Community 116 - "SEAD Authority Service - AI Coding Instructions"
Cohesion: 0.67
Nodes (9): SEAD Authority Service - AI Coding Instructions, Design Docs Instructions, Development Docs Instructions, Mermaid Diagram Style Instructions, GitHub Workflow Instructions, Operations Docs Instructions, README Instructions, Testing Docs Instructions (+1 more)

### Community 117 - "SamplingContextReconciliationStrategy"
Cohesion: 0.33
Nodes (5): BaseRepository, register, StrategySpecification, Sampling Context-specific reconciliation with sampling context names and…, SamplingContextReconciliationStrategy

### Community 118 - "resolve_specification"
Cohesion: 0.25
Nodes (6): load_resource_yaml(), Loads a resource YAML file from the resources folder., Resolves a specification which can be either a dict or a resource key string., resolve_specification(), Tests for resource YAML helpers., TestResourceYaml

### Community 119 - "SEAD MCP Server (sead.pg)"
Cohesion: 0.29
Nodes (8): MCP Config, Hybrid RAG + MCP Flow, RAG vs MCP Comparison, MCP Server Phase, get_by_id Tool, SEAD MCP Server (sead.pg), RAG Pipeline (MCP-based), rerank Tool

### Community 120 - "public.tbl_value_classes"
Cohesion: 0.38
Nodes (7): public.tbl_analysis_categorical_values, public.tbl_data_type_groups, public.tbl_data_types, public.tbl_property_types, public.tbl_value_classes, public.tbl_value_type_items, public.tbl_value_types

### Community 121 - "Config"
Cohesion: 0.03
Nodes (57): BaseResolver, Config, is_config_path(), is_path_to_existing_file(), Any, Path, Save configuration to the YAML file. This method preserves the raw YAML…, Create a deep copy of the configuration. (+49 more)

### Community 122 - "Design"
Cohesion: 0.10
Nodes (20): 1. Resolve Identity, 2. Bind, 3. Associate with Change Request, 4. Detect Change (Update Foundation), Approach, Authority-key intake, Business-key intake, Concept-to-Structure Mapping (+12 more)

### Community 123 - "_replace_references"
Cohesion: 0.13
Nodes (13): Any, Helper function for replace_references, Recursively searches dict for values matching @value directives optionally with…, _replace_references(), Test _replace_references recursive resolution., Should recursively replace references in nested dicts., Should recursively replace references in lists., Should parse and resolve list expressions with operations. (+5 more)

### Community 124 - "configuration/test_utility.py"
Cohesion: 0.25
Nodes (7): Tests for src.configuration.utility helpers., List operations should concatenate literal lists and referenced lists., Invalid nested list expressions should be returned unchanged., @value directive should copy referenced data., test_replace_references_ignores_nested_list_expression(), test_replace_references_list_operations(), test_replace_references_simple_include()

### Community 125 - "test_llm_input_format.py"
Cohesion: 0.13
Nodes (14): FormatterRegistry, _has_non_scalar(), _is_scalar(), MarkdownFormatter, Any, Protocol, RowFormatter, _total_chars() (+6 more)

### Community 126 - "TestPreviewTemplate"
Cohesion: 0.14
Nodes (8): Test PreviewTemplate model., Test creating a valid preview template., Test preview template with custom dimensions., Test width must be > 0., Test width must be <= 1920., Test height must be > 0., Test height must be <= 1080., TestPreviewTemplate

### Community 127 - "check_imports.py"
Cohesion: 0.33
Nodes (5): Check Imports Pre-commit Hook, Ruff Pre-commit Hook, find_import_inconsistencies(), main(), Find files that import the same module using different paths.

### Community 128 - "LLM Config"
Cohesion: 0.29
Nodes (7): Abbreviation Prompt, Language Detection Prompt, Reconciliation Prompt, Translation Prompt, LLM Integration, LLM Providers (OpenAI, Anthropic, Ollama), LLM Config

### Community 129 - "RAGHybridReconciliationStrategy"
Cohesion: 0.29
Nodes (7): Embedded MCP Server, RAGHybridReconciliationStrategy, Per-Entity Policy, Observability & SLOs, RAGHybrid Strategy Implementation, Rollout Plan, search_lookup Tool

### Community 130 - "public.tbl_sites"
Cohesion: 0.25
Nodes (8): public.tbl_site_natgridrefs, public.tbl_site_preservation_status, public.tbl_site_properties, public.tbl_site_references, public.tbl_site_site_types, public.tbl_site_type_groups, public.tbl_site_types, public.tbl_sites

### Community 131 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 132 - "RuntimeError"
Cohesion: 0.20
Nodes (4): RuntimeError, Raised when a repository operation fails unexpectedly., RepositoryError, _SuggestStrategyBase

### Community 133 - "Proposal Document Structure Instructions"
Cohesion: 0.60
Nodes (6): Phase Plan Instructions, Proposal Document Structure Instructions, Proposal Writing Guide, Task Plan Instructions, Writing Style Instructions, Proposal and Planning Document Family

### Community 134 - "authority.location"
Cohesion: 0.40
Nodes (5): tbl_location_types, authority.fuzzy_location(), authority.location, public.tbl_location_types, public.tbl_locations

### Community 135 - "sead_identity.bindings"
Cohesion: 0.33
Nodes (5): sead_identity.bindings, sead_identity, sead_identity.source_identities, sead_identity.binding_sets, sead_identity.tracked_identities

### Community 136 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 137 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 142 - "TestDatabaseUtilities"
Cohesion: 0.20
Nodes (6): Tests for database utility functions., Test create_db_uri function., Test create_db_uri with string port., Test create_db_uri with custom driver., Test create_db_uri with password., TestDatabaseUtilities

### Community 144 - "Graphify Skill (Codex)"
Cohesion: 0.40
Nodes (5): Graphify Extraction Spec, Graphify Query Reference, Graphify Update Reference, Graphify Skill (Codex), Graphify Skill (Copilot)

### Community 145 - "graphify Knowledge Graph Pipeline"
Cohesion: 0.50
Nodes (5): graphify Reference: Commit Hook and CLAUDE.md Integration, graphify Reference: Query, Path, Explain, graphify Reference: Transcribe Video and Audio, graphify Reference: Incremental Update and Cluster-Only, graphify Knowledge Graph Pipeline

### Community 146 - "asyncio"
Cohesion: 0.11
Nodes (15): debug, asyncio, skip, Test that connection errors are properly handled with rollback. This test…, Tests specifically for DatabaseRepository transaction handling, Test that fetch_all properly handles errors and rolls back the transaction.…, Test that fetch_one properly handles errors and rolls back the transaction., Special test for debugging the transaction error with a debugger. To use this… (+7 more)

### Community 147 - "Identity Router"
Cohesion: 0.40
Nodes (5): IdentityPolicy, Identity Router, IdentityService, Identity Tables, Shape Shifter

### Community 148 - "ReconciliationStrategy"
Cohesion: 0.40
Nodes (5): MethodReconciliationStrategy, ReconciliationStrategy, SiteReconciliationStrategy, SiteRepository, TaxonReconciliationStrategy

### Community 149 - "authority.taxa_synonym"
Cohesion: 0.50
Nodes (4): authority.fuzzy_taxa_synonym(), authority.taxa_synonym, public.tbl_taxa_synonyms, public.tbl_taxa_tree_master

### Community 150 - "authority.taxa_tree_family"
Cohesion: 0.50
Nodes (4): authority.fuzzy_taxa_tree_family(), authority.taxa_tree_family, public.tbl_taxa_tree_families, public.tbl_taxa_tree_orders

### Community 151 - "authority.taxa_tree_genus"
Cohesion: 0.50
Nodes (4): authority.fuzzy_taxa_tree_genus(), authority.taxa_tree_genus, public.tbl_taxa_tree_families, public.tbl_taxa_tree_genera

### Community 152 - "authority.taxa_tree_master"
Cohesion: 0.50
Nodes (4): authority.fuzzy_taxa_tree_master(), authority.taxa_tree_master, public.tbl_taxa_tree_genera, public.tbl_taxa_tree_master

### Community 153 - "authority.taxa_tree_order"
Cohesion: 0.50
Nodes (4): authority.fuzzy_taxa_tree_order(), authority.taxa_tree_order, public.tbl_record_types, public.tbl_taxa_tree_orders

### Community 155 - "fix_imports_in_file"
Cohesion: 0.60
Nodes (4): fix_imports_in_file(), main(), Path, Fix imports in a single file.

### Community 156 - "Countries Resource"
Cohesion: 0.40
Nodes (5): authority.fuzzy_location, authority.location, Countries Resource, Country Details SQL, Country Fuzzy Find SQL

### Community 157 - "test_config_extended.py"
Cohesion: 0.22
Nodes (6): Ignore unknown tags silently, SafeLoaderIgnoreUnknown, Extended tests for src.configuration.config module to improve coverage., Test Config.clone method., Clone should create independent copy of config data., TestConfigClone

### Community 158 - "LLM Configuration"
Cohesion: 0.40
Nodes (5): LLM Configuration, Abbreviation Expansion Prompt, Language Detection Prompt, Reconciliation Prompt, Translation Prompt

### Community 159 - "Any"
Cohesion: 0.22
Nodes (5): Any, Perform fuzzy name search, Perform (possibly) fuzzy name search, Fetch details for a specific entity by ID, Fetch entity by alternate identity

### Community 160 - "SIMS Identity Module"
Cohesion: 0.28
Nodes (7): SIMS Operations Doc, SIMS Entity Register, SIMS Identity Module, IdentityPolicy, policy.py, repository.py, types.py

### Community 161 - "TestConfigStoreClassMethods"
Cohesion: 0.25
Nodes (5): Check if configuration is available (uses provider layer), Test ConfigStore class methods for backward compatibility., is_configured_global should use provider layer., config_global should use provider layer., TestConfigStoreClassMethods

### Community 162 - "authority.bibliographic_reference"
Cohesion: 0.67
Nodes (3): authority.bibliographic_reference, authority.fuzzy_bibliographic_reference(), public.tbl_biblio

### Community 163 - "authority.data_type"
Cohesion: 0.67
Nodes (3): authority.data_type, authority.fuzzy_data_type(), public.tbl_data_types

### Community 164 - "authority.data_type_group"
Cohesion: 0.67
Nodes (3): authority.data_type_group, authority.fuzzy_data_type_group(), public.tbl_data_type_groups

### Community 165 - "authority.dating_uncertainty"
Cohesion: 0.67
Nodes (3): authority.dating_uncertainty, authority.fuzzy_dating_uncertainty(), public.tbl_dating_uncertainty

### Community 166 - "authority.feature"
Cohesion: 0.67
Nodes (3): authority.feature, authority.fuzzy_feature(), public.tbl_features

### Community 167 - "authority.feature_type"
Cohesion: 0.67
Nodes (3): authority.feature_type, authority.fuzzy_feature_type(), public.tbl_feature_types

### Community 168 - "authority.location_type"
Cohesion: 0.67
Nodes (3): authority.fuzzy_location_type(), authority.location_type, public.tbl_location_types

### Community 169 - "authority.method"
Cohesion: 0.67
Nodes (3): authority.fuzzy_method(), authority.method, public.tbl_methods

### Community 170 - "authority.method_group"
Cohesion: 0.67
Nodes (3): authority.fuzzy_method_group(), authority.method_group, public.tbl_method_groups

### Community 171 - "authority.modification_type"
Cohesion: 0.67
Nodes (3): authority.fuzzy_modification_type(), authority.modification_type, public.tbl_modification_types

### Community 172 - "authority.record_type"
Cohesion: 0.67
Nodes (3): authority.fuzzy_record_type(), authority.record_type, public.tbl_record_types

### Community 173 - "authority.relative_age"
Cohesion: 0.67
Nodes (3): authority.fuzzy_relative_age(), authority.relative_age, public.tbl_relative_ages

### Community 174 - "authority.relative_age_type"
Cohesion: 0.67
Nodes (3): authority.fuzzy_relative_age_type(), authority.relative_age_type, public.tbl_relative_age_types

### Community 175 - "authority.sample_description_type"
Cohesion: 0.67
Nodes (3): authority.fuzzy_sample_description_type(), authority.sample_description_type, public.tbl_sample_description_types

### Community 176 - "authority.sample_group_description_type"
Cohesion: 0.67
Nodes (3): authority.fuzzy_sample_group_description_type(), authority.sample_group_description_type, public.tbl_sample_group_description_types

### Community 177 - "authority.sample_location_type"
Cohesion: 0.67
Nodes (3): authority.fuzzy_sample_location_type(), authority.sample_location_type, public.tbl_sample_location_types

### Community 178 - "authority.sample_type"
Cohesion: 0.67
Nodes (3): authority.fuzzy_sample_type(), authority.sample_type, public.tbl_sample_types

### Community 179 - "authority.sampling_context"
Cohesion: 0.67
Nodes (3): authority.fuzzy_sampling_context(), authority.sampling_context, public.tbl_sample_group_sampling_contexts

### Community 180 - "authority.taxa_tree_author"
Cohesion: 0.67
Nodes (3): authority.fuzzy_taxa_tree_author(), authority.taxa_tree_author, public.tbl_taxa_tree_authors

### Community 181 - "authority.taxonomic_order_system"
Cohesion: 0.67
Nodes (3): authority.fuzzy_taxonomic_order_system(), authority.taxonomic_order_system, public.tbl_taxonomic_order_systems

### Community 182 - "authority.taxonomy_note"
Cohesion: 0.67
Nodes (3): authority.fuzzy_taxonomy_note(), authority.taxonomy_note, public.tbl_taxonomy_notes

### Community 183 - "sead_identity.source_identity_keys"
Cohesion: 0.50
Nodes (3): sead_identity.source_identity_keys, sead_identity, sead_identity.source_identities

### Community 184 - "sead_identity.submission_source_identities"
Cohesion: 0.50
Nodes (3): sead_identity.submission_source_identities, sead_identity.source_identities, sead_identity.submissions

### Community 185 - "Path"
Cohesion: 0.13
Nodes (8): Path, Test loading TSV (tab-separated) data using @load: notation, Test loading CSV with explicit comma delimiter option, Test that @load with options dict but no filename returns directive argument, Test loading CSV with relative path (relative to config file), Test loading sub-config with absolute path, Test that circular references are handled (Python recursion limit will catch…, Test loading a simple sub-config referenced with @include: notation

### Community 186 - "authority.feature_type"
Cohesion: 0.67
Nodes (4): authority.feature_type, Feature Type Details SQL, Feature Types Resource, Feature Type Fuzzy Find SQL

### Community 187 - "Core Concepts"
Cohesion: 0.20
Nodes (10): Binding, Binding Set, Change Request, Core Concepts, Identity Resolution, Materialization, Source Identity, Source Scope (+2 more)

### Community 188 - "ChangeDetectionResult"
Cohesion: 0.36
Nodes (4): ChangeDetectionResult, Output of the Detect Change operation., Compare an incoming content hash against the stored hash for a Tracked…, TestChangeDetection

### Community 191 - "site_location (Bridge)"
Cohesion: 0.67
Nodes (3): location (Shared Metadata), site (Shared Metadata), site_location (Bridge)

### Community 192 - "create_connection_mock"
Cohesion: 0.40
Nodes (4): create_connection_mock(), Any, Create an async psycopg connection mock whose cursor methods return given…, Create a mock connection pool that returns mock connections

### Community 198 - ".test_get_entity_id_field"
Cohesion: 0.40
Nodes (3): parametrize, Test getting entity ID field name., Test get_property_settings method returns location-specific settings.

### Community 199 - "TestYAMLHelpers"
Cohesion: 0.25
Nodes (5): Test YAML custom constructors and utility functions., Test !join constructor joins sequence elements into string., Test !path_join and !jj constructors join paths correctly., Test is_path_to_existing_file with various invalid inputs., TestYAMLHelpers

### Community 200 - "Test Configuration"
Cohesion: 0.67
Nodes (3): Test Configuration, Entity Definitions, LLM Prompt Templates

### Community 201 - "TestSafeLoaderIgnoreUnknown"
Cohesion: 0.25
Nodes (5): Test custom YAML loader that ignores unknown tags., Test loader handles unknown scalar tags gracefully., Test loader handles unknown sequence tags., Test loader handles unknown mapping tags., TestSafeLoaderIgnoreUnknown

### Community 209 - "TestMultipleRepository"
Cohesion: 0.21
Nodes (8): parametrize, Test getting details with invalid ID., Test getting details when not found., Tests for common logic in various Repository classes., Test fuzzy name search., Test fuzzy name search with default limit., Test getting details with valid ID., TestMultipleRepository

### Community 211 - "SIMS Diagrams"
Cohesion: 0.22
Nodes (9): 1. Submission Setup, 2. Provider-Owned Entity — First Submission (New Identity), 3. Provider-Owned Entity — Re-Submission (Matched Identity), 4. Shared Metadata Entity — Allocation Blocked, 5. Manual Confirmation and Change Request Association, 6. Change Detection, 7. Binding Set State Machine, 8. Tracked Identity State Machine (+1 more)

### Community 212 - ".fetch_all"
Cohesion: 0.38
Nodes (4): DictRow, Params, Fetch entity by alternate identity, TupleRow

### Community 213 - "TestViewTemplate"
Cohesion: 0.33
Nodes (4): Test ViewTemplate model., Test creating a valid view template., Test view template with multiple parameters., TestViewTemplate

### Community 249 - "SIMS — SEAD Identity Management System"
Cohesion: 0.22
Nodes (9): Archived (historical), Boundary to Shape Shifter, Current Status, Documentation Map, Reference Material, SIMS — SEAD Identity Management System, Source of Truth, System reference (+1 more)

### Community 250 - "TypeRef"
Cohesion: 0.29
Nodes (6): TypeRef, Test creating a valid TypeRef., Test TypeRef JSON serialization., Test TypeRef requires both id and name., Test TypeRef accepts empty strings., TestTypeRef

### Community 251 - "TestSuggestSubservice"
Cohesion: 0.33
Nodes (4): Test SuggestSubservice model., Test minimal suggest subservice., Test suggest subservice with flyout., TestSuggestSubservice

### Community 252 - "TestConfigSaveErrors"
Cohesion: 0.33
Nodes (4): Test Config.save error handling., Save should raise ValueError if no filename is set., Save without updates should log warning about losing directives., TestConfigSaveErrors

### Community 253 - "Storage Design"
Cohesion: 0.22
Nodes (9): Binding Sets, Bindings, Change Request References, Source Identities, Source Scopes, Storage Design, Submission–Source Identity Junction, Submissions (+1 more)

### Community 254 - "TestConfigResolveReferences"
Cohesion: 0.33
Nodes (4): Test Config.resolve_references static method., resolve_references should not mutate input when inplace=False., resolve_references with inplace=True modifies original dict., TestConfigResolveReferences

### Community 255 - "Requirements Docs"
Cohesion: 0.25
Nodes (7): Purpose, Requirements Docs, Scope boundaries, Size expectations, Sources to trust, What belongs, Writing rules

### Community 256 - "Constraints"
Cohesion: 0.40
Nodes (5): Binding constraints, Binding Set constraints, Constraints, Identity constraints, Process constraints

### Community 257 - "SIMS target_id Contract Proposal"
Cohesion: 0.52
Nodes (7): Proposal Backlog, SIMS target_id Contract Proposal, target_id Contract Issue Draft, target_id Contract PR Draft, ResolutionOutcome, target_id Field, Shape Shifter sead_change_request

### Community 258 - "Canonical Use Cases"
Cohesion: 0.33
Nodes (6): 1. Reuse a confirmed binding for a known source identity, 2. Match a new source identity to an existing tracked identity, 3. Allocate a new tracked identity for an unmatched source identity, 4. Correct a confirmed binding, 5. Invalidate a tracked identity after a rejected change request, Canonical Use Cases

### Community 262 - "test_provider"
Cohesion: 0.40
Nodes (5): fixture, Provide TestConfigProvider with test configuration, Configure logging for all tests with DEBUG level., setup_test_logging(), test_provider()

### Community 263 - "OpenAIProvider"
Cohesion: 0.33
Nodes (3): OpenAIProvider, Any, register

### Community 264 - "TestBaseResolver"
Cohesion: 0.50
Nodes (3): Test BaseResolver abstract functionality., BaseResolver should recursively process nested dicts and lists., TestBaseResolver

### Community 265 - ".test_whoami_returns_host_and_port"
Cohesion: 0.40
Nodes (4): skip, Test whoami endpoint for service discovery., Test whoami endpoint returns host and port information., TestWhoAmIEndpoint

### Community 267 - "configuration/provider.py"
Cohesion: 0.04
Nodes (77): shutdown(), startup(), on_event, ConfigProvider, get_config_provider(), ABC, Abstract configuration provider for dependency injection, Check if configuration exists for the given context (+69 more)

## Ambiguous Edges - Review These
- `SEAD Authority Service - AI Coding Instructions` → `Design Docs Instructions`  [AMBIGUOUS]
  .github/instructions/design.instructions.md · relation: references
- `SEAD Authority Service - AI Coding Instructions` → `Development Docs Instructions`  [AMBIGUOUS]
  .github/instructions/development.instructions.md · relation: references
- `SEAD Authority Service - AI Coding Instructions` → `Operations Docs Instructions`  [AMBIGUOUS]
  .github/instructions/operations.instructions.md · relation: references
- `SEAD Authority Service - AI Coding Instructions` → `README Instructions`  [AMBIGUOUS]
  .github/instructions/readme.instructions.md · relation: references
- `SEAD Authority Service - AI Coding Instructions` → `Testing Docs Instructions`  [AMBIGUOUS]
  .github/instructions/testing.instructions.md · relation: references
- `SEAD Authority Service` → `Release Workflow`  [AMBIGUOUS]
  .github/workflows/release.yml · relation: references
- `Method Entity` → `Taxa Order Entity`  [AMBIGUOUS]
  tests/config/entities.yml · relation: conceptually_related_to

## Knowledge Gaps
- **404 isolated node(s):** `tbl_abundances`, `tbl_abundance_elements`, `tbl_abundance_ident_levels`, `tbl_abundance_modifications`, `tbl_activity_types` (+399 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **37 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `SEAD Authority Service - AI Coding Instructions` and `Design Docs Instructions`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `SEAD Authority Service - AI Coding Instructions` and `Development Docs Instructions`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `SEAD Authority Service - AI Coding Instructions` and `Operations Docs Instructions`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `SEAD Authority Service - AI Coding Instructions` and `README Instructions`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `SEAD Authority Service - AI Coding Instructions` and `Testing Docs Instructions`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `SEAD Authority Service` and `Release Workflow`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `Method Entity` and `Taxa Order Entity`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._