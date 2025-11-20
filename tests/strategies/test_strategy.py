from typing import Any, Type

import pytest

from src.strategies.strategy import ReconciliationStrategy, Strategies
from strategies import strategy
from tests.conftest import ExtendedMockConfigProvider
from tests.decorators import with_test_config

# pylint: disable=attribute-defined-outside-init,protected-access, unused-argument


class TestMultipleReconciliationStrategy:

    @pytest.mark.parametrize(
        "strategy_class",
        [strategy_cls for strategy_cls in Strategies.items.values()],
    )
    @pytest.mark.asyncio
    @with_test_config
    async def test_reconciliation_strategy(
        self,
        strategy_class: Type[ReconciliationStrategy],
        test_provider: ExtendedMockConfigProvider,
    ) -> None:
        """Test reconciliation strategy."""

        strategy = strategy_class()

        if strategy_class.__name__.split(".")[-1] in [
            "GeoNamesReconciliationStrategy",
            "BibliographicReferenceReconciliationStrategy",
            "RAGMethodsReconciliationStrategy",
            "TaxonReconciliationStrategy",
        ]:
            return

        key: str = strategy.specification.get("key", "unknown")
        id_field: str = strategy.specification.get("id_field", "id")

        assert key == strategy.key
        assert strategy.get_entity_id_field() == id_field
        assert strategy.get_label_field() == strategy.specification.get("label_field", "name")

        mock_rows = [
            {id_field: 1, "label": f"Test {key.capitalize()} 1", "name_sim": 0.9},
            {id_field: 2, "label": f"Test {key.capitalize()} 2", "name_sim": 0.8},
        ]

        test_provider.create_connection_mock(fetchall=mock_rows, execute=None)

        result: list[dict[str, Any]] = await strategy.find_candidates(f"Hej {key}", limit=5)

        test_provider.connection_mock.cursor_instance.execute.assert_called()
        test_provider.connection_mock.cursor_instance.fetchall.assert_called()
        assert result == mock_rows
