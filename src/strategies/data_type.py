from .query import DatabaseQueryProxy
from .strategy import ReconciliationStrategy, Strategies, StrategySpecification

SPECIFICATION: StrategySpecification = {
    "key": "data_type",
    "display_name": "Data Types",
    "id_field": "data_type_id",
    "label_field": "label",
    "properties": [],
    "property_settings": {},
    "sql_queries": {
        "fuzzy_find_sql": """
            select
                s.data_type_id,
                s.data_type_name as label,
                greatest(
                    case when s.norm_label = pq.q then 1.0 else similarity(s.norm_label, pq.q) end,
                    0.0001
                ) as name_sim
            from (
                select data_type_id,
                        data_type_name,
                        authority.immutable_unaccent(lower(data_type_name))::text as norm_label
                from tbl_data_types
            ) as s
            cross join (
                select authority.immutable_unaccent(lower(%(q)s))::text as q
            ) as pq
            where s.norm_label %% pq.q
            order by name_sim desc, 2
            limit %(n)s;
    """,
        "details_sql": """
            select dt.data_type_id as "ID",
                   dt.label as "Name",
                   dt.description as "Description",
                   dt.definition as "Definition",
                   dtg.data_type_group_name as "Group",
                   dtg.description as "Group Description"
            from authority.data_types dt
            join tbl_data_type_groups dtg using (data_type_group_id)
            where data_type_id = %(id)s::int
    """,
    },
}


class DataTypeQueryProxy(DatabaseQueryProxy):
    """Data Type-specific query proxy"""


@Strategies.register(key="data_type")
class DataTypeReconciliationStrategy(ReconciliationStrategy):
    """Data Type-specific reconciliation with data type names and descriptions"""

    def __init__(self, specification: StrategySpecification | None = None) -> None:
        super().__init__(specification or SPECIFICATION, DataTypeQueryProxy)
