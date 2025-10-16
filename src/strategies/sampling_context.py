from .query import DatabaseQueryProxy
from .strategy import ReconciliationStrategy, Strategies, StrategySpecification

SPECIFICATION: StrategySpecification = {
    "key": "sampling_context",
    "display_name": "Sampling Contexts",
    "id_field": "sampling_context_id",
    "label_field": "label",
    "properties": [],
    "property_settings": {},
    "sql_queries": {
        "fuzzy_label_sql": """
            select
                s.sampling_context_id,
                s.sampling_context as label,
                greatest(
                    case when s.norm_label = pq.q then 1.0 else similarity(s.norm_label, pq.q) end,
                    0.0001
                ) as name_sim
            from (
                select sampling_context_id,
                    sampling_context,
                    authority.immutable_unaccent(lower(sampling_context))::text as norm_label
                from tbl_sample_group_sampling_contexts
            ) as s
            cross join (
                select authority.immutable_unaccent(lower(%(q)s))::text as q
            ) as pq
            where s.norm_label %% pq.q
            order by name_sim desc, 2
            limit %(n)s;
    """,
        "get_details": """
            select sampling_context_id as "ID",
                sampling_context as "Name",
                description as "Description",
                type_names as "Types"
            from tbl_sample_group_sampling_contexts sgc
            left join (
                select sampling_context_id, '<ul>' || string_agg('<li><strong>' || type_name || '</string>: ' || type_description, e'</li>\n') || '</ul>' as type_names
                from tbl_sample_group_description_type_sampling_contexts 
                join tbl_sample_group_description_types sgdt using (sample_group_description_type_id)
                group by sampling_context_id
            ) using (sampling_context_id)
        where sampling_context_id = %(id)s::int
    """,
    },
}


@Strategies.register(key="sampling_context")
class SamplingContextReconciliationStrategy(ReconciliationStrategy):
    """Sampling Context-specific reconciliation with sampling context names and descriptions"""

    def __init__(self, specification: StrategySpecification = None) -> None:
        specification = specification or SPECIFICATION
        super().__init__(specification, DatabaseQueryProxy)
