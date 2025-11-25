import asyncio
import os
from src.arbodat.workflow import workflow
from src.configuration.setup import setup_config_store

def test_workflow():

    config_file: str = "src/arbodat/config.yml"

    asyncio.run(setup_config_store(config_file))

    if os.path.exists("output.xlsx"):
        os.remove("output.xlsx")
        
    assert not os.path.exists("output.xlsx")
    workflow(
        input_csv="src/arbodat/input/arbodat_mal_elena_input.csv",
        target="output.xlsx",
        sep=";",
        verbose=False,
        translate=False,
        mode="xlsx",
        drop_foreign_keys=False,
    )

    assert os.path.exists("output.xlsx")