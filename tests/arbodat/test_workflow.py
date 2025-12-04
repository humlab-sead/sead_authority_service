import asyncio
import os
import shutil

from src.arbodat.survey2excel import workflow
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
            verbose=False,
            translate=translate,
            mode="csv",
            drop_foreign_keys=False,
        )
    )

    assert os.path.exists(output_path)
