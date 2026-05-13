from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from .researcher import DeepResearcher, IterativeResearcher


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mvp-research",
        description="Run a deep-research pass and print a cited markdown report.",
    )
    parser.add_argument("query", nargs="+", help="The research question.")
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Write the markdown report to this file (in addition to stdout).",
    )
    parser.add_argument(
        "--pdf", type=Path, default=None,
        help="Also render the report as a PDF at this path.",
    )
    parser.add_argument(
        "-m", "--mode", choices=("deep", "iterative"), default="deep",
        help="deep = multi-section report (default); iterative = single loop.",
    )
    parser.add_argument(
        "-i", "--max-iterations", type=int, default=None,
        help="Override MAX_ITERATIONS.",
    )
    parser.add_argument(
        "--no-proofread", action="store_true",
        help="Skip the proofreader pass in deep mode.",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress progress logging.",
    )
    args = parser.parse_args()

    query = " ".join(args.query)
    if args.mode == "deep":
        researcher = DeepResearcher(
            max_iterations=args.max_iterations,
            verbose=not args.quiet,
            proofread=not args.no_proofread,
        )
    else:
        researcher = IterativeResearcher(
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
        print(f"\n[saved markdown to {args.output}]", file=sys.stderr)

    if args.pdf:
        from .utils import markdown_to_pdf
        try:
            markdown_to_pdf(report.markdown, args.pdf)
            print(f"[saved pdf to {args.pdf}]", file=sys.stderr)
        except Exception as e:
            print(f"[pdf export failed: {e}]", file=sys.stderr)
