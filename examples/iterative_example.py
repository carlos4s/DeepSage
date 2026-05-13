"""Run the single-loop IterativeResearcher on a focused question.

Use this when you want a short, evidence-cited answer to one specific question
without the overhead of multi-section planning.
"""
import asyncio

from deep_researcher import IterativeResearcher


async def main() -> None:
    researcher = IterativeResearcher(max_iterations=3, verbose=True)
    report = await researcher.run(
        "What were the most-deployed open-source LLM serving frameworks in 2025?"
    )
    print("\n" + "=" * 60 + "\n")
    print(report.markdown)
    print(f"\nSources collected: {len(report.sources)} | iterations: {report.iterations}")


if __name__ == "__main__":
    asyncio.run(main())
