from __future__ import annotations

import sys
import argparse
from pathlib import Path
from typing import List

from rich.console import Console

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.runner.run_case import RunConfig, run_single_case
from src.report.markdown import save_markdown_report


console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a suite of cases against one or more models.")
    parser.add_argument(
        "--cases",
        nargs="+",
        default=["A01", "B01", "C01", "D01"],
        help="Case IDs to run, default: A01 B01 C01 D01",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        required=True,
        help="Target model names on provider (space-separated).",
    )
    parser.add_argument("--provider", default="openrouter", help="Provider name, default: openrouter")
    parser.add_argument("--phase", type=int, default=3, help="Which phase to run: 2 or 3 (default: 3)")
    return parser.parse_args()


async def run_suite(cases: List[str], models: List[str], provider: str) -> None:
    project_root = Path(__file__).resolve().parents[1]

    for model in models:
        for case_id in cases:
            console.print(f"[bold]Running[/bold] case {case_id} on model {model}")
            run_cfg = RunConfig(case_id=case_id, provider=provider, model=model)
            run_result = await run_single_case(run_cfg)

            report_path = project_root / "data" / "reports" / f"{run_result['run_id']}.md"
            save_markdown_report(run_result, report_path)
            console.print(f"[green]Report saved:[/green] {report_path}")


async def main() -> None:
    args = parse_args()
    await run_suite(args.cases, args.models, args.provider)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

