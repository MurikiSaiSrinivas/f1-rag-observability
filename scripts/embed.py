"""CLI entrypoint for Phase 2 embedding.

Default mode is dry-run: counts pending chunks + tokens, prints estimated
cost, and exits. Re-run with --confirm to actually call the OpenAI API.

Usage:
    uv run python scripts/embed.py                # dry-run, no API call
    uv run python scripts/embed.py --confirm      # embed for real
"""

from __future__ import annotations

import argparse

from dotenv import load_dotenv

from ingestion.embed.openai_client import dry_run, load_chunks, run_embed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Embed Phase 2 chunks via OpenAI text-embedding-3-small.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually call the OpenAI API. Without this, prints a dry-run estimate only.",
    )
    args = parser.parse_args()

    # Load .env from project root. Always called so dry-run also picks it up
    # (the OpenAI client check happens later, only if --confirm).
    load_dotenv()

    if args.confirm:
        run_embed()
    else:
        chunks = load_chunks()
        dry_run(chunks)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
