
/**********************************************************/

select *
from authority.fuzzy_find_entity_type_candidates('burial ground', 5);

-- find "träkol" in full text search using fuzzy matching
select *, ts_rank_cd(tsv, plainto_tsquery('english', unaccent(pq.q))) as rank, sead_utility.table_name_to_entity_name(table_name) as entity_name
from sead_utility.full_text_search
cross join (
    select authority.immutable_unaccent(lower('Pithole'))::text as q
) as pq
--where value % pq.q
where value::tsvector @@ to_tsquery('Pithole')
order by ts_rank_cd(tsv, plainto_tsquery('english', unaccent(pq.q))) desc
limit 20;

select *, sead_utility.table_name_to_entity_name(table_name) as entity_name
from sead_utility.full_text_search
cross join (
    select plainto_tsquery('insect') as q, authority.immutable_unaccent(:user_query) as uq
) as pq
where tsv @@ pq.q
limit 20;

select * from sead_utility.full_text_search

-- Fuzzy full text search threshold tuning:
/*
SHOW pg_trgm.similarity_threshold;
SET pg_trgm.similarity_threshold = 0.25;
| Method                              | Description                          | Strengths                              | Weaknesses                                                        |
| ----------------------------------- | ------------------------------------ | -------------------------------------- | ----------------------------------------------------------------- |
| **`%` (trigram)**                   | Boolean fuzzy match using `pg_trgm`  | Fast, indexable, tunable               | Threshold-based (no numeric result unless you use `similarity()`) |
| **`similarity(a,b)`**               | Returns float 0–1                    | Precise scoring, rank results          | Slower if no index, you must filter manually                      |
| **`<->`**                           | “Distance” operator (1 − similarity) | Works for `ORDER BY value <-> 'query'` | Threshold must be applied separately                              |
| **`ILIKE`**                         | Case-insensitive substring           | Simple, deterministic                  | No fuzziness, no index use (usually)                              |
| **`Levenshtein(a,b)`**              | Edit distance from `fuzzystrmatch`   | Exact edit count                       | No index support, slower for big datasets                         |
| **`dmetaphone(a) = dmetaphone(b)`** | Phonetic match (`fuzzystrmatch`)     | Good for names/speech                  | Not useful for general text                                       |
| **`to_tsvector @@ to_tsquery`**     | Full-text search                     | Semantic/stem-based                    | No typo tolerance                                                 |

| Operator | Meaning                   | Typical use                     |
| -------- | ------------------------- | ------------------------------- |
| `%`      | fuzzy match (basic)       | general-purpose fuzzy search    |
| `<->`    | similarity distance       | ranking / ordering              |
| `<%>`    | fuzzy match at word level | matching subwords in long text  |
| `<<%>>`  | strict word fuzzy match   | when words must match exactly   |
| `<<->`   | word-level distance       | ranking for token-level matches |
| `<<<->`  | strict word distance      | ranking stricter matches        |
| Function                                 | Description                                                                                          | Return type | Example                                                                    | Notes                            |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------- | ----------- | -------------------------------------------------------------------------- | -------------------------------- |
| **`similarity(text, text)`**             | Returns a number between **0 and 1** showing how similar two strings are (based on trigram overlap). | `float4`    | `SELECT similarity('cat', 'cats');` → `0.75`                               | Used for ranking.                |
| **`show_trgm(text)`**                    | Returns the set of trigrams (three-character sequences) that make up the text.                       | `text[]`    | `SELECT show_trgm('pithole');` → `{  p, pi, pit, ith, tho, hol, ole, le }` | Diagnostic tool.                 |
| **`word_similarity(text, text)`**        | Measures trigram similarity between words within the two strings.                                    | `float4`    | `SELECT word_similarity('postgres', 'postgreSQL database');`               | Focuses on word boundaries.      |
| **`strict_word_similarity(text, text)`** | Like `word_similarity` but requires entire words to match.                                           | `float4`    |                                                                            | Useful for token-aware matching. |
| **`word_similarity_op(text, text)`**     | Same as `word_similarity`, used internally by `<%%>` operator.                                       | `float4`    |                                                                            | Normally not called directly.    |
| Category                   | Function / Operator                         | Output         | Indexed | Notes                   |
| -------------------------- | ------------------------------------------- | -------------- | ------- | ----------------------- |
| **Similarity**             | `similarity(a,b)`                           | Float 0–1      | ✅       | core measure            |
| **Boolean fuzzy**          | `%`                                         | Boolean        | ✅       | default threshold       |
| **Distance**               | `<->`                                       | Float distance | ✅       | use for ORDER BY        |
| **Word similarity**        | `word_similarity(a,b)`                      | Float 0–1      | ✅       | word-based              |
| **Strict word similarity** | `strict_word_similarity(a,b)`               | Float 0–1      | ✅       | stricter token match    |
| **Word boolean fuzzy**     | `<%>`, `<<%>>`                              | Boolean        | ✅       | word-level thresholds   |
| **Word distance**          | `<<->`, `<<<->`                             | Float          | ✅       | word-level ORDER BY     |
| **Debugging**              | `show_trgm(a)`                              | Text array     | ❌       | reveals actual trigrams |
| **Tuning**                 | `SET pg_trgm.similarity_threshold = n`      | —              | —       | affects `%` ops         |
| **Tuning (word)**          | `SET pg_trgm.word_similarity_threshold = n` | —              | —       | affects word ops        |
*/


with params as (
  select 'brandgrav'::text as q,
         websearch_to_tsquery('simple', 'brandgrav') as tsq
)
select
  t.table_name,
  -- take the best fts score among that table's rows (only when fts matched)
  coalesce(max(ts_rank_cd(t.tsv, p.tsq)) filter (where t.tsv @@ p.tsq), 0) as fts_rank,
  -- best trigram similarity among that table's rows (only when trigram matched)
  coalesce(max(similarity(t.value_norm, p.q)) filter (where t.value_norm % p.q), 0) as trigram_sim,
  -- combined score: weight fts higher than trigram fuzziness
  (coalesce(max(ts_rank_cd(t.tsv, p.tsq)) filter (where t.tsv @@ p.tsq), 0)
   + 0.35 * coalesce(max(similarity(t.value_norm, p.q)) filter (where t.value_norm % p.q), 0)
  ) as score
from sead_utility.full_text_search t
cross join params p
where t.tsv @@ p.tsq
   or t.value_norm % p.q
group by t.table_name
order by score desc
limit 5;

select * from sead_utility.full_text_search
where table_name = 'tbl_taxa_tree_master'

drop function authority.fuzzy_find_entity_type_candidates( p_text text, p_limit integer);
