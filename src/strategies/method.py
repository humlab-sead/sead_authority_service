# from src.utility import load_resource_yaml
from .query import DatabaseQueryProxy
from .rag_hybrid.rag_hybrid_strategy import RAGHybridReconciliationStrategy
from .strategy import ReconciliationStrategy, Strategies, StrategySpecification

SPECIFICATION: StrategySpecification = {
    "key": "method",
    "display_name": "Methods",
    "id_field": "method_id",
    "label_field": "label",
    "alternate_identity_field": "method_abbreviation",
    "properties": [
        {
            "id": "method_abbreviation",
            "name": "Method Abbreviation",
            "type": "string",
            "description": "Abbreviation for the method used",
        }
    ],
    "property_settings": {},
    "sql_queries": {
        "fuzzy_label_sql": """
        select * from authority.methods(%(q)s, %(n)s);
    """,
        "details_sql": """
            select
                m.method_id as "ID",
                m.method_name as "Name",
                m.description as "Description",
                m.method_abbrev_or_alt_name as "Abbreviation",
                mg.group_name as "Group",
                mg.description as "Group Description"
            from tbl_methods as m
            join tbl_method_groups mg using (method_group_id)
            where method_id = %(id)s
    """,
        "alternate_identity_sql": """
        select method_id, label, 1.0 as name_sim
        from authority.methods
        where method_abbrev_or_alt_name = %(alternate_identity)s
        limit 1
    """,
    },
}

RAG_SPECIFICATION: StrategySpecification = {
    "key": "method (rag hybrid)",
    "display_name": "Methods (RAG Hybrid)",
    "id_field": "method_id",
    "label_field": "label",
    "alternate_identity_field": "method_abbreviation",
    "properties": [],
    "property_settings": {},
    "sql_queries": {},
}


class MethodQueryProxy(DatabaseQueryProxy):
    """Method-specific query proxy"""


@Strategies.register(key="method")
class MethodReconciliationStrategy(ReconciliationStrategy):
    """Method-specific reconciliation with place names and coordinates"""

    def __init__(self) -> None:
        super().__init__(SPECIFICATION, MethodQueryProxy)


@Strategies.register(key="rag_methods")
class RAGMethodsReconciliationStrategy(RAGHybridReconciliationStrategy):
    def __init__(self):
        super().__init__(RAG_SPECIFICATION, MethodQueryProxy)
