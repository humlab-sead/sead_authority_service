import asyncio
import os
import shutil
from typing import Any

import pandas as pd

from src.arbodat.survey2excel import workflow
from src.configuration.resolve import ConfigValue
from src.configuration.setup import setup_config_store

# def test_workflow():

#     config_file: str = "src/arbodat/input/arbodat.yml"
#     translate: bool = False

#     output_filename: str = f"output{'' if not translate else '_translated'}.xlsx"
#     asyncio.run(
#         setup_config_store(
#             config_file,
#             env_prefix="SEAD_NORMALIZER",
#             env_filename="src/arbodat/input/.env",
#             db_opts_path=None,
#         )
#     )
#     asyncio.sleep(0.1)  # type: ignore ; ensure config is fully loaded;
#     if os.path.exists(output_filename):
#         os.remove(output_filename)

#     assert not os.path.exists(output_filename)
#     asyncio.run(
#         workflow(
#             input_csv="src/arbodat/input/arbodat_mal_elena_input.csv",
#             target=output_filename,
#             sep=";",
#             verbose=False,
#             translate=translate,
#             mode="xlsx",
#             drop_foreign_keys=False,
#         )
#     )

#     assert os.path.exists(output_filename)

EXPECTED_FILE_SHEETS = {
    "site": {
        "filename": "site.csv",
        "expected_rows": 7,
        "expected_columns": 10,
    }
}


def test_csv_workflow():

    config_file: str = "src/arbodat/input/arbodat.yml"
    translate: bool = False

    output_path: str = "tmp/arbodat/"
    asyncio.run(
        setup_config_store(
            config_file,
            env_prefix="SEAD_NORMALIZER",
            env_filename="src/arbodat/input/.env",
            db_opts_path=None,
        )
    )
    asyncio.run(asyncio.sleep(0.1))  # type: ignore ; ensure config is fully loaded;

    if os.path.exists(output_path):
        shutil.rmtree(output_path, ignore_errors=True)

    assert not os.path.exists(output_path)

    asyncio.run(
        workflow(
            input_csv="src/arbodat/input/arbodat_mal_elena_input.csv",
            target=output_path,
            sep=";",
            verbose=True,
            translate=translate,
            mode="csv",
            drop_foreign_keys=False,
        )
    )

    assert os.path.exists(output_path)

    # Check individual files
    entities: dict[str, Any] | None = ConfigValue("entities").resolve()
    for entity in entities or {}:
        df = pd.read_csv(os.path.join(output_path, f"{entity}.csv"))
        expected_info = EXPECTED_FILE_SHEETS.get(entity, None)
        if expected_info:
            assert df.shape[0] == expected_info["expected_rows"]
            assert df.shape[1] == expected_info["expected_columns"]
