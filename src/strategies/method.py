# from src.utility import load_resource_yaml
from .query import BaseRepository
from .rag_hybrid.rag_hybrid_strategy import RAGHybridReconciliationStrategy
from .strategy import ReconciliationStrategy, Strategies, StrategySpecification

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


class MethodRepository(BaseRepository):
    """Method-specific query proxy"""


@Strategies.register(key="method", repository_cls=MethodRepository)
class MethodReconciliationStrategy(ReconciliationStrategy):
    """Method-specific reconciliation with place names and coordinates"""
    def __init__(self, specification: StrategySpecification | None = None, repository_or_cls: type[BaseRepository] | BaseRepository | None = None) -> None:
        super().__init__(specification=specification, repository_or_cls=repository_or_cls)


@Strategies.register(key="rag_methods", repository_cls=MethodRepository)
class RAGMethodsReconciliationStrategy(RAGHybridReconciliationStrategy):

    def __init__(self):
        super().__init__(RAG_SPECIFICATION, self.repository_cls)
