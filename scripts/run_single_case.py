from __future__ import annotations

import sys
import argparse
from pathlib import Path

from rich.console import Console

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.runner.run_case import RunConfig, run_single_case
from src.report.markdown import save_markdown_report


console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a single stress-test case against one model.")
    parser.add_argument("--case-id", required=True, help="Case ID, e.g. A01 / B01 / C01 / D01")
    parser.add_argument("--provider", default="openrouter", help="Provider name, default: openrouter")
    parser.add_argument("--model", required=True, help="Target model name on provider.")
    parser.add_argument("--phase", type=int, default=3, help="Which phase to run: 2/3/4 (default: 3)")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    run_cfg = RunConfig(case_id=args.case_id, provider=args.provider, model=args.model, phase=args.phase)
    console.print(f"[bold]Running case[/bold] {args.case_id} on model {args.model} ({args.provider})")

    run_result = await run_single_case(run_cfg)

    project_root = Path(__file__).resolve().parents[1]
    report_path = project_root / "data" / "reports" / f"{run_result['run_id']}.md"
    save_markdown_report(run_result, report_path)

    console.print(f"[green]Done.[/green] Report saved to {report_path}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

