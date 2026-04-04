#!/usr/bin/env python3
"""Seed / verify the SIMS well-known source scopes in a target PostgreSQL database.

Usage (from repo root)::

    # Dry-run: show what would be inserted
    uv run python scripts/seed_identity_scopes.py --dry-run

    # Apply to staging (uses connection from config/config.yml)
    uv run python scripts/seed_identity_scopes.py

    # Verify only: exit code 0 if all scopes present, 1 if any are missing
    uv run python scripts/seed_identity_scopes.py --verify

Environment:
    CONFIG_FILE   Override the default config/config.yml path.
    DATABASE_URL  Optional direct DSN override (skips config-based pool).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure repo root is on sys.path when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

WELL_KNOWN_SCOPES: list[dict] = [
    {
        "name": "sead://admin",
        "description": (
            "SEAD administrator actions: adding or modifying classifiers, "
            "methods, and other SEAD-administered entities."
        ),
    },
    {
        "name": "sead://migration",
        "description": "Sqitch-driven schema or data migrations that produce or modify tracked entities.",
    },
    {
        "name": "sead://reconciliation",
        "description": "Reconciliation outputs from the Shape Shifter workflow: matched shared metadata entities.",
    },
]


async def _seed(dry_run: bool, verify: bool) -> int:
    """Return exit code: 0 = OK, 1 = error or missing scopes (verify mode)."""
    from src.configuration import setup_config_store
    from src.configuration import get_connection

    await setup_config_store()

    async with await get_connection() as conn:
        async with conn.cursor() as cur:

            # ------------------------------------------------------------------
            # Check which scopes already exist
            # ------------------------------------------------------------------
            existing_names: set[str] = set()
            await cur.execute("SELECT scope_name FROM sead_identity.source_scopes")
            for row in await cur.fetchall():
                existing_names.add(row[0])

            missing = [s for s in WELL_KNOWN_SCOPES if s["name"] not in existing_names]
            present = [s for s in WELL_KNOWN_SCOPES if s["name"] in existing_names]

            for s in present:
                logger.info(f"  already present: {s['name']}")

            if not missing:
                logger.info("All well-known scopes are present. Nothing to do.")
                return 0

            if verify:
                for s in missing:
                    logger.error(f"  MISSING: {s['name']}")
                logger.error(f"{len(missing)} scope(s) missing — run without --verify to insert them.")
                return 1

            # ------------------------------------------------------------------
            # Insert missing scopes
            # ------------------------------------------------------------------
            if dry_run:
                for s in missing:
                    logger.info(f"  [dry-run] would insert: {s['name']}")
                logger.info(f"Dry-run complete. {len(missing)} scope(s) would be inserted.")
                return 0

            for s in missing:
                await cur.execute(
                    """
                    INSERT INTO sead_identity.source_scopes (scope_name, description)
                    VALUES (%s, %s)
                    ON CONFLICT (scope_name) DO NOTHING
                    """,
                    (s["name"], s["description"]),
                )
                logger.info(f"  inserted: {s['name']}")

            await conn.commit()
            logger.info(f"Seeded {len(missing)} well-known source scope(s).")
            return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed SIMS well-known source scopes.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be inserted without making changes.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Check all scopes are present; exit 1 if any are missing.",
    )
    args = parser.parse_args()

    exit_code = asyncio.run(_seed(dry_run=args.dry_run, verify=args.verify))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
