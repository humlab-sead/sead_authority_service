# Graph Report - sead_authority_service  (2026-10-29)

## Corpus Check
- 286 files · ~210,074 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 17 file(s) not represented in the graph (top: (none) 9, .example 2, .service 2)

## Summary
- 6744 nodes · 13009 edges · 389 communities (297 shown, 92 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 1163 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8e3656b2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- 01_tables.sql
- router.py
- SEAD Identity System Requirements
- BaseRepository
- TestClient
- ExtendedMockConfigProvider
- IdentityService
- MockConfigProvider
- GeoNamesProxy
- TestDotNotationUtilities
- test_router.py
- test_suggest.py
- _patch_connection
- with_test_config
- IdentityPolicy
- FeatureTypeReconciliationStrategy
- ResolveBatchResult
- LLMProvider
- ResolutionRequest
- LLMModificationTypeReconciliationStrategy
- ReconQuery
- _make_service
- SuggestSubservice
- Proposal: SIMS Identity Capability Contract
- .load
- TestListOperations
- _make_service_mock
- _parse_list_expression
- SEADMCPServer
- .fetch_all
- BaseRepository
- .get_config
- render_preview
- BindingSet
- TestReplaceReferences
- MCPTools
- SEAD MCP Server - Embedded Implementation
- test_provider_extended.py
- test_mcp.py
- TranslationService
- public.tbl_datasets
- __deploy__.sql
- AbstractRepository
- Path
- ReconCandidate
- replace_env_vars
- TestMCPModels
- ExtendRequestProperty
- Proposal: SIMS `target_id` Contract For Delivery 1
- TestJSONFormatter
- public.tbl_sample_group_sampling_contexts
- TestUtilityFunctions
- SuggestEntityResponse
- TranslationCache
- format_rows_for_llm
- LLMReconciliationStrategy
- GeoNamesRepository
- strategies/test_strategy.py
- ConfigFactory
- public.tbl_taxa_tree_master
- test_router_extended.py
- Phase 1 Task Plan: Prepare the Podman Deployment Bundle
- site
- TestRegistry
- EmbeddingPopulator
- main
- ReconBatchRequest
- asyncio
- llm
- method
- TestMCPConfig
- test_llm_input_format.py
- foreign_key_column
- create_schema.sh
- PropertySetting
- Provider-Supplied Shared Metadata Entries
- TestCSVFormatter
- test_config_extended.py
- ._make_repo
- TestTranslationCacheGet
- SIMS Conceptual Model and Systems Design
- SIMS_TARGET_ID_CONTRACT.md
- location
- modification_type
- TestTranslationCacheIntegration
- OpenAIProvider
- reconcile_queries
- Dimension Details SQL
- test_translation_cache.py
- TestStrategyRegistry
- public.tbl_locations
- sql_queries
- TestExtCell
- llm
- public.tbl_methods
- test_model.py
- recursive_filter_dict
- TestModelSerialization
- MCPResources
- taxa_tree_master
- env2dict
- FastAPI Application
- taxa_tree_family
- ReconPropertyConstraint
- .test_find_candidates_with_llm_success
- authority.get_embedding_status
- BibliographicReferenceReconciliationStrategy
- RAGHybridReconciliationStrategy
- retrieval
- analyze
- Review a GitHub pull request
- TestAPIResponse
- TestEdgeCases
- TestReplaceReferencesPublicAPI
- service.py
- Proposal: Move Authority Service Deployment from Docker to Podman
- SEAD Authority Service - AI Coding Instructions
- Phase 2 Task Plan: First Deployment to the Target Host
- Entity Register
- SEAD MCP Server (sead.pg)
- public.view_typed_analysis_values
- src/configuration/__init__.py
- Design
- TestReplaceReferences
- configuration/test_utility.py
- normalize_text
- DummyRegistry
- taxa_tree_order
- Podman Deployment Migration Phase Plan
- config-template.yml
- analyze
- git_commit
- json
- Proposal Document Structure Instructions
- analyze
- AGENTS.md - AI Coding Agent Instructions
- location
- foreign_key_column
- location
- test_llm_input_format.py
- BaseModel
- ConfigValue
- SEAD Authority Service — Rootless Podman Deployment
- Implementation Phases
- metadata.py
- data_type
- .create_connection_mock
- feature_type
- method_rag.yml
- public.tbl_taxa_tree_genera
- public.tbl_sample_description_types
- dimension.yml
- __init__
- public.tbl_record_types
- utility.sql
- options
- Countries Resource
- container/config/entities.yml
- llm
- tests/config/entities.yml
- SIMS Identity Module
- sead-authority-service
- location.yml
- public.tbl_data_types
- StrategyRegistry
- public.tbl_relative_ages
- public.tbl_features
- modification_type
- modification_type
- config/config.yml
- mcp
- public.tbl_modification_types
- mcp
- create_db_uri
- database
- mcp
- foreign_key_column
- strategies/__init__.py
- public.tbl_sample_types
- llm
- DimensionReconciliationStrategy
- 06_indexes.sql
- handlers
- taxa_synonym
- taxa_tree_genus
- mcp
- authority.feature_type
- Core Concepts
- Any
- .test_is_registered_true
- openai
- .test_fetch_all_with_error_and_rollback
- bibliographic_reference
- sead_identity.bindings
- method
- modification_type
- record_type
- site
- taxa_tree_author
- ConfigStore
- tests/config/config.yml
- .test_registered_strategy_has_key_property
- config/entities.yml
- taxa_tree_family
- taxa_tree_master
- test-ci.sh
- taxa_tree_order
- sampling_context.yml
- Storage Design
- taxonomic_order_system
- EntityPolicy
- CHANGELOG.md - Version History
- taxonomy_note
- with
- authority-service
- TypeRef
- GeoNames Places Resource
- Taxon Resource (Empty)
- SIMS — SEAD Identity Management System
- data_type.yml
- Create a Phase Task Plan
- feature_type.yml
- Create a Proposal
- Implement a Phase Task Plan
- Requirements Docs
- Review the AI coding model strategy
- IdentityService
- Create a Phase Plan
- anthropic
- taxa_synonym
- Create a Phase Task Plan
- .__init__
- taxa_tree_family
- taxa_tree_genus
- taxa_tree_master
- taxa_tree_order
- MockConfigProvider
- Create a Proposal
- Implement a Phase Task Plan
- options
- Create a Phase Plan
- Move a Proposal
- Review a Proposal
- Clarify Technical Docs
- build.sh
- handlers
- Clarify Technical Docs
- taxonomy_note
- container/config/config.yml
- check_relative_links.sh
- Work Breakdown
- policy
- 011_resolve_batch_idempotency.sql
- Python Architecture Instructions
- data_type
- steps
- Functional Requirements
- Config
- config_fixtures.py
- TestConfigFactoryEdgeCases
- Domain Concepts
- administrative_region.yml
- country.yml
- policy
- bibliographic_reference
- data_type
- feature_type
- method
- modification_type
- record_type
- site
- taxa_tree_author
- taxonomic_order_system
- taxonomy_note
- seed_identity_scopes.py
- defaults
- database
- options
- cache
- geonames.yml
- options
- handlers
- sample_description_type
- config/entities.yml
- sample_type
- sampling_context
- ollama
- dating_uncertainty
- method_group
- relative_age_type
- sample_description_type
- sample_group_description_type
- sample_location_type
- sample_type
- sampling_context
- embeddings
- ollama
- site
- steps
- foreign_key_column
- ollama
- table_specs
- location_type
- method_group
- relative_age
- relative_age_type
- sample_description_type
- sample_group_description_type
- sample_location_type
- sample_type
- allocate_new
- bind_existing
- options
- handlers
- env
- build-and-push
- permissions
- target_environment
- data_type
- data_type_group
- dating_uncertainty
- feature
- feature_type
- location
- location_type
- method
- method_group
- modification_type
- record_type
- relative_age
- relative_age_type
- sample_group_description_type
- sample_location_type
- sample_type
- sampling_context
- site
- interface
- interface
- data_type
- dataset
- feature_type
- method
- sample
- sample_dimension
- sample_group
- site
- submission
- taxa_tree_master
- unit
- build.yml
- DataTypeReconciliationStrategy
- prompts
- test_config
- FakeSiteStrategy
- FakeTaxonStrategy
- _StubConfigValue
- .test_get_registered_strategy
- .test_registry_items_isolated

## God Nodes (most connected - your core abstractions)
1. `with_test_config()` - 312 edges
2. `MockConfigProvider` - 197 edges
3. `ExtendedMockConfigProvider` - 153 edges
4. `Config` - 117 edges
5. `ConfigValue` - 91 edges
6. `ConfigFactory` - 77 edges
7. `BaseRepository` - 74 edges
8. `IdentityPolicy` - 70 edges
9. `IdentityService` - 65 edges
10. `replace_references()` - 60 edges

## Surprising Connections (you probably didn't know these)
- `8. Tracked Identity State Machine` --references--> `TrackedIdentity`  [INFERRED]
  docs/SIMS/DIAGRAMS.md → src/identity/models.py
- `7. Binding Set State Machine` --references--> `BindingSet`  [INFERRED]
  docs/SIMS/DIAGRAMS.md → src/identity/models.py
- `API change` --references--> `ResolutionOutcome`  [INFERRED]
  docs/proposals/SIMS_TARGET_ID_CONTRACT/SIMS_TARGET_ID_CONTRACT.md → src/identity/models.py
- `Files` --references--> `ResolutionOutcome`  [INFERRED]
  docs/proposals/SIMS_TARGET_ID_CONTRACT/SIMS_TARGET_ID_CONTRACT_ISSUE.md → src/identity/models.py
- `Solution` --references--> `ResolutionOutcome`  [INFERRED]
  docs/proposals/SIMS_TARGET_ID_CONTRACT/SIMS_TARGET_ID_CONTRACT_ISSUE.md → src/identity/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Proposal and Planning Document Family** — _github_instructions_proposal_writing_guide_instructions, _github_instructions_proposal_document_structure_instructions, _github_instructions_phase_plan_instructions, _github_instructions_task_plan_instructions, concept_proposal_planning_docs [EXTRACTED 0.85]
- **Multilingual Reconciliation Pipeline Prompts** — tests_config_prompts_language_detection, tests_config_prompts_translation, tests_config_prompts_abbreviation, tests_config_prompts_reconciliation [EXTRACTED 0.90]
- **Resource Definition Pattern (key, id_field, label_field, sql_queries)** — src_resources_location, src_resources_method, src_resources_sampling_context, src_resources_site [EXTRACTED 0.90]
- **SEAD Documentation Scope Boundaries** — _github_instructions_design_instructions, _github_instructions_development_instructions, _github_instructions_operations_instructions, _github_instructions_testing_instructions, _github_instructions_readme_instructions, concept_docs_scope_boundaries [EXTRACTED 0.90]
- **SEAD Authority Service Main Configuration** — config_config, config_entities, config_prompts, config_identity_policy [EXTRACTED 0.95]
- **MCP Server API Surface** — docs_mcp_server_sead_reconciliation_via_mcp_architecture_doc_outline_mcp_server, docs_mcp_server_sead_reconciliation_via_mcp_architecture_doc_outline_search_lookup, docs_mcp_server_sead_reconciliation_via_mcp_architecture_doc_outline_rerank, docs_mcp_server_sead_reconciliation_via_mcp_architecture_doc_outline_get_by_id [EXTRACTED 0.95]
- **Reconciliation Request Flow Participants** — docs_design_openrefine, docs_design_reconciliation_router, docs_design_reconciliation_orchestrator, docs_design_strategy_registry, docs_design_base_repository, docs_design_postgresql [EXTRACTED 0.95]
- **Taxonomic Classification Hierarchy** — config_entities_taxa_tree_master, config_entities_taxa_tree_genus, config_entities_taxa_tree_family, config_entities_taxa_tree_order, config_entities_taxa_synonym, config_entities_record_type [EXTRACTED 0.95]
- **Taxonomic Hierarchy (Order → Family → Genus → Species)** — config_entities_taxa_tree_order, config_entities_taxa_tree_family, config_entities_taxa_tree_genus, config_entities_taxa_tree_master [EXTRACTED 0.95]
- **Reconciliation Request Flow** — src_api_router, src_reconcile, src_strategies_strategy, agents_strategy_registry_pattern [EXTRACTED 1.00]
- **SIMS Identity Module Components** — src_identity, src_api_identity_router, agents_sims_identity_module, docs_sims [EXTRACTED 1.00]
- **Details SQL Queries** — src_resources_country_details_sql, src_resources_data_type_details_sql, src_resources_dimension_details_sql, src_resources_feature_type_details_sql [INFERRED 0.75]
- **Fuzzy Search SQL Queries** — src_resources_country_fuzzy_find_sql, src_resources_data_type_fuzzy_find_sql, src_resources_dimension_fuzzy_find_sql, src_resources_feature_type_fuzzy_find_sql [INFERRED 0.75]
- **Resource Definitions** — src_resources_country_country, src_resources_data_type_data_type, src_resources_dimension_dimension, src_resources_feature_type_feature_type, src_resources_geonames_geonames [INFERRED 0.80]

## Communities (389 total, 92 thin omitted)

### Community 0 - "01_tables.sql"
Cohesion: 0.01
Nodes (136): tbl_abundance_elements, tbl_abundance_ident_levels, tbl_abundance_modifications, tbl_abundance_properties, tbl_abundances, tbl_activity_types, tbl_age_types, tbl_alt_ref_types (+128 more)

### Community 1 - "router.py"
Cohesion: 0.11
Nodes (11): flyout_entity(), is_alive(), meta(), preview(), reconcile(), suggest_entity(), suggest_properties(), suggest_property() (+3 more)

### Community 2 - "SEAD Identity System Requirements"
Cohesion: 0.12
Nodes (17): API non-goals at this stage, API-visible concepts, Goals, High Level API Behaviour, Out Of Scope For This Document, Problem boundaries, Problem Statement, Purpose (+9 more)

### Community 3 - "BaseRepository"
Cohesion: 0.11
Nodes (9): DataTypeRepository, DimensionRepository, FeatureTypeRepository, LocationRepository, MethodRepository, BaseRepository, RAGHybridReconciliationStrategy, ReconciliationStrategy (+1 more)

### Community 4 - "TestClient"
Cohesion: 0.05
Nodes (10): TestFlyoutEntityEndpoint, TestReconcileEndpointExtended, TestResponseModels, TestSuggestEntityEndpoint, TestSuggestPropertyEndpoint, TestSuggestTypeEndpoint, with_test_config(), async_wrapper() (+2 more)

### Community 5 - "ExtendedMockConfigProvider"
Cohesion: 0.04
Nodes (11): AdministrativeRegionReconciliationStrategy, CountryReconciliationStrategy, LocationReconciliationStrategy, ExtendedMockConfigProvider, TestAdministrativeRegionBasics, TestAdministrativeRegionDistinctionFromCountry, TestAdministrativeRegionEdgeCases, TestAdministrativeRegionIntegration (+3 more)

### Community 6 - "IdentityService"
Cohesion: 0.06
Nodes (26): associate_change_request(), AssociateChangeRequestBody, CapabilitiesResponse, confirm_binding_set(), detect_change(), EntityCapabilityResponse, get_binding_set(), get_capabilities() (+18 more)

### Community 7 - "MockConfigProvider"
Cohesion: 0.05
Nodes (3): GeoNamesReconciliationStrategy, TestGeoNamesEdgeCases, TestGeoNamesReconciliationStrategy

### Community 8 - "GeoNamesProxy"
Cohesion: 0.05
Nodes (5): GeoNamesProxy, NotSupportedError, TestGeoNamesProxy, TestGeoNamesProxyEdgeCases, TestGeoNamesProxyIntegration

### Community 9 - "TestDotNotationUtilities"
Cohesion: 0.03
Nodes (14): configure_logging(), dget(), dotexists(), dotexpand(), dotget(), dotset(), import_sub_modules(), load_resource_yaml() (+6 more)

### Community 10 - "test_router.py"
Cohesion: 0.05
Nodes (9): app(), client(), MockStrategies, MockStrategy, TestEndpointIntegration, TestErrorHandling, TestHealthCheck, TestMetaEndpoint (+1 more)

### Community 11 - "test_suggest.py"
Cohesion: 0.06
Nodes (31): render_flyout_preview(), suggest_entities(), suggest_properties(), suggest_types(), mock_results(), _SuggestStrategyBase, test_app(), test_flyout_entity_invalid_id() (+23 more)

### Community 12 - "_patch_connection"
Cohesion: 0.11
Nodes (14): BindingRepository, SourceScopeRepository, SubmissionRepository, TrackedIdentityRepository, _fake_get_connection(), _make_conn(), _make_cursor(), _patch_connection() (+6 more)

### Community 13 - "with_test_config"
Cohesion: 0.06
Nodes (4): SiteReconciliationStrategy, TestSiteReconciliationStrategy, TestSiteStrategyEdgeCases, TestSiteStrategyIntegration

### Community 14 - "IdentityPolicy"
Cohesion: 0.05
Nodes (22): get_config_dep(), EntityCapability, IdentityPolicy, _resolve_policy_path(), _make_client(), test_capability_endpoint_returns_versioned_list(), test_real_policy_exposes_expected_capabilities(), test_unconfigured_entity_is_absent_from_capabilities() (+14 more)

### Community 15 - "FeatureTypeReconciliationStrategy"
Cohesion: 0.05
Nodes (4): FeatureTypeReconciliationStrategy, create_connection_mock(), MockRow, TestFeatureTypeReconciliationStrategy

### Community 16 - "ResolveBatchResult"
Cohesion: 0.10
Nodes (8): ResolveBatchRecord, ResolveBatchResult, ResolveBatchRepository, IdentityBatchConflict, _request_fingerprint(), TestResolveBatchRepository, TestResolveBatch, no_database_transaction()

### Community 18 - "ResolutionRequest"
Cohesion: 0.06
Nodes (20): get_connection(), ChangeDetectionRequest, IdentitySignal, ResolutionRequest, TestResolutionRequest, _disposable_service(), _managed_entity_request(), _sample_request() (+12 more)

### Community 19 - "LLMModificationTypeReconciliationStrategy"
Cohesion: 0.10
Nodes (3): LLMModificationTypeReconciliationStrategy, ModificationTypeRepository, TestModificationTypeReconciliationStrategy

### Community 21 - "_make_service"
Cohesion: 0.08
Nodes (26): Files, Issue Draft: Add `ResolutionOutcome.target_id` to `POST /identity/resolve`, Problem, Solution, Files, PR Draft: Add `ResolutionOutcome.target_id` to `POST /identity/resolve`, Problem, Solution (+18 more)

### Community 22 - "SuggestSubservice"
Cohesion: 0.09
Nodes (9): APIResponse, ReconServiceManifest, SuggestDescriptor, SuggestSubservice, ViewTemplate, TestReconServiceManifest, TestSuggestDescriptor, TestSuggestSubservice (+1 more)

### Community 23 - "Proposal: SIMS Identity Capability Contract"
Cohesion: 0.11
Nodes (18): Acceptance Criteria, Capability discovery, Confirmation behavior, Entity configuration, Final Recommendation, Identity-value result, Non-Goals, Problem (+10 more)

### Community 26 - "_make_service_mock"
Cohesion: 0.10
Nodes (10): _make_client(), _make_policy_mock(), _make_service_mock(), TestAssociateChangeRequest, TestConfirmBindingSet, TestDetectChange, TestGetBindingSet, TestListScopes (+2 more)

### Community 27 - "_parse_list_expression"
Cohesion: 0.08
Nodes (3): _parse_list_expression(), _replace_references(), TestParseListExpression

### Community 28 - "SEADMCPServer"
Cohesion: 0.08
Nodes (4): GetByIdParams, SEADMCPServer, test_search_lookup_integration(), TestMCPServer

### Community 29 - ".fetch_all"
Cohesion: 0.17
Nodes (4): BibliographicReferenceRepository, DictRow, Params, TupleRow

### Community 31 - ".get_config"
Cohesion: 0.09
Nodes (3): OllamaProvider, ResponseModel, TestOllamaProvider

### Community 32 - "render_preview"
Cohesion: 0.09
Nodes (3): render_preview(), mock_strategy_with_get_details(), TestRenderPreview

### Community 33 - "BindingSet"
Cohesion: 0.09
Nodes (6): BindingSet, BindingSetRepository, RepositoryError, SourceIdentityRepository, _uuid(), TestBindingSet

### Community 35 - "MCPTools"
Cohesion: 0.13
Nodes (3): SearchLookupParams, MCPTools, TestMCPTools

### Community 36 - "SEAD MCP Server - Embedded Implementation"
Cohesion: 0.06
Nodes (33): 1. Enable the Feature Flag, 2. Test the MCP Server, 3. Try It in Python REPL, 4. Integrate into a Strategy, 5. Enable and Test via OpenRefine, Connection errors, Feature flag not working, Getting Started (5 Minutes) (+25 more)

### Community 37 - "test_provider_extended.py"
Cohesion: 0.06
Nodes (7): SingletonConfigProvider, reset_fixtures(), TestConfigStoreConfigureContext, TestConfigStoreConsolidateErrors, TestConfigStoreSetConfig, TestProviderThreadSafety, TestSingletonConfigProvider

### Community 38 - "test_mcp.py"
Cohesion: 0.14
Nodes (6): Candidate, GetByIdResult, LookupTable, RerankParams, RerankResult, SearchLookupResult

### Community 39 - "TranslationService"
Cohesion: 0.22
Nodes (5): LanguageDetection, TranslationService, TestTranslationServiceDetectLanguage, TestTranslationServiceHeuristics, TestTranslationServiceTranslate

### Community 40 - "public.tbl_datasets"
Cohesion: 0.06
Nodes (24): public.master_set_reference, public.typed_analysis_values, public.view_bibliography_references, public.view_chronometric_ages, public.view_identified_by, public.view_occurrence_ids, public.view_physical_abundances, public.view_physical_ages (+16 more)

### Community 41 - "__deploy__.sql"
Cohesion: 0.05
Nodes (56): authority.data_type, authority.data_type_group, authority.dating_uncertainty, authority.feature, authority.feature_type, authority.fuzzy_data_type(), authority.fuzzy_data_type_group(), authority.fuzzy_dating_uncertainty() (+48 more)

### Community 44 - "ReconCandidate"
Cohesion: 0.09
Nodes (6): ReconBatchResponse, ReconCandidate, ReconQueryResult, TestReconBatchResponse, TestReconCandidate, TestReconQueryResult

### Community 46 - "TestMCPModels"
Cohesion: 0.09
Nodes (3): MCPError, RawScores, TestMCPModels

### Community 47 - "ExtendRequestProperty"
Cohesion: 0.10
Nodes (7): ExtCell, ExtendRequest, ExtendRequestProperty, ExtendResponse, TestExtendRequest, TestExtendRequestProperty, TestExtendResponse

### Community 48 - "Proposal: SIMS `target_id` Contract For Delivery 1"
Cohesion: 0.11
Nodes (18): Acceptance Criteria, API change, Approved Identity-Allocation Decision, Backward compatibility, Behavior rules, Current Behavior, Final Recommendation, Identity ownership (+10 more)

### Community 50 - "public.tbl_sample_group_sampling_contexts"
Cohesion: 0.10
Nodes (15): tbl_sample_group_description_types_norm_trgm, tbl_sample_group_sampling_contexts_norm_trgm, tbl_sample_location_types_norm_trgm, tbl_sample_group_description_types_norm_trgm, tbl_sample_group_sampling_contexts_norm_trgm, tbl_sample_location_types_norm_trgm, authority.fuzzy_sample_group_description_type(), authority.sample_group_description_type (+7 more)

### Community 51 - "TestUtilityFunctions"
Cohesion: 0.11
Nodes (4): _has_non_scalar(), _is_scalar(), _resolve_format(), TestUtilityFunctions

### Community 52 - "SuggestEntityResponse"
Cohesion: 0.17
Nodes (4): SuggestEntityItem, SuggestEntityResponse, TestSuggestEntityItem, TestSuggestEntityResponse

### Community 54 - "format_rows_for_llm"
Cohesion: 0.08
Nodes (3): format_rows_for_llm(), TestEdgeCases, TestFormatRowsForLLM

### Community 56 - "GeoNamesRepository"
Cohesion: 0.14
Nodes (3): GeoNamesRepository, TestGeoNamesIntegration, TestGeoNamesRepository

### Community 57 - "strategies/test_strategy.py"
Cohesion: 0.15
Nodes (13): _DummyRepoInstance, _FakeRepository, _NoRepoStrategy, _StubConfigValue, test_as_candidate_includes_distance_and_threshold(), test_find_candidates_sorts_by_score_when_name_sim_missing(), test_find_candidates_uses_alternate_identity(), test_get_display_name_fallback_uses_key_title() (+5 more)

### Community 59 - "public.tbl_taxa_tree_master"
Cohesion: 0.06
Nodes (29): public.taxon_view, idx_taxa_tree_authors_name, idx_taxa_tree_master_author_id, idx_taxa_tree_master_genus_id, tbl_biblio_norm_trgm, tbl_taxa_synonyms_norm_trgm, tbl_taxa_tree_authors_norm_trgm, tbl_taxa_tree_master_norm_trgm (+21 more)

### Community 60 - "test_router_extended.py"
Cohesion: 0.12
Nodes (5): app(), client(), TestConfigDependency, TestContentTypeHandling, TestWhoAmIEndpoint

### Community 61 - "Phase 1 Task Plan: Prepare the Podman Deployment Bundle"
Cohesion: 0.13
Nodes (15): Acceptance-Criteria Coverage, Area 1: Build and describe the Podman container, Area 2: Add simple operator setup and safeguards, Definition Of Done, Deliverables, Phase 1 Task Plan: Prepare the Podman Deployment Bundle, Phase Acceptance Criteria, Phase Summary (+7 more)

### Community 62 - "site"
Cohesion: 0.08
Nodes (24): display_name, id_field, key, label_field, max, min, precision, max (+16 more)

### Community 63 - "TestRegistry"
Cohesion: 0.11
Nodes (4): _ensure_key_property(), Registry, decorator(), TestRegistry

### Community 64 - "EmbeddingPopulator"
Cohesion: 0.11
Nodes (3): EmbeddingPopulator, process_with_semaphore(), main()

### Community 65 - "main"
Cohesion: 0.15
Nodes (7): filter_entities_with_embeddings(), generate_semantic_sql(), generate_trigram_sql(), get_trigram_config(), load_entities_config(), main(), setup_logging()

### Community 66 - "ReconBatchRequest"
Cohesion: 0.13
Nodes (4): ReconBatchRequest, ReconBatchRequestHandler, TestReconBatchRequest, TestReconBatchRequestHandler

### Community 68 - "llm"
Cohesion: 0.09
Nodes (25): api_key, model, options, provider_id, llm, anthropic, enable_semantic_matching, enable_translation (+17 more)

### Community 69 - "method"
Cohesion: 0.06
Nodes (31): method, alternate_identity_column, description_column, extra_columns, method_group, alternate_identity_column, description_column, id_column (+23 more)

### Community 70 - "TestMCPConfig"
Cohesion: 0.15
Nodes (4): MCPConfig, MCPRetrievalConfig, MCPTableConfig, TestMCPConfig

### Community 72 - "foreign_key_column"
Cohesion: 0.11
Nodes (24): type_or_grouping, feature, alternate_identity_column, description_column, id_column, label_column, name, table_name (+16 more)

### Community 73 - "create_schema.sh"
Cohesion: 0.22
Nodes (17): cleanup(), deploy_schema(), g_deploy_sql_filename, g_root_dir, g_script_dir, generate_deploy_sql(), generate_entity_schema(), GREEN (+9 more)

### Community 74 - "PropertySetting"
Cohesion: 0.13
Nodes (6): ExtendDescriptor, PropertySetting, ProposePropertiesDescriptor, TestExtendDescriptor, TestPropertySetting, TestProposePropertiesDescriptor

### Community 75 - "Provider-Supplied Shared Metadata Entries"
Cohesion: 0.10
Nodes (19): Acceptance Criteria, Alternatives Considered, API, Current Behavior, Final Recommendation, Flow, Non-Goals, Open Questions (+11 more)

### Community 77 - "test_config_extended.py"
Cohesion: 0.03
Nodes (19): BaseResolver, is_config_path(), is_path_to_existing_file(), LoadResolver, SafeLoaderIgnoreUnknown, SubConfigResolver, yaml_path_join(), yaml_str_join() (+11 more)

### Community 80 - "SIMS Conceptual Model and Systems Design"
Cohesion: 0.07
Nodes (27): 1. Reuse a confirmed binding for a known source identity, 1. Value objects are aggregate state, not identity targets, 2. Match a new source identity to an existing tracked identity, 2. SIMS aggregate identity must remain distinct from source identifiers, 3. Allocate a new tracked identity for an unmatched source identity, 3. Consumers apply domain changes only after identity checks, 4. Correct a confirmed binding, 5. Invalidate a tracked identity after a rejected change request (+19 more)

### Community 82 - "location"
Cohesion: 0.08
Nodes (25): cte_definition, default, description, join_clause, name, type, where_clause, location (+17 more)

### Community 83 - "modification_type"
Cohesion: 0.08
Nodes (24): description, id, label, context, description_field, entity_type_description, id_field, label_field (+16 more)

### Community 86 - "reconcile_queries"
Cohesion: 0.15
Nodes (9): reconcile_queries(), _ConfigProvider, _RecordingStrategy, test_reconcile_queries_builds_properties_and_candidates(), test_reconcile_queries_covers_strategy_cls_none_branch(), test_reconcile_queries_empty_query_short_circuits(), test_reconcile_queries_fallback_default_limit(), test_reconcile_queries_missing_type_raises() (+1 more)

### Community 87 - "Dimension Details SQL"
Cohesion: 0.14
Nodes (15): authority.data_type, authority.immutable_unaccent, Data Types Resource, Data Type Details SQL, Data Type Fuzzy Find SQL, tbl_data_type_groups, tbl_data_types, Dimension Alternate Identity SQL (+7 more)

### Community 90 - "public.tbl_locations"
Cohesion: 0.13
Nodes (14): tbl_location_types, idx_locations_location_type_id, tbl_location_types_norm_trgm, tbl_locations_norm_trgm, authority.fuzzy_location(), authority.location, tbl_location_types_norm_trgm, tbl_locations_norm_trgm (+6 more)

### Community 91 - "sql_queries"
Cohesion: 0.09
Nodes (22): display_name, id_field, key, label_field, properties, description, id, name (+14 more)

### Community 93 - "llm"
Cohesion: 0.08
Nodes (29): api_key, model, options, provider_id, llm, anthropic, enable_semantic_matching, enable_translation (+21 more)

### Community 94 - "public.tbl_methods"
Cohesion: 0.06
Nodes (11): idx_measured_values_analysis_entity_id, tbl_method_groups_norm_trgm, tbl_methods_norm_trgm, tbl_method_groups_norm_trgm, tbl_methods_norm_trgm, authority.fuzzy_method(), authority.method, authority.fuzzy_method_group() (+3 more)

### Community 95 - "test_model.py"
Cohesion: 0.15
Nodes (8): SuggestPropertyItem, SuggestPropertyResponse, SuggestTypeItem, SuggestTypeResponse, TestSuggestPropertyItem, TestSuggestPropertyResponse, TestSuggestTypeItem, TestSuggestTypeResponse

### Community 96 - "recursive_filter_dict"
Cohesion: 0.08
Nodes (4): recursive_filter_dict(), recursive_update(), TestRecursiveFilterDict, TestRecursiveUpdate

### Community 98 - "MCPResources"
Cohesion: 0.10
Nodes (3): ServerInfo, MCPResources, TestMCPResources

### Community 99 - "taxa_tree_master"
Cohesion: 0.10
Nodes (21): taxa_synonym, alternate_identity_column, description_column, embedding_config, extra_columns, id_column, joins, label_column (+13 more)

### Community 100 - "env2dict"
Cohesion: 0.11
Nodes (3): env2dict(), TestConfigResolveReferences, TestEnv2Dict

### Community 101 - "FastAPI Application"
Cohesion: 0.15
Nodes (13): FastAPI Application, IdentityPolicy, Identity Router, IdentityService, Identity Tables, OpenRefine, Reconciliation Orchestrator, Reconciliation Router (+5 more)

### Community 102 - "taxa_tree_family"
Cohesion: 0.10
Nodes (21): taxa_tree_family, alternate_identity_column, description_column, extra_columns, id_column, joins, label_column, materialized (+13 more)

### Community 104 - ".test_find_candidates_with_llm_success"
Cohesion: 0.25
Nodes (3): Candidate, ReconciliationResponse, ReconciliationResult

### Community 106 - "BibliographicReferenceReconciliationStrategy"
Cohesion: 0.15
Nodes (4): BibliographicReferenceReconciliationStrategy, _FakeBiblioRepo, TestBibliographicReferenceReconciliationStrategy, TestBibliographicReferenceRepository

### Community 107 - "RAGHybridReconciliationStrategy"
Cohesion: 0.08
Nodes (31): Authority Views (authority.*), BaseRepository, ConfigValue, config.yml, entities.yml, get_connection(), LLM Integration, Embedded MCP Server (+23 more)

### Community 108 - "retrieval"
Cohesion: 0.18
Nodes (14): sem_weight, trgm_weight, language, retrieval, enabled, k, model, retrieval (+6 more)

### Community 109 - "analyze"
Cohesion: 0.07
Nodes (39): bibliographic_reference, alternate_identity_column, description_column, embedding_config, extra_columns, id_column, label_column, materialized (+31 more)

### Community 110 - "Review a GitHub pull request"
Cohesion: 0.17
Nodes (9): PR review criteria, Draft review JSON format, 1. Identify the exact PR and commit, 2. Validate possible findings, 3. Preview — stop here by default, 4. Publish only after explicit user approval, Integration notes, Non-negotiable boundaries (+1 more)

### Community 114 - "service.py"
Cohesion: 0.06
Nodes (23): Binding, BindRequest, ChangeDetectionResult, RejectDiagnostics, SourceIdentity, SourceIdentityKey, Submission, TrackedIdentity (+15 more)

### Community 115 - "Proposal: Move Authority Service Deployment from Docker to Podman"
Cohesion: 0.17
Nodes (12): Acceptance Criteria, Current Behavior, Final Recommendation, Non-Goals, Problem, Proposal: Move Authority Service Deployment from Docker to Podman, Proposed Design, Risks And Tradeoffs (+4 more)

### Community 116 - "SEAD Authority Service - AI Coding Instructions"
Cohesion: 0.67
Nodes (9): SEAD Authority Service - AI Coding Instructions, Design Docs Instructions, Development Docs Instructions, Mermaid Diagram Style Instructions, GitHub Workflow Instructions, Operations Docs Instructions, README Instructions, Testing Docs Instructions (+1 more)

### Community 117 - "Phase 2 Task Plan: First Deployment to the Target Host"
Cohesion: 0.17
Nodes (12): Acceptance-Criteria Coverage, Acceptance-Criteria Results, Definition Of Done, Deliverables, Phase 2 Task Plan: First Deployment to the Target Host, Phase Acceptance Criteria, Phase Summary, Progress Tracker (+4 more)

### Community 118 - "Entity Register"
Cohesion: 0.17
Nodes (11): Aggregate Boundaries, Cross-Aggregate Associations, Entity Register, Provider-Owned Child Entities (Value Objects), Provider-Owned Root Entities, Reconciliation Strategies, Relationship Entities (Bridges), Shape Shifter Target-Model Entity Register (+3 more)

### Community 119 - "SEAD MCP Server (sead.pg)"
Cohesion: 0.29
Nodes (8): LLM Providers (OpenAI, Anthropic, Ollama), Hybrid RAG + MCP Flow, RAG vs MCP Comparison, MCP Server Phase, get_by_id Tool, SEAD MCP Server (sead.pg), RAG Pipeline (MCP-based), rerank Tool

### Community 121 - "src/configuration/__init__.py"
Cohesion: 0.05
Nodes (21): shutdown(), startup(), ConfigProvider, get_config_provider(), reset_config_provider(), set_config_provider(), Configurable, inject_config() (+13 more)

### Community 122 - "Design"
Cohesion: 0.10
Nodes (20): 1. Resolve Identity, 2. Bind, 3. Record external reference (current integration), 4. Detect Change (Update Foundation), Approach, Authority-key intake, Business-key intake, Concept-to-Structure Mapping (+12 more)

### Community 124 - "configuration/test_utility.py"
Cohesion: 0.25
Nodes (3): test_replace_references_ignores_nested_list_expression(), test_replace_references_list_operations(), test_replace_references_simple_include()

### Community 127 - "taxa_tree_order"
Cohesion: 0.10
Nodes (21): record_type, alternate_identity_column, description_column, embedding_config, extra_columns, id_column, label_column, materialized (+13 more)

### Community 128 - "Podman Deployment Migration Phase Plan"
Cohesion: 0.18
Nodes (11): Cross-Phase Rules, Current Position, Final Recommendation, Phase 1: Prepare the Podman Deployment Bundle, Phase 2: Deploy to the Target Host, Phase Plan, Podman Deployment Migration Phase Plan, Problem (+3 more)

### Community 129 - "config-template.yml"
Cohesion: 0.13
Nodes (15): geonames, options, country_bias, feature_classes, fuzzy, lang, orderby, style (+7 more)

### Community 130 - "analyze"
Cohesion: 0.18
Nodes (19): embedding_config, analyze, dimension, ivfflat_lists, feature_type, alternate_identity_column, description_column, embedding_config (+11 more)

### Community 131 - "git_commit"
Cohesion: 0.12
Nodes (19): description, required, type, description, required, type, description, required (+11 more)

### Community 132 - "json"
Cohesion: 0.08
Nodes (24): Check Imports Pre-commit Hook, Ruff Pre-commit Hook, anchors_in_patch(), gh_api_json(), load_draft(), main(), require(), ReviewError (+16 more)

### Community 133 - "Proposal Document Structure Instructions"
Cohesion: 0.31
Nodes (8): Phase Plan Instructions, Proposal Document Structure Instructions, Proposal Writing Guide, Task Plan Instructions, Writing Style Instructions, Proposal and Planning Document Family, SIMS Proposals Directory, Proposal Template

### Community 134 - "analyze"
Cohesion: 0.28
Nodes (19): embedding_config, embedding_config, analyze, dimension, ivfflat_lists, embedding_config, embedding_config, embedding_config (+11 more)

### Community 135 - "AGENTS.md - AI Coding Agent Instructions"
Cohesion: 0.15
Nodes (17): AGENTS.md - AI Coding Agent Instructions, ConfigValue, Database Connection Singleton, OpenRefine Reconciliation API, RAG Hybrid Strategy, SIMS Identity Module, Output, Review Authority Service Configuration (+9 more)

### Community 136 - "location"
Cohesion: 0.11
Nodes (18): cte_definition, default, description, join_clause, name, type, where_clause, location (+10 more)

### Community 137 - "foreign_key_column"
Cohesion: 0.16
Nodes (18): type_or_grouping, feature, alternate_identity_column, description_column, id_column, label_column, name, table_name (+10 more)

### Community 138 - "location"
Cohesion: 0.11
Nodes (18): cte_definition, default, description, join_clause, name, type, where_clause, location (+10 more)

### Community 139 - "test_llm_input_format.py"
Cohesion: 0.18
Nodes (5): CSVFormatter, FormatterRegistry, JSONFormatter, MarkdownFormatter, TestFormatterRegistry

### Community 141 - "ConfigValue"
Cohesion: 0.06
Nodes (7): ConfigValue, TestConfigProvider, TestConfigurable, __init__(), TestConfigValueEdgeCases, test_config_value_supports_class_key(), test_inject_config_resolves_defaults()

### Community 142 - "SEAD Authority Service — Rootless Podman Deployment"
Cohesion: 0.17
Nodes (12): Build or publish a development image from the checkout, First-time setup, GitHub Actions image publication, Layout, Lifecycle, Pull a published image on the deployment account, Pull or build the image, Requirements (+4 more)

### Community 143 - "Implementation Phases"
Cohesion: 0.12
Nodes (12): Phase 2: Embedding Ingestion, Phase 3: Hybrid Search, Phase 4: Optional Reranking, What's Coming Next, Implementation Phases, ✅ Phase 0: Setup (Current), 🔄 Phase 1: Database Prep (In Progress), 📋 Phase 2: Embedding Ingestion (+4 more)

### Community 144 - "metadata.py"
Cohesion: 0.16
Nodes (10): _compile_property_settings(), _get_default_types(), _get_properties(), get_reconcile_properties(), get_reconciliation_metadata(), test_compile_property_settings_dedup_and_entity_types(), test_get_reconcile_properties_no_type(), test_get_reconcile_properties_query_filter() (+2 more)

### Community 145 - "data_type"
Cohesion: 0.12
Nodes (16): data_type, alternate_identity_column, description_column, extra_columns, data_type_group, alternate_identity_column, description_column, id_column (+8 more)

### Community 146 - ".create_connection_mock"
Cohesion: 0.09
Nodes (5): SiteRepository, create_connection_cm(), TestSiteReconciliationStrategyErrorHandling, TestSiteRepository, TestMultipleReconciliationStrategy

### Community 147 - "feature_type"
Cohesion: 0.12
Nodes (17): feature, alternate_identity_column, description_column, id_column, label_column, name, table_name, feature_type (+9 more)

### Community 148 - "method_rag.yml"
Cohesion: 0.22
Nodes (8): alternate_identity_field, display_name, id_field, key, label_field, properties, property_settings, sql_queries

### Community 149 - "public.tbl_taxa_tree_genera"
Cohesion: 0.14
Nodes (14): idx_taxa_tree_families_name, idx_taxa_tree_families_order_id, idx_taxa_tree_genera_family_id, idx_taxa_tree_genera_name, tbl_taxa_tree_families_norm_trgm, tbl_taxa_tree_genera_norm_trgm, tbl_taxa_tree_families_norm_trgm, tbl_taxa_tree_genera_norm_trgm (+6 more)

### Community 150 - "public.tbl_sample_description_types"
Cohesion: 0.32
Nodes (5): tbl_sample_description_types_norm_trgm, tbl_sample_description_types_norm_trgm, authority.fuzzy_sample_description_type(), authority.sample_description_type, tbl_sample_description_types_norm_trgm

### Community 151 - "dimension.yml"
Cohesion: 0.12
Nodes (15): alternate_identity_field, display_name, id_field, key, label_field, properties, description, id (+7 more)

### Community 152 - "__init__"
Cohesion: 0.15
Nodes (5): __init__(), __init__(), __init__(), registered_class_hook(), __init__()

### Community 153 - "public.tbl_record_types"
Cohesion: 0.18
Nodes (11): idx_taxa_tree_orders_order_id, tbl_record_types_norm_trgm, tbl_taxa_tree_orders_norm_trgm, tbl_record_types_norm_trgm, tbl_taxa_tree_orders_norm_trgm, authority.fuzzy_record_type(), authority.record_type, tbl_record_types_norm_trgm (+3 more)

### Community 155 - "options"
Cohesion: 0.06
Nodes (31): geonames, options, description, id, label, context, entity_type_description, lookup_fields_map (+23 more)

### Community 156 - "Countries Resource"
Cohesion: 0.40
Nodes (5): authority.fuzzy_location, authority.location, Countries Resource, Country Details SQL, Country Fuzzy Find SQL

### Community 157 - "container/config/entities.yml"
Cohesion: 0.13
Nodes (14): data_type_group, alternate_identity_column, description_column, id_column, label_column, name, table_name, location_type (+6 more)

### Community 158 - "llm"
Cohesion: 0.14
Nodes (14): llm, enable_semantic_matching, enable_translation, openai, provider, semantic_batch_size, translation_target_lang, api_key (+6 more)

### Community 159 - "tests/config/entities.yml"
Cohesion: 0.13
Nodes (14): data_type_group, alternate_identity_column, description_column, id_column, label_column, name, table_name, dating_uncertainty (+6 more)

### Community 161 - "sead-authority-service"
Cohesion: 0.14
Nodes (13): env_file, extra_hosts, image, platform, ports, restart, user, userns_mode (+5 more)

### Community 162 - "location.yml"
Cohesion: 0.14
Nodes (13): display_name, id_field, key, label_field, properties, description, id, name (+5 more)

### Community 163 - "public.tbl_data_types"
Cohesion: 0.19
Nodes (10): tbl_data_type_groups_norm_trgm, tbl_data_types_norm_trgm, tbl_data_type_groups_norm_trgm, tbl_data_types_norm_trgm, authority.data_type, authority.fuzzy_data_type(), authority.data_type_group, authority.fuzzy_data_type_group() (+2 more)

### Community 164 - "StrategyRegistry"
Cohesion: 0.18
Nodes (4): StrategyRegistry, __init__(), __init__(), __init__()

### Community 165 - "public.tbl_relative_ages"
Cohesion: 0.11
Nodes (15): tbl_dating_uncertainty_norm_trgm, tbl_relative_age_types_norm_trgm, tbl_relative_ages_norm_trgm, tbl_dating_uncertainty_norm_trgm, tbl_relative_age_types_norm_trgm, tbl_relative_ages_norm_trgm, authority.dating_uncertainty, authority.fuzzy_dating_uncertainty() (+7 more)

### Community 166 - "public.tbl_features"
Cohesion: 0.17
Nodes (11): idx_features_feature_type_id, tbl_feature_types_norm_trgm, tbl_features_norm_trgm, tbl_feature_types_norm_trgm, tbl_features_norm_trgm, authority.feature, authority.fuzzy_feature(), tbl_features_norm_trgm (+3 more)

### Community 167 - "modification_type"
Cohesion: 0.15
Nodes (13): description, id, label, context, entity_type_description, lookup_fields_map, lookup_format, output (+5 more)

### Community 168 - "modification_type"
Cohesion: 0.15
Nodes (13): description, id, label, context, entity_type_description, lookup_fields_map, lookup_format, output (+5 more)

### Community 169 - "config/config.yml"
Cohesion: 0.07
Nodes (29): features, use_mcp_server, identity, policy_file, well_known_scopes, table_specs, description, name (+21 more)

### Community 170 - "mcp"
Cohesion: 0.17
Nodes (12): dimensions, model, mcp, cache_ttl_seconds, embedding, enable_caching, retrieval, version (+4 more)

### Community 171 - "public.tbl_modification_types"
Cohesion: 0.38
Nodes (5): tbl_modification_types_norm_trgm, tbl_modification_types_norm_trgm, authority.fuzzy_modification_type(), authority.modification_type, tbl_modification_types_norm_trgm

### Community 172 - "mcp"
Cohesion: 0.17
Nodes (12): dimensions, model, mcp, cache_ttl_seconds, embedding, enable_caching, retrieval, version (+4 more)

### Community 174 - "database"
Cohesion: 0.17
Nodes (12): dbname, host, pool_max_size, pool_min_size, pool_timeout, port, user, options (+4 more)

### Community 175 - "mcp"
Cohesion: 0.17
Nodes (12): dimensions, model, mcp, cache_ttl_seconds, embedding, enable_caching, retrieval, version (+4 more)

### Community 176 - "foreign_key_column"
Cohesion: 0.33
Nodes (11): type_or_grouping, type_or_grouping, type_or_grouping, type_or_grouping, type_or_grouping, type_or_grouping, type_or_grouping, type_or_grouping (+3 more)

### Community 178 - "public.tbl_sample_types"
Cohesion: 0.38
Nodes (5): tbl_sample_types_norm_trgm, tbl_sample_types_norm_trgm, authority.fuzzy_sample_type(), authority.sample_type, tbl_sample_types_norm_trgm

### Community 179 - "llm"
Cohesion: 0.18
Nodes (11): api_key, model, provider_id, llm, anthropic, enable_semantic_matching, enable_translation, prompts (+3 more)

### Community 181 - "06_indexes.sql"
Cohesion: 0.04
Nodes (45): idx_abundance_modifications_abundance_id, idx_abundance_modifications_modification_type_id, idx_analysis_entity_prep_methods_analysis_entity_id, idx_analysis_entity_prep_methods_method_id, idx_biblio_id, idx_ecocode_groups_ecocode_system_id, idx_ecocode_groups_name, idx_ecocode_systems_biblio_id (+37 more)

### Community 182 - "handlers"
Cohesion: 0.18
Nodes (11): backtrace, compression, diagnose, format, level, retention, rotation, sink (+3 more)

### Community 183 - "taxa_synonym"
Cohesion: 0.18
Nodes (11): taxa_synonym, alternate_identity_column, description_column, embedding_config, extra_columns, id_column, joins, label_column (+3 more)

### Community 184 - "taxa_tree_genus"
Cohesion: 0.18
Nodes (11): taxa_tree_genus, alternate_identity_column, description_column, embedding_config, extra_columns, id_column, joins, label_column (+3 more)

### Community 185 - "mcp"
Cohesion: 0.18
Nodes (11): token, type, mcp, auth, base_url, enabled, fallback_to_db, tools (+3 more)

### Community 186 - "authority.feature_type"
Cohesion: 0.67
Nodes (4): authority.feature_type, Feature Type Details SQL, Feature Types Resource, Feature Type Fuzzy Find SQL

### Community 187 - "Core Concepts"
Cohesion: 0.20
Nodes (10): Binding, Binding Set, Change Request, Core Concepts, Identity Resolution, Materialization, Source Identity, Source Scope (+2 more)

### Community 190 - "openai"
Cohesion: 0.24
Nodes (10): options, openai, options, api_key, model, options, provider_id, max_tokens (+2 more)

### Community 191 - ".test_fetch_all_with_error_and_rollback"
Cohesion: 0.08
Nodes (6): TestDatabaseRepositoryTransactionHandling, TestManualDatabaseTesting, TestReconcileIntegration, execute_side_effect(), mock_rollback(), TestReconcileWithDebugger

### Community 192 - "bibliographic_reference"
Cohesion: 0.20
Nodes (10): bibliographic_reference, alternate_identity_column, description_column, embedding_config, extra_columns, id_column, label_column, materialized (+2 more)

### Community 193 - "sead_identity.bindings"
Cohesion: 0.10
Nodes (21): sead_identity.source_scopes, sead_identity.submissions, submissions_scope_idx, sead_identity.source_identities, source_identities_scope_entity_idx, sead_identity.source_identity_keys, source_identity_keys_lookup_idx, source_identity_keys_source_idx (+13 more)

### Community 194 - "method"
Cohesion: 0.20
Nodes (10): method, alternate_identity_column, description_column, extra_columns, id_column, label_column, materialized, name (+2 more)

### Community 195 - "modification_type"
Cohesion: 0.20
Nodes (10): modification_type, alternate_identity_column, description_column, embedding_config, extra_columns, id_column, label_column, materialized (+2 more)

### Community 196 - "record_type"
Cohesion: 0.20
Nodes (10): record_type, alternate_identity_column, description_column, embedding_config, extra_columns, id_column, label_column, materialized (+2 more)

### Community 197 - "site"
Cohesion: 0.20
Nodes (10): site, alternate_identity_column, description_column, embedding_config, extra_columns, id_column, label_column, materialized (+2 more)

### Community 198 - "taxa_tree_author"
Cohesion: 0.20
Nodes (10): taxa_tree_author, alternate_identity_column, description_column, embedding_config, extra_columns, id_column, label_column, materialized (+2 more)

### Community 199 - "ConfigStore"
Cohesion: 0.05
Nodes (12): get_config_dependency(), ConfigFactoryLike, ConfigLike, ConfigStore, setup_config_store(), _setup_connection_pool(), shutdown_connection_pool(), setup_config_store2() (+4 more)

### Community 200 - "tests/config/config.yml"
Cohesion: 0.20
Nodes (9): features, use_mcp_server, geonames, identity, policy_file, well_known_scopes, description, name (+1 more)

### Community 202 - "config/entities.yml"
Cohesion: 0.14
Nodes (14): relative_age, alternate_identity_column, description_column, id_column, label_column, name, table_name, relative_age_type (+6 more)

### Community 203 - "taxa_tree_family"
Cohesion: 0.20
Nodes (10): taxa_tree_family, alternate_identity_column, description_column, extra_columns, id_column, joins, label_column, materialized (+2 more)

### Community 207 - "taxa_tree_master"
Cohesion: 0.20
Nodes (10): taxa_tree_master, alternate_identity_column, description_column, extra_columns, id_column, joins, label_column, materialized (+2 more)

### Community 209 - "taxa_tree_order"
Cohesion: 0.20
Nodes (10): taxa_tree_order, alternate_identity_column, description_column, extra_columns, id_column, joins, label_column, materialized (+2 more)

### Community 210 - "sampling_context.yml"
Cohesion: 0.12
Nodes (16): display_name, id_field, key, label_field, properties, property_settings, sql_queries, details_sql (+8 more)

### Community 211 - "Storage Design"
Cohesion: 0.11
Nodes (19): Binding Sets, Bindings, Change Request References, Source Identities, Source Scopes, Storage Design, Submission–Source Identity Junction, Submissions (+11 more)

### Community 212 - "taxonomic_order_system"
Cohesion: 0.20
Nodes (10): taxonomic_order_system, alternate_identity_column, description_column, embedding_config, extra_columns, id_column, label_column, materialized (+2 more)

### Community 213 - "EntityPolicy"
Cohesion: 0.22
Nodes (5): EntityPolicy, _validate_operations(), _validate_policy(), TestEntityPolicyProperties, _provider_owned_policy()

### Community 217 - "taxonomy_note"
Cohesion: 0.20
Nodes (10): taxonomy_note, alternate_identity_column, description_column, embedding_config, extra_columns, id_column, label_column, materialized (+2 more)

### Community 220 - "with"
Cohesion: 0.20
Nodes (10): with, enable-cache, password, push-to-registry, python-version, ref, registry, subject-digest (+2 more)

### Community 249 - "SIMS — SEAD Identity Management System"
Cohesion: 0.22
Nodes (9): Archived (historical), Boundary to Shape Shifter, Current Status, Documentation Map, Reference Material, SIMS — SEAD Identity Management System, Source of Truth, System reference (+1 more)

### Community 250 - "data_type.yml"
Cohesion: 0.20
Nodes (9): display_name, id_field, key, label_field, properties, property_settings, sql_queries, details_sql (+1 more)

### Community 251 - "Create a Phase Task Plan"
Cohesion: 0.29
Nodes (6): Create a Phase Task Plan, Inputs, Limits, Output, References, Workflow

### Community 252 - "feature_type.yml"
Cohesion: 0.20
Nodes (9): display_name, id_field, key, label_field, properties, property_settings, sql_queries, details_sql (+1 more)

### Community 253 - "Create a Proposal"
Cohesion: 0.29
Nodes (7): Create a Proposal, Inputs, Limits, Output, Proposal Standard, References, Workflow

### Community 254 - "Implement a Phase Task Plan"
Cohesion: 0.22
Nodes (8): General Coding Practices Instructions, Implement a Phase Task Plan, Inputs, Limits, Output, Preconditions, References, Workflow

### Community 255 - "Requirements Docs"
Cohesion: 0.25
Nodes (7): Purpose, Requirements Docs, Scope boundaries, Size expectations, Sources to trust, What belongs, Writing rules

### Community 256 - "Review the AI coding model strategy"
Cohesion: 0.29
Nodes (6): Context to verify, Evaluation, Research, Review the AI coding model strategy, Strategy file, Write the strategy

### Community 257 - "IdentityService"
Cohesion: 0.60
Nodes (5): BindingSet, IdentityService, models.py, ResolutionOutcome (DTO), TrackedIdentity

### Community 258 - "Create a Phase Plan"
Cohesion: 0.29
Nodes (7): Create a Phase Plan, Inputs, Limits, Output, Phase Plan Standard, References, Workflow

### Community 259 - "anthropic"
Cohesion: 0.24
Nodes (10): api_key, model, options, provider_id, anthropic, options, options, max_tokens (+2 more)

### Community 260 - "taxa_synonym"
Cohesion: 0.20
Nodes (10): taxa_synonym, alternate_identity_column, description_column, extra_columns, id_column, joins, label_column, materialized (+2 more)

### Community 261 - "Create a Phase Task Plan"
Cohesion: 0.29
Nodes (7): Create a Phase Task Plan, Inputs, Limits, Output, References, Task Plan Standard, Workflow

### Community 262 - ".__init__"
Cohesion: 0.06
Nodes (4): MethodReconciliationStrategy, SamplingContextReconciliationStrategy, TaxonReconciliationStrategy, resolve_specification()

### Community 263 - "taxa_tree_family"
Cohesion: 0.20
Nodes (10): taxa_tree_family, alternate_identity_column, description_column, extra_columns, id_column, joins, label_column, materialized (+2 more)

### Community 264 - "taxa_tree_genus"
Cohesion: 0.20
Nodes (10): taxa_tree_genus, alternate_identity_column, description_column, extra_columns, id_column, joins, label_column, materialized (+2 more)

### Community 265 - "taxa_tree_master"
Cohesion: 0.20
Nodes (10): taxa_tree_master, alternate_identity_column, description_column, extra_columns, id_column, joins, label_column, materialized (+2 more)

### Community 266 - "taxa_tree_order"
Cohesion: 0.20
Nodes (10): taxa_tree_order, alternate_identity_column, description_column, extra_columns, id_column, joins, label_column, materialized (+2 more)

### Community 268 - "MockConfigProvider"
Cohesion: 0.05
Nodes (5): MockConfigProvider, TestPreviewEndpoint, TestPropertiesEndpoint, TestMockConfigProvider, test_openai_provider_uses_configured_endpoint()

### Community 269 - "Create a Proposal"
Cohesion: 0.29
Nodes (7): Create a Proposal, Inputs, Limits, Output, Proposal Standard, References, Workflow

### Community 270 - "Implement a Phase Task Plan"
Cohesion: 0.29
Nodes (7): Implement a Phase Task Plan, Inputs, Limits, Output, Preconditions, References, Workflow

### Community 271 - "options"
Cohesion: 0.22
Nodes (9): dbname, pool_max_size, pool_min_size, pool_timeout, options, auto_accept_threshold, database, default_query_limit (+1 more)

### Community 274 - "Create a Phase Plan"
Cohesion: 0.33
Nodes (6): Create a Phase Plan, Inputs, Limits, Output, References, Workflow

### Community 275 - "Move a Proposal"
Cohesion: 0.33
Nodes (5): Limits, Move a Proposal, Move and update links, Resolve the move, Verify

### Community 276 - "Review a Proposal"
Cohesion: 0.33
Nodes (6): Inputs, Limits, Output, References, Review a Proposal, Workflow

### Community 277 - "Clarify Technical Docs"
Cohesion: 0.33
Nodes (4): Rewrite Rules, Clarify Technical Docs, Output, Use This Skill

### Community 280 - "build.sh"
Cohesion: 0.53
Nodes (5): env_or(), print_usage(), read_env_value(), seen_tags, build.sh script

### Community 281 - "handlers"
Cohesion: 0.18
Nodes (11): backtrace, compression, diagnose, format, level, retention, rotation, sink (+3 more)

### Community 287 - "Clarify Technical Docs"
Cohesion: 0.50
Nodes (3): Clarify Technical Docs, Output, Use This Skill

### Community 288 - "taxonomy_note"
Cohesion: 0.20
Nodes (10): taxonomy_note, alternate_identity_column, description_column, embedding_config, extra_columns, id_column, label_column, materialized (+2 more)

### Community 290 - "container/config/config.yml"
Cohesion: 0.22
Nodes (8): features, use_mcp_server, geonames, options, auto_accept_threshold, default_query_limit, id_base, table_specs

### Community 293 - "Work Breakdown"
Cohesion: 0.67
Nodes (3): Area 1: Confirm target and prepare first deployment, Area 2: Start and verify the first Podman deployment, Work Breakdown

### Community 294 - "policy"
Cohesion: 0.22
Nodes (9): max_boost, similarity_threshold, policy, geonames, site, to_far_distance_km, very_near_distance_km, place_name_similarity_boost (+1 more)

### Community 297 - "data_type"
Cohesion: 0.22
Nodes (9): data_type, alternate_identity_column, description_column, extra_columns, id_column, label_column, materialized, name (+1 more)

### Community 298 - "steps"
Cohesion: 0.05
Nodes (39): if, needs, permissions, uses, with, GH_TOKEN, jobs, build-and-push (+31 more)

### Community 299 - "Functional Requirements"
Cohesion: 0.22
Nodes (9): Binding set requirements, Change Request completeness requirements, Domain modeling requirements, Functional Requirements, Idempotency and mapping requirements, Identifier intake requirements, Identity model requirements, Submission and traceability requirements (+1 more)

### Community 300 - "Config"
Cohesion: 0.04
Nodes (15): Config, decorated(), resolve_arguments(), TestConfigClone, TestConfigUpdate, test_config_get_defaults_and_mandatory(), test_config_resolve_applies_env(), test_config_update_and_exists() (+7 more)

### Community 301 - "config_fixtures.py"
Cohesion: 0.15
Nodes (8): config_context(), mock_config_context(), mock_connection(), patch_config_provider(), restore_production_config(), setup_test_config(), test_config_dict(), test_config_provider()

### Community 303 - "Domain Concepts"
Cohesion: 0.22
Nodes (9): Conceptual model alignment, Core identity concepts, Domain Concepts, Entity subtypes, Provider-owned entities, Relationship entities, Relationship types, Shared metadata entities (+1 more)

### Community 304 - "administrative_region.yml"
Cohesion: 0.22
Nodes (8): display_name, id_field, key, label_field, property_settings, sql_queries, details_sql, fuzzy_find_sql

### Community 305 - "country.yml"
Cohesion: 0.22
Nodes (8): display_name, id_field, key, label_field, property_settings, sql_queries, details_sql, fuzzy_find_sql

### Community 307 - "policy"
Cohesion: 0.22
Nodes (9): max_boost, similarity_threshold, policy, geonames, site, to_far_distance_km, very_near_distance_km, place_name_similarity_boost (+1 more)

### Community 308 - "bibliographic_reference"
Cohesion: 0.22
Nodes (9): bibliographic_reference, alternate_identity_column, description_column, extra_columns, id_column, label_column, materialized, name (+1 more)

### Community 309 - "data_type"
Cohesion: 0.22
Nodes (9): data_type, alternate_identity_column, description_column, extra_columns, id_column, label_column, materialized, name (+1 more)

### Community 310 - "feature_type"
Cohesion: 0.22
Nodes (9): feature_type, alternate_identity_column, description_column, extra_columns, id_column, label_column, materialized, name (+1 more)

### Community 311 - "method"
Cohesion: 0.22
Nodes (9): method, alternate_identity_column, description_column, extra_columns, id_column, label_column, materialized, name (+1 more)

### Community 312 - "modification_type"
Cohesion: 0.22
Nodes (9): modification_type, alternate_identity_column, description_column, extra_columns, id_column, label_column, materialized, name (+1 more)

### Community 313 - "record_type"
Cohesion: 0.22
Nodes (9): record_type, alternate_identity_column, description_column, extra_columns, id_column, label_column, materialized, name (+1 more)

### Community 314 - "site"
Cohesion: 0.22
Nodes (9): site, alternate_identity_column, description_column, extra_columns, id_column, label_column, materialized, name (+1 more)

### Community 315 - "taxa_tree_author"
Cohesion: 0.22
Nodes (9): taxa_tree_author, alternate_identity_column, description_column, extra_columns, id_column, label_column, materialized, name (+1 more)

### Community 316 - "taxonomic_order_system"
Cohesion: 0.22
Nodes (9): taxonomic_order_system, alternate_identity_column, description_column, extra_columns, id_column, label_column, materialized, name (+1 more)

### Community 317 - "taxonomy_note"
Cohesion: 0.22
Nodes (9): taxonomy_note, alternate_identity_column, description_column, extra_columns, id_column, label_column, materialized, name (+1 more)

### Community 319 - "defaults"
Cohesion: 0.50
Nodes (4): defaults, accept_uuid, auto_confirm, entity_subtype

### Community 320 - "database"
Cohesion: 0.25
Nodes (8): dbname, host, pool_max_size, pool_min_size, pool_timeout, port, user, database

### Community 321 - "options"
Cohesion: 0.25
Nodes (8): options, country_bias, feature_classes, fuzzy, lang, orderby, style, username

### Community 322 - "cache"
Cohesion: 0.25
Nodes (8): cache, backend, keys, ttl, url, prefix, candidates_sec, llm_result_sec

### Community 323 - "geonames.yml"
Cohesion: 0.25
Nodes (7): display_name, id_field, key, label_field, properties, property_settings, sql_queries

### Community 324 - "options"
Cohesion: 0.25
Nodes (8): options, country_bias, feature_classes, fuzzy, lang, orderby, style, username

### Community 325 - "handlers"
Cohesion: 0.25
Nodes (8): format, level, retention, rotation, sink, logging, folder, handlers

### Community 328 - "sample_description_type"
Cohesion: 0.29
Nodes (7): sample_description_type, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 329 - "config/entities.yml"
Cohesion: 0.08
Nodes (23): Schema Generation from Templates, dating_uncertainty, alternate_identity_column, description_column, id_column, label_column, name, table_name (+15 more)

### Community 331 - "sample_type"
Cohesion: 0.29
Nodes (7): sample_type, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 332 - "sampling_context"
Cohesion: 0.29
Nodes (7): sampling_context, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 333 - "ollama"
Cohesion: 0.29
Nodes (7): ollama, host, model, options, provider_id, timeout, num_predict

### Community 334 - "dating_uncertainty"
Cohesion: 0.29
Nodes (7): dating_uncertainty, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 335 - "method_group"
Cohesion: 0.29
Nodes (7): method_group, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 336 - "relative_age_type"
Cohesion: 0.29
Nodes (7): relative_age_type, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 337 - "sample_description_type"
Cohesion: 0.29
Nodes (7): sample_description_type, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 338 - "sample_group_description_type"
Cohesion: 0.29
Nodes (7): sample_group_description_type, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 339 - "sample_location_type"
Cohesion: 0.29
Nodes (7): sample_location_type, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 340 - "sample_type"
Cohesion: 0.29
Nodes (7): sample_type, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 341 - "sampling_context"
Cohesion: 0.29
Nodes (7): sampling_context, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 342 - "embeddings"
Cohesion: 0.29
Nodes (7): embeddings, batch_size, dim, model, refresh, on_insert_update, schedule

### Community 343 - "ollama"
Cohesion: 0.29
Nodes (7): ollama, host, model, options, provider_id, timeout, num_predict

### Community 344 - "site"
Cohesion: 0.29
Nodes (7): max_boost, similarity_threshold, site, to_far_distance_km, very_near_distance_km, place_name_similarity_boost, proximity_boost

### Community 345 - "steps"
Cohesion: 0.38
Nodes (7): steps, id, if, name, run, uses, steps

### Community 346 - "foreign_key_column"
Cohesion: 0.48
Nodes (7): type_or_grouping, type_or_grouping, type_or_grouping, type_or_grouping, type_or_grouping, foreign_key_column, foreign_table

### Community 347 - "ollama"
Cohesion: 0.29
Nodes (7): ollama, host, model, options, provider_id, timeout, num_predict

### Community 348 - "table_specs"
Cohesion: 0.29
Nodes (7): alternate_identity_column, description_column, id_column, label_column, table_name, table_specs, sample_description_type

### Community 349 - "location_type"
Cohesion: 0.29
Nodes (7): location_type, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 350 - "method_group"
Cohesion: 0.29
Nodes (7): method_group, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 351 - "relative_age"
Cohesion: 0.29
Nodes (7): relative_age, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 352 - "relative_age_type"
Cohesion: 0.29
Nodes (7): relative_age_type, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 353 - "sample_description_type"
Cohesion: 0.29
Nodes (7): sample_description_type, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 354 - "sample_group_description_type"
Cohesion: 0.29
Nodes (7): sample_group_description_type, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 355 - "sample_location_type"
Cohesion: 0.29
Nodes (7): sample_location_type, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 356 - "sample_type"
Cohesion: 0.29
Nodes (7): sample_type, alternate_identity_column, description_column, id_column, label_column, name, table_name

### Community 357 - "allocate_new"
Cohesion: 0.40
Nodes (5): accept_uuid, auto_confirm, entity_subtype, entities, abundance

### Community 358 - "bind_existing"
Cohesion: 0.40
Nodes (5): accept_uuid, auto_confirm, entity_subtype, operations, analysis_entity

### Community 359 - "options"
Cohesion: 0.33
Nodes (6): dbname, options, auto_accept_threshold, database, default_query_limit, id_base

### Community 360 - "handlers"
Cohesion: 0.33
Nodes (6): format, level, sink, logging, folder, handlers

### Community 361 - "env"
Cohesion: 0.33
Nodes (6): env, GIT_COMMIT, GIT_REF, IMAGE_NAME, IMAGE_TAGS, TARGET_ENVIRONMENT

### Community 362 - "build-and-push"
Cohesion: 0.33
Nodes (6): needs, runs-on, jobs, build-and-push, test, runs-on

### Community 363 - "permissions"
Cohesion: 0.33
Nodes (6): permissions, artifact-metadata, attestations, contents, id-token, packages

### Community 364 - "target_environment"
Cohesion: 0.33
Nodes (6): target_environment, default, description, options, required, type

### Community 365 - "data_type"
Cohesion: 0.33
Nodes (6): alternate_identity_column, description_column, id_column, label_column, table_name, data_type

### Community 366 - "data_type_group"
Cohesion: 0.33
Nodes (6): alternate_identity_column, description_column, id_column, label_column, table_name, data_type_group

### Community 367 - "dating_uncertainty"
Cohesion: 0.33
Nodes (6): alternate_identity_column, description_column, id_column, label_column, table_name, dating_uncertainty

### Community 368 - "feature"
Cohesion: 0.33
Nodes (6): alternate_identity_column, description_column, id_column, label_column, table_name, feature

### Community 369 - "feature_type"
Cohesion: 0.33
Nodes (6): alternate_identity_column, description_column, id_column, label_column, table_name, feature_type

### Community 370 - "location"
Cohesion: 0.33
Nodes (6): alternate_identity_column, description_column, id_column, label_column, table_name, location

### Community 371 - "location_type"
Cohesion: 0.33
Nodes (6): alternate_identity_column, description_column, id_column, label_column, table_name, location_type

### Community 372 - "method"
Cohesion: 0.33
Nodes (6): alternate_identity_column, description_column, id_column, label_column, table_name, method

### Community 373 - "method_group"
Cohesion: 0.33
Nodes (6): alternate_identity_column, description_column, id_column, label_column, table_name, method_group

### Community 374 - "modification_type"
Cohesion: 0.33
Nodes (6): alternate_identity_column, description_column, id_column, label_column, table_name, modification_type

### Community 375 - "record_type"
Cohesion: 0.33
Nodes (6): alternate_identity_column, description_column, id_column, label_column, table_name, record_type

### Community 376 - "relative_age"
Cohesion: 0.33
Nodes (6): alternate_identity_column, description_column, id_column, label_column, table_name, relative_age

### Community 377 - "relative_age_type"
Cohesion: 0.33
Nodes (6): alternate_identity_column, description_column, id_column, label_column, table_name, relative_age_type

### Community 378 - "sample_group_description_type"
Cohesion: 0.33
Nodes (6): alternate_identity_column, description_column, id_column, label_column, table_name, sample_group_description_type

### Community 379 - "sample_location_type"
Cohesion: 0.33
Nodes (6): alternate_identity_column, description_column, id_column, label_column, table_name, sample_location_type

### Community 380 - "sample_type"
Cohesion: 0.33
Nodes (6): alternate_identity_column, description_column, id_column, label_column, table_name, sample_type

### Community 381 - "sampling_context"
Cohesion: 0.33
Nodes (6): alternate_identity_column, description_column, id_column, label_column, table_name, sampling_context

### Community 382 - "site"
Cohesion: 0.33
Nodes (6): alternate_identity_column, description_column, id_column, label_column, table_name, site

### Community 383 - "interface"
Cohesion: 0.40
Nodes (4): interface, default_prompt, display_name, short_description

### Community 384 - "interface"
Cohesion: 0.40
Nodes (4): interface, default_prompt, display_name, short_description

### Community 385 - "data_type"
Cohesion: 0.40
Nodes (5): accept_uuid, auto_confirm, entity_subtype, operations, data_type

### Community 386 - "dataset"
Cohesion: 0.40
Nodes (5): accept_uuid, auto_confirm, entity_subtype, operations, dataset

### Community 387 - "feature_type"
Cohesion: 0.40
Nodes (5): feature_type, accept_uuid, auto_confirm, entity_subtype, operations

### Community 388 - "method"
Cohesion: 0.40
Nodes (5): method, accept_uuid, auto_confirm, entity_subtype, operations

### Community 389 - "sample"
Cohesion: 0.40
Nodes (5): sample, accept_uuid, auto_confirm, entity_subtype, operations

### Community 390 - "sample_dimension"
Cohesion: 0.40
Nodes (5): sample_dimension, accept_uuid, auto_confirm, entity_subtype, operations

### Community 391 - "sample_group"
Cohesion: 0.40
Nodes (5): sample_group, accept_uuid, auto_confirm, entity_subtype, operations

### Community 392 - "site"
Cohesion: 0.28
Nodes (9): operations, operations, site, allocate_new, bind_existing, accept_uuid, auto_confirm, entity_subtype (+1 more)

### Community 393 - "submission"
Cohesion: 0.40
Nodes (5): submission, accept_uuid, auto_confirm, entity_subtype, operations

### Community 394 - "taxa_tree_master"
Cohesion: 0.40
Nodes (5): taxa_tree_master, accept_uuid, auto_confirm, entity_subtype, operations

### Community 395 - "unit"
Cohesion: 0.40
Nodes (5): unit, accept_uuid, auto_confirm, entity_subtype, operations

### Community 396 - "build.yml"
Cohesion: 0.40
Nodes (4): concurrency, cancel-in-progress, group, name

### Community 399 - "prompts"
Cohesion: 0.40
Nodes (5): prompts, abbreviation, language_detection, reconciliation, translation

## Ambiguous Edges - Review These
- `method` → `taxa_tree_order`  [AMBIGUOUS]
  tests/config/entities.yml · relation: conceptually_related_to
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

## Knowledge Gaps
- **51 isolated node(s):** `seen_tags`, `authority-service`, `RED`, `GREEN`, `YELLOW` (+46 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 3417 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **92 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AGENTS.md - AI Coding Agent Instructions` connect `AGENTS.md - AI Coding Agent Instructions` to `router.py`, `BaseRepository`, `Proposal Document Structure Instructions`, `IdentityService`, `config/entities.yml`, `src/configuration/__init__.py`?**
  _High betweenness centrality (0.164) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `with_test_config()` (e.g. with `async_wrapper()` and `sync_wrapper()`) actually correct?**
  _`with_test_config()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `seen_tags`, `authority-service`, `RED` to the rest of the system?**
  _51 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `01_tables.sql` be split into smaller, more focused modules?**
  _Cohesion score 0.014598540145985401 - nodes in this community are weakly interconnected._
- **Why does `SIMS Identity Module` connect `SIMS Identity Module` to `config/config.yml`, `service.py`, `EntityPolicy`, `IdentityService`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `method` and `taxa_tree_order`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `SEAD Authority Service - AI Coding Instructions` and `Design Docs Instructions`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._