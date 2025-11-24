# Taxonomic Data Reconciliation Strategy for SEAD

## Overview

Taxonomic reconciliation is complex due to:
1. **Hierarchical structure**: Order → Family → Genus → Species
2. **Variable identification levels**: Species, genus, family, or order
3. **Uncertainty indicators**: cf., aff., ?, sp., spp., etc.
4. **Data format variations**: Single column vs. multiple columns
5. **Authority citations**: Author names with dates and qualifiers

This document proposes a comprehensive strategy for reconciling taxonomic data in SEAD.

## SEAD Taxonomic Hierarchy

```
tbl_taxa_tree_orders (order_id, order_name)
    ↓
tbl_taxa_tree_families (family_id, family_name, order_id)
    ↓
tbl_taxa_tree_genera (genus_id, genus_name, family_id)
    ↓
tbl_taxa_tree_master (taxon_id, species, genus_id, author_id)
    ↓
tbl_taxa_tree_authors (author_id, author_name)
```

## Reconciliation Architecture

### Two-Tier Approach

#### 1. Entity-Level Reconciliation (Low-Level)
Individual OpenRefine entity types for each taxonomic rank:

- **`/reconcile/taxa_author`** - Taxonomic authorities (e.g., "L.", "Bojer ex Sims")
- **`/reconcile/taxa_order`** - Taxonomic orders (e.g., "Coleoptera", "Lamiales")
- **`/reconcile/taxa_family`** - Families (e.g., "Aceraceae", "Rosaceae")
- **`/reconcile/taxa_genus`** - Genera (e.g., "Acer", "Rosa")
- **`/reconcile/taxa_species`** - Full species (e.g., "Acer platanoides L.")

Each endpoint uses hybrid search (trigram + semantic embeddings).

#### 2. Orchestrated Reconciliation (High-Level)
A specialized **`TaxaReconciliationStrategy`** that:

1. **Parses** taxonomic strings into components
2. **Classifies** identification level (species, genus, family, order)
3. **Handles** uncertainty indicators (cf., aff., ?, sp., spp.)
4. **Reconciles** at appropriate hierarchical level
5. **Validates** hierarchical consistency
6. **Returns** structured results with taxonomic rank and confidence

---

## Phase 1: Entity-Level Strategies

### OpenRefine Entity Types

Create individual reconciliation endpoints for each taxonomic rank:

```python
# src/strategies/taxa_author_strategy.py
class TaxaAuthorReconciliationStrategy(RAGHybridReconciliationStrategy):
    entity_type = "taxa_author"
    table = "taxa_tree_authors"
    id_column = "author_id"
    label_column = "label"
    
# src/strategies/taxa_order_strategy.py
class TaxaOrderReconciliationStrategy(RAGHybridReconciliationStrategy):
    entity_type = "taxa_order"
    table = "taxa_tree_orders"
    id_column = "order_id"
    label_column = "label"
    
# src/strategies/taxa_family_strategy.py
class TaxaFamilyReconciliationStrategy(RAGHybridReconciliationStrategy):
    entity_type = "taxa_family"
    table = "taxa_tree_families"
    id_column = "family_id"
    label_column = "label"
    
# src/strategies/taxa_genus_strategy.py
class TaxaGenusReconciliationStrategy(RAGHybridReconciliationStrategy):
    entity_type = "taxa_genus"
    table = "taxa_tree_genera"
    id_column = "genus_id"
    label_column = "label"
    
# src/strategies/taxa_species_strategy.py
class TaxaSpeciesReconciliationStrategy(RAGHybridReconciliationStrategy):
    entity_type = "taxa_species"
    table = "taxa_tree_master"
    id_column = "taxon_id"
    label_column = "label"  # genus + species
```

---

## Phase 2: High-Level Orchestration

### TaxaReconciliationStrategy

A specialized strategy that orchestrates the reconciliation workflow:

