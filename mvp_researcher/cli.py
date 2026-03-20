from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from .researcher import DeepResearcher


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mvp-research",
        description="Run an iterative deep-research pass and print a cited report.",
    )
    parser.add_argument("query", nargs="+", help="The research question.")
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Write the markdown report to this file (in addition to stdout).",
    )
    parser.add_argument(
        "-i", "--max-iterations", type=int, default=None,
        help="Override MAX_ITERATIONS.",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress progress logging.",
    )
    args = parser.parse_args()

    query = " ".join(args.query)
    researcher = DeepResearcher(
        max_iterations=args.max_iterations,
        verbose=not args.quiet,
    )

    try:
        report = asyncio.run(researcher.run(query))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)

    print("\n" + "=" * 60 + "\n", flush=True)
    print(report.markdown)

    if args.output:
        args.output.write_text(report.markdown, encoding="utf-8")
        print(f"\n[saved to {args.output}]", file=sys.stderr)
