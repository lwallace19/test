#!/usr/bin/env python3
"""Operational diagnostic for law firms with benchmark comparisons."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class BenchmarkRange:
    low: float
    high: float
    unit: str

    def evaluate(self, value: float) -> str:
        if value < self.low:
            return "below"
        if value > self.high:
            return "above"
        return "within"


@dataclass(frozen=True)
class FirmData:
    name: str
    revenue: float
    lawyers: int
    staff: int
    overhead: float
    practice_areas: List[str]


DEFAULT_BENCHMARKS: Dict[str, BenchmarkRange] = {
    "staff_per_million_revenue": BenchmarkRange(4.0, 7.0, "staff / $1M revenue"),
    "staff_to_lawyer_ratio": BenchmarkRange(1.0, 1.8, "staff per lawyer"),
    "revenue_per_lawyer": BenchmarkRange(550_000.0, 950_000.0, "$ per lawyer"),
    "revenue_per_staff": BenchmarkRange(200_000.0, 350_000.0, "$ per staff"),
    "overhead_pct": BenchmarkRange(0.35, 0.5, "share of revenue"),
}

DEFAULT_SIGNAL_PROMPTS = [
    "Billing realization and collection cycle times.",
    "Practice mix concentration and matter profitability.",
    "Technology spend per FTE compared to peer firms.",
    "Client satisfaction or net promoter scores.",
]


def load_firm_data(path: Path) -> FirmData:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return FirmData(
        name=str(payload["firm_name"]),
        revenue=float(payload["annual_revenue"]),
        lawyers=int(payload["lawyers"]),
        staff=int(payload["staff"]),
        overhead=float(payload["overhead"]),
        practice_areas=list(payload.get("practice_areas", [])),
    )


def load_benchmarks(path: Path | None) -> Dict[str, BenchmarkRange]:
    if path is None:
        return DEFAULT_BENCHMARKS
    payload = json.loads(path.read_text(encoding="utf-8"))
    benchmarks: Dict[str, BenchmarkRange] = {}
    for key, value in payload.items():
        benchmarks[key] = BenchmarkRange(
            low=float(value["low"]),
            high=float(value["high"]),
            unit=str(value.get("unit", "")),
        )
    return {**DEFAULT_BENCHMARKS, **benchmarks}


def load_sources(path: Path | None) -> Dict[str, List[str]]:
    if path is None:
        return {"signals": DEFAULT_SIGNAL_PROMPTS, "sources": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "signals": list(payload.get("signals", DEFAULT_SIGNAL_PROMPTS)),
        "sources": list(payload.get("sources", [])),
    }


def compute_metrics(firm: FirmData) -> Dict[str, float]:
    revenue_millions = firm.revenue / 1_000_000.0
    return {
        "staff_per_million_revenue": firm.staff / revenue_millions,
        "staff_to_lawyer_ratio": firm.staff / firm.lawyers,
        "revenue_per_lawyer": firm.revenue / firm.lawyers,
        "revenue_per_staff": firm.revenue / firm.staff,
        "overhead_pct": firm.overhead / firm.revenue,
    }


def summarize_metric(
    key: str, value: float, benchmarks: Dict[str, BenchmarkRange]
) -> Tuple[str, str, str]:
    benchmark = benchmarks[key]
    status = benchmark.evaluate(value)
    if key == "overhead_pct":
        value_display = f"{value:.0%}"
        range_display = f"{benchmark.low:.0%}-{benchmark.high:.0%}"
    elif "revenue" in key:
        value_display = f"${value:,.0f}"
        range_display = f"${benchmark.low:,.0f}-${benchmark.high:,.0f}"
    else:
        value_display = f"{value:.2f}"
        range_display = f"{benchmark.low:.2f}-{benchmark.high:.2f}"
    return value_display, range_display, status


def build_report(
    firm: FirmData,
    metrics: Dict[str, float],
    benchmarks: Dict[str, BenchmarkRange],
    sources: Dict[str, List[str]],
) -> str:
    lines = [
        f"# Operational Diagnostic: {firm.name}",
        "",
        "## Firm Profile",
        f"- Annual revenue: ${firm.revenue:,.0f}",
        f"- Lawyers: {firm.lawyers}",
        f"- Staff: {firm.staff}",
        f"- Overhead: ${firm.overhead:,.0f}",
    ]
    if firm.practice_areas:
        lines.append(f"- Practice areas: {', '.join(firm.practice_areas)}")
    lines.extend(
        [
            "",
            "## Benchmark Comparisons",
            "| Metric | Your firm | Benchmark | Status |",
            "| --- | --- | --- | --- |",
        ]
    )
    metric_labels = {
        "staff_per_million_revenue": "Staff per $1M revenue",
        "staff_to_lawyer_ratio": "Staff per lawyer",
        "revenue_per_lawyer": "Revenue per lawyer",
        "revenue_per_staff": "Revenue per staff",
        "overhead_pct": "Overhead as % of revenue",
    }
    for key in metric_labels:
        value_display, range_display, status = summarize_metric(
            key, metrics[key], benchmarks
        )
        lines.append(
            f"| {metric_labels[key]} | {value_display} | {range_display} | {status} |"
        )
    if sources["signals"]:
        lines.extend(["", "## Supplemental Signals to Review"])
        for signal in sources["signals"]:
            lines.append(f"- {signal}")
    if sources["sources"]:
        lines.extend(["", "## Data Sources"])
        for source in sources["sources"]:
            lines.append(f"- {source}")
    lines.extend(
        [
            "",
            "## Opportunity Prompts",
            "- Where is staffing density above benchmark, and does it map to practice mix?",
            "- Are administrative roles aligned with attorney leverage expectations?",
            "- How could process automation or shared services shift the staff-to-revenue ratio?",
            "- Which practice areas are driving overhead outliers?",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate an operational diagnostic for a law firm."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to JSON file with firm data.",
    )
    parser.add_argument(
        "--benchmarks",
        help="Optional JSON file with benchmark ranges.",
    )
    parser.add_argument(
        "--sources",
        help="Optional JSON file listing supplemental signals and data sources.",
    )
    args = parser.parse_args()

    firm = load_firm_data(Path(args.input))
    metrics = compute_metrics(firm)
    benchmarks = load_benchmarks(Path(args.benchmarks) if args.benchmarks else None)
    sources = load_sources(Path(args.sources) if args.sources else None)
    print(build_report(firm, metrics, benchmarks, sources))


if __name__ == "__main__":
    main()