```python
# src/strategies/taxa_reconciliation_strategy.py

class TaxaReconciliationStrategy(BaseReconciliationStrategy):
    """
    Orchestrated taxonomic reconciliation strategy.
    
    Handles:
    - Parsing taxonomic strings
    - Identifying taxonomic rank
    - Managing uncertainty indicators
    - Hierarchical validation
    - Multi-level fallback
    """
    
    entity_type = "taxa"
    
    def __init__(self, db_connection):
        self.db = db_connection
        # Initialize sub-strategies
        self.species_strategy = TaxaSpeciesReconciliationStrategy(db_connection)
        self.genus_strategy = TaxaGenusReconciliationStrategy(db_connection)
        self.family_strategy = TaxaFamilyReconciliationStrategy(db_connection)
        self.order_strategy = TaxaOrderReconciliationStrategy(db_connection)
        self.author_strategy = TaxaAuthorReconciliationStrategy(db_connection)
    
    async def reconcile(self, query: str, limit: int = 10) -> List[Candidate]:
        # Step 1: Parse taxonomic string
        parsed = self.parse_taxonomic_string(query)
        
        # Step 2: Determine identification level
        level = self.determine_taxonomic_level(parsed)
        
        # Step 3: Handle uncertainty
        uncertainty = self.extract_uncertainty(parsed)
        
        # Step 4: Reconcile at appropriate level
        candidates = await self.reconcile_at_level(parsed, level, limit)
        
        # Step 5: Validate hierarchy
        candidates = self.validate_hierarchy(candidates)
        
        # Step 6: Enrich with taxonomic context
        candidates = self.enrich_candidates(candidates, parsed, uncertainty)
        
        return candidates
```

---

## Parsing Taxonomic Strings

### Input Format Variations

#### Single Column (Common)
```
"Acer platanoides L."
"Acer sp."
"Quercus cf. robur"
"Rosa aff. canina"
"Betula ?"
"Salix/Populus"
"Coleoptera indet."
```

#### Multiple Columns (Structured)
```
genus: "Acer"
species: "platanoides"
author: "L."
qualifier: None
```

### Parsing Logic

```python
def parse_taxonomic_string(self, query: str) -> TaxonomicParsed:
    """
    Parse taxonomic string into components.
    
    Returns:
        TaxonomicParsed(
            genus: str | None,
            species: str | None,
            author: str | None,
            qualifier: str | None,  # cf., aff., ?, etc.
            rank: str,  # 'species', 'genus', 'family', 'order'
            original: str
        )
    """
    # Remove leading/trailing whitespace
    query = query.strip()
    
    # Detect and extract qualifiers
    qualifier = None
    if ' cf. ' in query:
        qualifier = 'cf.'
        query = query.replace(' cf. ', ' ')
    elif ' aff. ' in query:
        qualifier = 'aff.'
        query = query.replace(' aff. ', ' ')
    elif query.endswith('?'):
        qualifier = '?'
        query = query.rstrip('?').strip()
    
    # Split into tokens
    tokens = query.split()
    
    # Pattern matching
    if len(tokens) == 1:
        # Single token: likely genus, family, or order
        return TaxonomicParsed(
            genus=tokens[0],
            rank='genus',
            qualifier=qualifier,
            original=query
        )
    
    elif len(tokens) >= 2:
        genus = tokens[0]
        
        # Check for "sp." or "spp."
        if tokens[1] in ['sp.', 'spp.', 'indet.']:
            return TaxonomicParsed(
                genus=genus,
                species=tokens[1],
                rank='genus',  # Identified at genus level
                qualifier=qualifier,
                original=query
            )
        
        # Check for split identification (e.g., "Salix/Populus")
        if '/' in genus:
            return TaxonomicParsed(
                genus=genus,
                rank='genus_group',
                qualifier='split',
                original=query
            )
        
        # Species epithet
        species = tokens[1]
        
        # Author (remaining tokens)
        author = ' '.join(tokens[2:]) if len(tokens) > 2 else None
        
        return TaxonomicParsed(
            genus=genus,
            species=species,
            author=author,
            rank='species',
            qualifier=qualifier,
            original=query
        )
    
    return TaxonomicParsed(original=query, rank='unknown')
```

---

## Handling Uncertainty Indicators

### Common Qualifiers

