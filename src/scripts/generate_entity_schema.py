#!/usr/bin/env python3
"""
Generate entity-specific SQL schema files from Jinja2 templates

This script reads entity configurations from config/entities.yml and generates
SQL DDL files for embedding tables, views, and search functions.

Usage:
    python src/scripts/generate_entity_schema.py [--entities entity1,entity2,...]
    python src/scripts/generate_entity_schema.py --all
    python src/scripts/generate_entity_schema.py --help

Examples:
    # Generate schema for specific entities
    python src/scripts/generate_entity_schema.py --entities method,site,location

    # Generate schema for all entities with embedding_config
    python src/scripts/generate_entity_schema.py --all

    # Generate only for entities that have changed
    python src/scripts/generate_entity_schema.py
"""

import sys
from pathlib import Path
from typing import Any

import click
import yaml
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound
from loguru import logger


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with loguru"""
    logger.remove()
    log_level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=log_level,
    )


def load_entities_config(config_path: Path) -> dict[str, Any]:
    """Load entities configuration from YAML file"""
    logger.info(f"Loading entities configuration from {config_path}")
    with open(config_path) as f:
        config: dict[str, Any] = yaml.safe_load(f)
    return config


def filter_entities_with_embeddings(entities: dict[str, Any]) -> dict[str, Any]:
    """Filter entities that have embedding_config defined"""
    return {key: entity for key, entity in entities.items() if "embedding_config" in entity and entity["embedding_config"]}


def get_trigram_config(entity: dict[str, Any]) -> dict[str, Any]:
    """Extract trigram-relevant configuration from entity"""
    # All view-related settings now at entity level
    # Only where_clause might still be in embedding_config (rarely used)
    embedding_config = entity.get("embedding_config", {})

    return {
        "materialized": entity.get("materialized", False),
        "extra_columns": entity.get("extra_columns", []),
        "joins": entity.get("joins", []),
        "where_clause": entity.get("where_clause") or embedding_config.get("where_clause"),
        "filter_params": entity.get("filter_params", []),
    }


def generate_trigram_sql(entity_key: str, entity: dict[str, Any], env: Environment, output_dir: Path, force: bool = False) -> None:
    """Generate tri-gram SQL file for a single entity"""
    output_file: Path = output_dir / f"{entity_key}.sql"

    # Skip if file exists and force is False
    if output_file.exists() and not force:
        logger.debug(f"Skipping trigram {entity_key}: {output_file} already exists (use --force to overwrite)")
        return

    try:
        template: Template = env.get_template("entity.sql.jinja2")
    except TemplateNotFound as e:
        logger.error(f"Trigram template not found: {e}")
        raise

    logger.info(f"Generating trigram schema for entity: {entity_key}")
    logger.debug(f"  Entity name: {entity['name']}")
    logger.debug(f"  Table: {entity['table_name']}")
    logger.debug(f"  ID column: {entity['id_column']}")
    logger.debug(f"  Label column: {entity['label_column']}")

    trigram_config = get_trigram_config(entity)
    context: dict[str, Any] = {
        "entity_key": entity_key,
        "entity": entity,
        "trigram_config": trigram_config,
    }

    sql_content = template.render(**context)

    output_file.write_text(sql_content)
    logger.success(f"Generated trigram: {output_file}")


def generate_semantic_sql(entity_key: str, entity: dict[str, Any], env: Environment, output_dir: Path, force: bool = False) -> None:
    """Generate semantic SQL file for a single entity with embeddings"""
    output_file: Path = output_dir / f"semantic-{entity_key}.sql"

    # Skip if file exists and force is False
    if output_file.exists() and not force:
        logger.debug(f"Skipping semantic {entity_key}: {output_file} already exists (use --force to overwrite)")
        return

    try:
        template: Template = env.get_template("semantic-entity.sql.jinja2")
    except TemplateNotFound as e:
        logger.error(f"Semantic template not found: {e}")
        raise

    logger.info(f"Generating semantic schema for entity: {entity_key}")
    logger.debug(f"  Entity name: {entity['name']}")
    logger.debug(f"  Embedding dimension: {entity.get('embedding_config', {}).get('dimension', 768)}")

    context: dict[str, Any] = {
        "entity_key": entity_key,
        "entity": entity,
        "embedding_config": entity.get("embedding_config", {}),
    }

    sql_content = template.render(**context)

    output_file.write_text(sql_content)
    logger.success(f"Generated semantic: {output_file}")


@click.command()
@click.option("--entities", type=str, help="Comma-separated list of entity keys to generate (e.g., method,site,location)")
@click.option("--all", "generate_all", is_flag=True, help="Generate schema for all entities")
@click.option("--force", is_flag=True, help="Force regeneration even if output files exist")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    default=Path("config/entities.yml"),
    help="Path to entities configuration file",
)
@click.option(
    "--template-dir", type=click.Path(exists=True, path_type=Path), default=Path("schema/templates"), help="Path to templates directory"
)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("schema/generated"), help="Path to output directory")
def main(entities: str | None, generate_all: bool, force: bool, verbose: bool, config: Path, template_dir: Path, output_dir: Path) -> None:
    """
    Generate entity-specific SQL schema files from Jinja2 templates.

    This script reads entity configurations from config/entities.yml and generates
    SQL DDL files for:
    - Trigram search (for all entities)
    - Semantic search with embeddings (for entities with embedding_config)

    \b
    Examples:
      # Generate for specific entities
      python src/scripts/generate_entity_schema.py --entities method,site,location

      # Generate for all entities
      python src/scripts/generate_entity_schema.py --all

      # Force regeneration even if files exist
      python src/scripts/generate_entity_schema.py --all --force

      # Verbose output
      python src/scripts/generate_entity_schema.py --all --verbose
    """
    # Setup logging
    setup_logging(verbose)

    # Validate inputs
    if not generate_all and not entities:
        raise click.UsageError("Either --all or --entities must be specified")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Load entities configuration
    entities_config = load_entities_config(config)

    # Separate entities with and without embeddings
    entities_with_embeddings = filter_entities_with_embeddings(entities_config)

    logger.info(f"Total entities: {len(entities_config)}")
    logger.info(f"Entities with embedding_config: {len(entities_with_embeddings)}")

    # Determine which entities to generate
    if generate_all:
        # Generate trigram for ALL entities
        trigram_entities = entities_config
        # Generate semantic only for entities with embeddings
        semantic_entities = entities_with_embeddings
    else:
        assert entities is not None, "entities must be provided when not using --all"
        requested_entities = [e.strip() for e in entities.split(",")]
        trigram_entities = {}
        semantic_entities = {}

        for entity_key in requested_entities:
            if entity_key not in entities_config:
                logger.warning(f"Entity '{entity_key}' not found, skipping")
            else:
                # Always add to trigram
                trigram_entities[entity_key] = entities_config[entity_key]
                # Add to semantic only if it has embedding_config
                if entity_key in entities_with_embeddings:
                    semantic_entities[entity_key] = entities_with_embeddings[entity_key]

    if not trigram_entities and not semantic_entities:
        logger.error("No valid entities to generate")
        sys.exit(1)

    # Setup Jinja2 environment
    env = Environment(loader=FileSystemLoader(str(template_dir)), trim_blocks=True, lstrip_blocks=True)

    # Generate SQL for each entity
    trigram_success = 0
    semantic_success = 0
    error_count = 0

    # Generate trigram SQL for all entities
    logger.info("")
    logger.info("Generating trigram search SQL files...")
    logger.info("-" * 60)
    for entity_key, entity in trigram_entities.items():
        try:
            generate_trigram_sql(entity_key, entity, env, output_dir, force=force)
            trigram_success += 1
        except Exception as e:
            logger.error(f"Failed to generate trigram schema for {entity_key}: {e}")
            if verbose:
                logger.exception(e)
            error_count += 1

    # Generate semantic SQL only for entities with embeddings
    if semantic_entities:
        logger.info("")
        logger.info("Generating semantic search SQL files...")
        logger.info("-" * 60)
        for entity_key, entity in semantic_entities.items():
            try:
                generate_semantic_sql(entity_key, entity, env, output_dir, force=force)
                semantic_success += 1
            except Exception as e:
                logger.error(f"Failed to generate semantic schema for {entity_key}: {e}")
                if verbose:
                    logger.exception(e)
                error_count += 1

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.success(f"Generated {trigram_success} trigram SQL files")
    logger.success(f"Generated {semantic_success} semantic SQL files")
    if error_count > 0:
        logger.error(f"Failed to generate {error_count} files")
    logger.info(f"Output directory: {output_dir.absolute()}")
    logger.info("=" * 60)

    sys.exit(0 if error_count == 0 else 1)


if __name__ == "__main__":
    main()
