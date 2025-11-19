#!/usr/bin/env python3
"""
Populate embedding tables for SEAD authority entities using Ollama nomic-embed-text.

This script reads config/entities.yml to discover entities with embedding_config,
then efficiently generates and stores embeddings in the corresponding authority.*_embeddings tables.

Performance optimizations:
- Batch text collection from database
- Batch embedding generation via Ollama API
- Batch upsert to embedding tables
- Progress reporting and error handling
- Concurrent processing for multiple entities

Usage:
    python src/scripts/populate_embeddings.py [OPTIONS]

Options:
    --entity TEXT               Process only this entity (e.g., 'bibliographic_reference')
    --batch-size INTEGER        Number of texts to embed per batch (default: 50)
    --force                     Regenerate all embeddings (default: only missing)
    --ollama-host TEXT          Ollama server URL (default: http://localhost:11434)
    --db-url TEXT               Database connection URL (reads from .env if not provided)
    --workers INTEGER           Number of concurrent entity workers (default: 4)
    --help                      Show this message and exit
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

import click
from configuration.interface import ConfigLike
from configuration.provider import ConfigStore, get_config_provider
from configuration.resolve import ConfigValue
import ollama
import psycopg
from utility import configure_logging, create_db_uri
import yaml
from dotenv import load_dotenv
from loguru import logger

from src.configuration import setup_config_store

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class EmbeddingPopulator:
    """Efficiently populate embeddings for SEAD authority entities."""

    def __init__(
        self,
        db_url: str,
        ollama_host: str = "http://localhost:11434",
        batch_size: int = 50,
        force: bool = False,
    ):
        self.db_url: str = db_url
        self.ollama_host: str = ollama_host
        self.batch_size: int = batch_size
        self.force: bool = force
        self.ollama_client = ollama.Client(host=ollama_host)
        self.model: str = "nomic-embed-text"

    def load_entities(self) -> dict[str, Any]:
        """Load entity configuration from YAML."""
        entities = get_config_provider().get_config().get('table_specs')
        return {k: v for k, v in entities.items() if v and v.get("embedding_config")}

    def construct_text_field(self, entity_config: dict[str, Any]) -> str:
        """
        Construct SQL expression for text to embed based on entity config.

        Combines label_column and description_column following the same logic
        as the generated SQL update procedures.
        """
        label_column: str = entity_config["label_column"]
        desc_column: str | None = entity_config.get("description_column")

        if desc_column:
            return f"t.{label_column} || coalesce(' ' || t.{desc_column}, '')"
        return f"t.{label_column}"

    def fetch_texts_to_embed(
        self, conn: psycopg.Connection, entity_key: str, entity_config: dict[str, Any]
    ) -> list[tuple[int, str]]:
        """
        Fetch texts that need embeddings from the database.

        Returns list of (id, text) tuples for rows missing embeddings or when force=True.
        """
        table_name: str = entity_config["table_name"]
        id_column: str = entity_config["id_column"]
        text_expr: str = self.construct_text_field(entity_config)
        embeddings_table: str = f"authority.{entity_key}_embeddings"

        where_clause: str = (
            f"where not exists (select 1 from {embeddings_table} e where e.{id_column} = t.{id_column})"
            if not self.force
            else ""
        )

        query: str = f"""
            select t.{id_column} as id, {text_expr} as text
            from public.{table_name} t
            {where_clause}
            order by t.{id_column}
        """

        with conn.cursor() as cur:
            cur.execute(query)  # type: ignore
            return [(row[0], row[1]) for row in cur.fetchall()]

    def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts using Ollama.

        Returns list of embedding vectors in same order as input texts.
        """
        embeddings: list[list[float]] = []
        for text in texts:
            try:
                response: ollama.EmbeddingsResponse = self.ollama_client.embeddings(model=self.model, prompt=text)
                embeddings.append(response["embedding"])
            except Exception as e:
                logger.error(f"Failed to generate embedding for text '{text[:50]}...': {e}")
                # Return zero vector on error to maintain batch alignment
                embeddings.append([0.0] * 768)
        return embeddings

    def upsert_embeddings_batch(
        self,
        conn: psycopg.Connection,
        entity_key: str,
        id_column: str,
        batch: list[tuple[int, list[float]]],
    ) -> int:
        """
        Upsert a batch of embeddings into the entity's embedding table.

        Returns number of rows inserted/updated.
        """
        embeddings_table: str = f"authority.{entity_key}_embeddings"

        with conn.cursor() as cur:
            # Use COPY for fast bulk insert, then handle conflicts
            insert_sql: str = f"""
                insert into {embeddings_table} ({id_column}, emb)
                    values (%s, %s::vector)
                on conflict ({id_column}) do update
                    set emb = excluded.emb
            """
            cur.executemany(insert_sql, [(id_val, emb) for id_val, emb in batch])  # type: ignore
            conn.commit()
            return len(batch)

    def populate_entity(self, entity_key: str, entity_config: dict[str, Any]) -> int:
        """
        Populate embeddings for a single entity.

        Returns total number of embeddings generated.
        """
        logger.info(f"Processing entity: {entity_config['name']} ({entity_key})")

        try:
            with psycopg.connect(self.db_url) as conn:
                # Fetch all texts needing embeddings
                texts_to_embed: list[tuple[int, str]] = self.fetch_texts_to_embed(conn, entity_key, entity_config)

                if not texts_to_embed:
                    logger.info(f"  ✓ No embeddings needed for {entity_key}")
                    return 0

                total: int = len(texts_to_embed)
                logger.info(f"  → Processing {total} rows for {entity_key}")

                total_processed: int = 0
                id_column: str = entity_config["id_column"]

                # Process in batches
                for i in range(0, total, self.batch_size):
                    batch: list[tuple[int, str]] = texts_to_embed[i : i + self.batch_size]
                    batch_ids: list[int] = [id_val for id_val, _ in batch]
                    batch_texts: list[str] = [text for _, text in batch]

                    # Generate embeddings
                    embeddings: list[list[float]] = self.generate_embeddings_batch(batch_texts)

                    # Upsert to database
                    batch_data: list[tuple[int, list[float]]] = list(zip(batch_ids, embeddings))
                    rows_updated: int = self.upsert_embeddings_batch(conn, entity_key, id_column, batch_data)

                    total_processed += rows_updated

                    if total_processed % 100 == 0 or total_processed == total:
                        logger.info(f"  → Processed {total_processed}/{total} rows for {entity_key}")

                logger.success(f"  ✓ Completed {entity_key}: {total_processed} embeddings generated")
                return total_processed

        except Exception as e:
            logger.error(f"  ✗ Failed to process {entity_key}: {e}")
            return 0

    async def populate_entity_async(self, entity_key: str, entity_config: dict[str, Any]) -> int:
        """Async wrapper for populate_entity to enable concurrent processing."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.populate_entity, entity_key, entity_config)

    async def populate_all_entities(
        self, entities: dict[str, Any], workers: int = 4, target_entity: str | None = None
    ) -> dict[str, int]:
        """
        Populate embeddings for all entities (or single entity if specified).

        Uses asyncio to process multiple entities concurrently while respecting worker limit.

        Returns dict mapping entity_key -> number of embeddings generated.
        """
        if target_entity:
            if target_entity not in entities:
                logger.error(f"Entity '{target_entity}' not found in config or has no embedding_config")
                return {}
            entities = {target_entity: entities[target_entity]}

        semaphore = asyncio.Semaphore(workers)

        async def process_with_semaphore(entity_key: str, entity_config: dict[str, Any]) -> tuple[str, int]:
            async with semaphore:
                count: int = await self.populate_entity_async(entity_key, entity_config)
                return entity_key, count

        tasks = [process_with_semaphore(k, v) for k, v in entities.items()]
        results: list[tuple[str, int]] = await asyncio.gather(*tasks)
        return dict(results)


def setup_config_store2(filename: str = "config.yml", force: bool = False) -> None:

    config_file: str = os.getenv("CONFIG_FILE", filename)
    store: ConfigStore = ConfigStore.get_instance()

    if store.is_configured() and not force:
        return

    store.configure_context(source=config_file, env_filename=".env", env_prefix="SEAD_AUTHORITY")

    assert store.is_configured(), "Config Store failed to configure properly"

    cfg: ConfigLike | None = store.config()
    if not cfg:
        raise ValueError("Config Store did not return a config")

    cfg.update({"runtime:config_file": config_file})


    logger.info("Config Store initialized successfully.")

@click.command()
@click.argument("config_filename", type=str)
@click.option("--entity", default=None, help="Process only this entity (e.g., 'bibliographic_reference')")
@click.option("--batch-size", default=50, help="Number of texts to embed per batch")
@click.option("--force", is_flag=True, help="Regenerate all embeddings (default: only missing)")
@click.option("--ollama-host", default=None, help="Ollama server URL")
@click.option("--db-url", default=None, help="Database connection URL (reads from .env if not provided)")
@click.option("--workers", default=4, help="Number of concurrent entity workers")
def main(
    config_filename: str,
    entity: str | None,
    batch_size: int,
    force: bool,
    ollama_host: str,
    db_url: str | None,
    workers: int,
):
    """Populate embedding tables for SEAD authority entities using Ollama nomic-embed-text."""

    # Load environment variables
    load_dotenv()

    setup_config_store2(filename=config_filename)
    configure_logging()

    db_url = db_url or create_db_uri(**ConfigValue(key="options:database").resolve())  #  type: ignore
    ollama_host = ollama_host or ConfigValue(key="llm.ollama.host").resolve() or ""

    logger.info(f"using Ollama host: {ollama_host}")
    logger.info(f"using Database URL: {db_url}")

    # Configure logger
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    populator = EmbeddingPopulator(db_url=db_url, ollama_host=ollama_host, batch_size=batch_size, force=force)

    entities: dict[str, Any] = populator.load_entities()

    logger.info(
        f"Starting embedding population: {len(entities)} entities, "
        f"batch_size={batch_size}, force={force}, workers={workers}"
    )

    # Run async population
    results: dict[str, int] = asyncio.run(populator.populate_all_entities(entities, workers=workers, target_entity=entity))

    # Summary
    total_embeddings = sum(results.values())
    logger.success(f"\n✓ Completed: {total_embeddings} total embeddings generated across {len(results)} entities")

    for entity_key, count in sorted(results.items()):
        if count > 0:
            logger.info(f"  {entity_key}: {count} embeddings")


if __name__ == "__main__":
    # main()
    from click.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(main, ["--entity", "feature_type", '--force', '--batch-size', "1", 'config/config.yml'])

    print(result.output)