| Qualifier | Meaning | Reconciliation Strategy |
|-----------|---------|-------------------------|
| **cf.** | "confer" - compare with | Return candidates, mark as uncertain |
| **aff.** | "affinis" - affinity with | Return related taxa, mark as uncertain |
| **?** | Uncertain identification | Increase candidate limit, lower threshold |
| **sp.** | Unspecified single species | Match at genus level |
| **spp.** | Multiple unspecified species | Match at genus level, plural context |
| **indet.** | Indeterminate | Match at higher rank (genus/family) |
| **/** | Split identification | Return multiple candidates |
| **grp** | Group/complex | Match at genus or species group level |

### Implementation

```python
def adjust_for_uncertainty(self, parsed: TaxonomicParsed, candidates: List[Candidate]) -> List[Candidate]:
    """
    Adjust candidate scores and metadata based on uncertainty indicators.
    """
    if parsed.qualifier in ['cf.', 'aff.', '?']:
        for candidate in candidates:
            # Reduce match score to reflect uncertainty
            candidate.match_score *= 0.85
            
            # Add uncertainty flag to metadata
            candidate.metadata['uncertainty'] = parsed.qualifier
            candidate.metadata['note'] = f"Uncertain identification ({parsed.qualifier})"
    
    elif parsed.qualifier == 'split':
        # For split identifications (e.g., "Salix/Populus")
        genera = parsed.genus.split('/')
        # Return candidates from both genera
        # (implementation details...)
    
    return candidates
```

---

## Hierarchical Reconciliation

### Cascading Strategy

When species-level match fails or is not attempted (e.g., "Acer sp."):

1. **Try Species Level** (if specific epithet provided)
   - Search `taxa_tree_master` for full scientific name
   - Example: "Acer platanoides" → taxon_id=5

2. **Fall Back to Genus** (if species fails or "sp." indicator)
   - Search `taxa_tree_genera` for genus name
   - Example: "Acer sp." → genus_id=3

3. **Fall Back to Family** (if genus fails)
   - Search `taxa_tree_families`
   - Example: "Aceraceae" → family_id=3

4. **Fall Back to Order** (if family fails)
   - Search `taxa_tree_orders`
   - Example: "Sapindales" → order_id=2

### Implementation

```python
async def reconcile_at_level(self, parsed: TaxonomicParsed, level: str, limit: int) -> List[Candidate]:
    """
    Reconcile at the determined taxonomic level with fallback.
    """
    if level == 'species' and parsed.genus and parsed.species:
        # Try full species match
        query = f"{parsed.genus} {parsed.species}"
        candidates = await self.species_strategy.reconcile(query, limit)
        
        if not candidates or candidates[0].match_score < 0.5:
            # Fall back to genus
            candidates = await self.genus_strategy.reconcile(parsed.genus, limit)
            for c in candidates:
                c.metadata['matched_at'] = 'genus'
                c.metadata['original_level'] = 'species'
        
        return candidates
    
    elif level == 'genus':
        return await self.genus_strategy.reconcile(parsed.genus, limit)
    
    elif level == 'family':
        # Assume query is family name
        return await self.family_strategy.reconcile(parsed.original, limit)
    
    elif level == 'order':
        return await self.order_strategy.reconcile(parsed.original, limit)
    
    return []
```

---

## Hierarchical Validation

### Consistency Checking

After reconciliation, validate that the taxonomic hierarchy is consistent:

```python
def validate_hierarchy(self, candidates: List[Candidate]) -> List[Candidate]:
    """
    Validate hierarchical consistency of candidates.
    
    For each candidate:
    - Fetch genus → family → order chain
    - Check for mismatches
    - Flag inconsistencies
    """
    for candidate in candidates:
        if candidate.entity_type == 'taxa_species':
            # Fetch full hierarchy
            hierarchy = self.fetch_hierarchy(candidate.id)
            
            # Validate (e.g., genus matches expected family)
            if not hierarchy.is_valid():
                candidate.metadata['hierarchy_warning'] = True
                candidate.match_score *= 0.9
    
    return candidates

def fetch_hierarchy(self, taxon_id: int) -> TaxonomicHierarchy:
    """
    Fetch complete taxonomic hierarchy for a taxon.
    """
    query = """
        SELECT 
            t.taxon_id,
            t.species,
            g.genus_id, g.genus_name,
            f.family_id, f.family_name,
            o.order_id, o.order_name,
            a.author_id, a.author_name
        FROM public.tbl_taxa_tree_master t
        LEFT JOIN public.tbl_taxa_tree_genera g USING (genus_id)
        LEFT JOIN public.tbl_taxa_tree_families f USING (family_id)
        LEFT JOIN public.tbl_taxa_tree_orders o USING (order_id)
        LEFT JOIN public.tbl_taxa_tree_authors a USING (author_id)
        WHERE t.taxon_id = $1
    """
    # Execute and return hierarchy object
```

---

## Multi-Column Input Support

### Structured Input

For datasets with separate columns:

```python
async def reconcile_structured(self, 
                                genus: str = None, 
                                species: str = None, 
                                author: str = None,
                                qualifier: str = None,
                                limit: int = 10) -> List[Candidate]:
    """
    Reconcile from structured input (multiple columns).
    """
    # Build query string
    parts = []
    if genus:
        parts.append(genus)
    if species and species not in ['sp.', 'spp.', 'indet.']:
        parts.append(species)
    if qualifier:
        parts.insert(1, qualifier)  # Insert between genus and species
    
    query = ' '.join(parts)
    
    # Use standard reconciliation
    return await self.reconcile(query, limit)
```

### OpenRefine Query Format

OpenRefine can send structured queries:

```json
{
  "query": "Acer platanoides",
  "properties": [
    {"pid": "genus", "v": "Acer"},
    {"pid": "species", "v": "platanoides"},
    {"pid": "author", "v": "L."},
    {"pid": "qualifier", "v": null}
  ]
}
```

Handle this in the reconciliation endpoint:

```python
@router.post("/reconcile/taxa")
async def reconcile_taxa(request: ReconcileRequest):
    if request.properties:
        # Extract structured properties
        genus = get_property(request.properties, 'genus')
        species = get_property(request.properties, 'species')
        author = get_property(request.properties, 'author')
        qualifier = get_property(request.properties, 'qualifier')
        
        return await taxa_strategy.reconcile_structured(
            genus=genus, 
            species=species, 
            author=author, 
            qualifier=qualifier,
            limit=request.limit
        )
    else:
        # Use query string
        return await taxa_strategy.reconcile(request.query, request.limit)
```

---

## Response Format

### Enriched Candidate Response

```json
{
  "result": [
    {
      "id": "taxon:5",
      "name": "Acer platanoides L.",
      "type": [{"id": "taxa_species", "name": "Taxon (Species)"}],
      "score": 0.98,
      "match": true,
      "metadata": {
        "taxon_id": 5,
        "genus": "Acer",
        "genus_id": 3,
        "species": "platanoides",
        "author": "L.",
        "author_id": 2,
        "family": "Aceraceae",
        "family_id": 3,
        "order": "Sapindales",
        "order_id": 2,
        "rank": "species",
        "matched_at": "species",
        "uncertainty": null,
        "full_name": "Acer platanoides L."
      }
    },
    {
      "id": "taxon:6",
      "name": "Acer pseudoplatanus L.",
      "type": [{"id": "taxa_species", "name": "Taxon (Species)"}],
      "score": 0.82,
      "match": false,
      "metadata": {
        "taxon_id": 6,
        "genus": "Acer",
        "genus_id": 3,
        "species": "pseudoplatanus",
        "author": "L.",
        "author_id": 2,
        "family": "Aceraceae",
        "family_id": 3,
        "order": "Sapindales",
        "order_id": 2,
        "rank": "species",
        "matched_at": "species",
        "uncertainty": null,
        "full_name": "Acer pseudoplatanus L."
      }
    }
  ]
}
```

---

## Implementation Phases

### Phase 1: Basic Entity Endpoints (Week 1-2)
- ✅ Create 5 entity-level strategies (author, order, family, genus, species)
- ✅ Deploy individual `/reconcile/{entity}` endpoints
- ✅ Test with simple queries in OpenRefine

### Phase 2: Parsing & Classification (Week 3)
- Implement taxonomic string parser
- Add uncertainty indicator detection
- Create taxonomic level classifier

### Phase 3: Orchestration Strategy (Week 4)
- Implement `TaxaReconciliationStrategy`
- Add hierarchical validation
- Support cascading fallback

### Phase 4: Structured Input (Week 5)
- Support multi-column input
- Handle OpenRefine `properties` parameter
- Add validation for structured queries

### Phase 5: Testing & Refinement (Week 6)
- Test with real SEAD data
- Tune hybrid search parameters (alpha, k_trgm, k_sem)
- Evaluate recall/precision on test dataset
- Document edge cases

---

## Special Cases & Edge Cases

### 1. Split Identifications
**Example**: "Salix/Populus" (could be either genus)

**Strategy**: Return candidates from both genera, mark as split:
```python
if '/' in parsed.genus:
    genera = parsed.genus.split('/')
    all_candidates = []
    for genus in genera:
        candidates = await self.genus_strategy.reconcile(genus, limit//2)
        for c in candidates:
            c.metadata['split_identification'] = parsed.genus
        all_candidates.extend(candidates)
    return sorted(all_candidates, key=lambda c: c.match_score, reverse=True)[:limit]
```

### 2. Subspecies & Varieties
**Example**: "Acer tataricum ssp ginnala"

**Strategy**: Already in `tbl_taxa_tree_master` with full string in `species` field. Hybrid search handles this naturally.

### 3. Author Citations
**Example**: "(Siebold & Zucc.) Planch. ex Miq."

**Strategy**: 
- Parse and separate from species
- Match author separately using `taxa_author` strategy
- Use for validation but not primary matching

### 4. Fossil Taxa
**Example**: "Betula (fossil)"

**Strategy**: Handle parenthetical notes, store in metadata

### 5. Aggregate Taxa
**Example**: "Coleoptera indet." (Order level, indeterminate species)

**Strategy**: Match at order level, mark as indeterminate

---

## Database Queries for Enrichment

### Fetch Complete Hierarchy

```sql
-- Get full taxonomic hierarchy for a taxon
SELECT 
    t.taxon_id,
    CONCAT(g.genus_name, ' ', t.species) AS full_name,
    t.species,
    g.genus_id,
    g.genus_name,
    f.family_id,
    f.family_name,
    o.order_id,
    o.order_name,
    a.author_id,
    a.author_name,
    t.species LIKE '%sp.%' OR t.species LIKE '%spp.%' AS is_genus_level
FROM public.tbl_taxa_tree_master t
LEFT JOIN public.tbl_taxa_tree_genera g USING (genus_id)
LEFT JOIN public.tbl_taxa_tree_families f USING (family_id)
LEFT JOIN public.tbl_taxa_tree_orders o USING (order_id)
LEFT JOIN public.tbl_taxa_tree_authors a USING (author_id)
WHERE t.taxon_id = ?;
```

### Find Related Taxa

```sql
-- Find all species in same genus
SELECT 
    t.taxon_id,
    CONCAT(g.genus_name, ' ', t.species) AS full_name
FROM public.tbl_taxa_tree_master t
JOIN public.tbl_taxa_tree_genera g USING (genus_id)
WHERE g.genus_id = ?
ORDER BY t.species;
```

---

## Performance Considerations

### Caching Strategy

Cache parsed taxonomic strings and hierarchies:

```python
@lru_cache(maxsize=10000)
def parse_taxonomic_string(self, query: str) -> TaxonomicParsed:
    # Parsing logic...

@lru_cache(maxsize=5000)
def fetch_hierarchy(self, taxon_id: int) -> TaxonomicHierarchy:
    # Hierarchy query...
```

### Query Optimization

- Use materialized views for frequently accessed hierarchies
- Precompute full taxonomic names in `taxa_tree_master` view
- Index on `(genus_id, species)` for fast lookups

---

## Testing Strategy

### Test Cases

1. **Exact matches**: "Acer platanoides L." → taxon_id=5
2. **Genus only**: "Acer" → genus_id=3
3. **Genus sp.**: "Acer sp." → genus_id=3 (genus level)
4. **Uncertain**: "Quercus cf. robur" → candidates with uncertainty flag
5. **Split**: "Salix/Populus" → candidates from both genera
6. **Misspellings**: "Acer platnoides" → fuzzy match to "Acer platanoides"
7. **Incomplete**: "A. platanoides" → abbreviation handling
8. **Family level**: "Rosaceae" → family_id=X
9. **Order level**: "Coleoptera" → order_id=X

### Evaluation Metrics

- **Recall@5**: Correct taxon in top 5 candidates
- **Recall@10**: Correct taxon in top 10 candidates
- **MRR (Mean Reciprocal Rank)**: Average position of correct match
- **Match rate**: % of queries with match score >0.8

---

## Summary

### Key Components

1. **5 Entity-Level Strategies**: author, order, family, genus, species
2. **Orchestrated Strategy**: `TaxaReconciliationStrategy` with parsing, classification, validation
3. **Uncertainty Handling**: cf., aff., ?, sp., spp., split identifications
4. **Hierarchical Validation**: Genus → Family → Order consistency
5. **Multi-Input Support**: Single-column text or structured multi-column
6. **Fallback Mechanism**: Species → Genus → Family → Order

### Benefits

- **Flexible**: Handles various input formats and identification levels
- **Robust**: Manages uncertainty and edge cases
- **Accurate**: Hybrid search + hierarchical validation
- **Fast**: Cached parsing, optimized queries
- **User-Friendly**: Clear metadata about match level and uncertainty

This strategy provides a solid foundation for reconciling taxonomic data in SEAD, balancing complexity with usability.
