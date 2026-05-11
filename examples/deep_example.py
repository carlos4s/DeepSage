"""Run the multi-section DeepResearcher and save the report to disk.

The DeepResearcher plans an outline of sections, runs an IterativeResearcher
per section concurrently, stitches the section drafts into one report, then
applies a proofread pass.
"""
import asyncio
from pathlib import Path

from mvp_researcher import DeepResearcher

OUT_DIR = Path(__file__).parent / "sample_output"


async def main() -> None:
    researcher = DeepResearcher(max_iterations=3, verbose=True)
    report = await researcher.run(
        "How are small modular nuclear reactors being deployed across "
        "North America and Europe in 2026?"
    )

    OUT_DIR.mkdir(exist_ok=True)
    md_path = OUT_DIR / "smr_deployment_2026.md"
    md_path.write_text(report.markdown, encoding="utf-8")
    print(f"\nSaved markdown report to {md_path}")
    print(f"Sources collected: {len(report.sources)} | iterations: {report.iterations}")


if __name__ == "__main__":
    asyncio.run(main())
