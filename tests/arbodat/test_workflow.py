import asyncio
import os

from src.arbodat.survey2excel import workflow
from src.configuration.setup import setup_config_store


def test_workflow():

    config_file: str = "src/arbodat/input/arbodat.yml"
    translate: bool = False

    output_filename: str = f"output{'' if not translate else '_translated'}.xlsx"
    asyncio.run(setup_config_store(config_file))

    if os.path.exists(output_filename):
        os.remove(output_filename)

    assert not os.path.exists(output_filename)
    workflow(
        input_csv="src/arbodat/input/arbodat_mal_elena_input.csv",
        target=output_filename,
        sep=";",
        verbose=False,
        translate=translate,
        mode="xlsx",
        drop_foreign_keys=False,
    )

    assert os.path.exists(output_filename)
