"""CLI: ask an F1 question end-to-end through the routed pipeline.

Usage:
    uv run python scripts/ask.py "Who won the 2023 Bahrain GP?"
    uv run python scripts/ask.py "How many wins did Verstappen have in 2023?" -v
    uv run python scripts/ask.py "What happened at the 2021 Abu Dhabi GP?" -v
"""

from __future__ import annotations

import argparse

from dotenv import load_dotenv

from rag.ask import ask


def _print_verbose(result) -> None:
    """Pretty-print all the intermediate state."""
    if result.sql_result is not None:
        print("--- SQL path ---")
        print(f"  Generated SQL: {result.sql_result.sql}")
        print(f"  Reasoning:     {result.sql_result.reasoning}")
        if result.sql_result.error:
            print(f"  ERROR: {result.sql_result.error}")
        print(f"  Rows ({result.sql_result.row_count}):")
        for row in result.sql_result.rows[:10]:
            print(f"    {row}")
        if result.sql_result.row_count > 10:
            print(f"    ... ({result.sql_result.row_count - 10} more)")
        print()

    if result.rag_result is not None:
        print("--- RAG path ---")
        used_ids = {c.chunk_id for c in result.rag_result.used_in_prompt}
        print(f"  Retrieved ({len(result.rag_result.retrieved_chunks)} chunks, * = used in prompt):")
        for i, c in enumerate(result.rag_result.retrieved_chunks, 1):
            mark = "*" if c.chunk_id in used_ids else " "
            title = c.metadata.get("title", "")
            print(f"    {mark} [{i}] sim={c.similarity:.3f}  {c.chunk_id}  {title!r}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ask an F1 question end-to-end through the routed RAG/SQL pipeline.",
    )
    parser.add_argument("question", help="The question to answer.")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show the route decision, generated SQL, retrieved chunks, etc.",
    )
    args = parser.parse_args()

    load_dotenv()
    result = ask(args.question)

    print(f"Q: {result.question}")
    print()
    print(
        f"Route: {result.route.category}  "
        f"(confidence {result.route.confidence:.2f})"
    )
    print(f"  reasoning: {result.route.reasoning}")
    print()

    if args.verbose:
        _print_verbose(result)

    print("=== ANSWER ===")
    print(result.final_answer)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
