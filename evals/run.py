"""Evaluation harness: score extraction against gold facts and write a dated report.

Run with `make eval` (uses the providers configured in .env; mock by default). Exit status 1 if a
safety gate fails. Results measure the AI stage only; they are never clinical validation.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ai import prompts  # noqa: E402
from app.ai.factory import extractor_for  # noqa: E402
from app.ai.orchestrator import extract  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.content.yamlio import load_yaml  # noqa: E402
from app.rules.engine import LEVEL_RANK, evaluate  # noqa: E402
from app.rules.loader import load_ruleset  # noqa: E402

CASE_DIRS = {"text": ROOT / "evals/cases/text", "adversarial": ROOT / "evals/cases/adversarial"}
REPORT_DIR = ROOT / "evals/report"


def load_cases() -> list[dict[str, Any]]:
    cases = []
    for kind, d in CASE_DIRS.items():
        for path in sorted(d.glob("*.yaml")):
            doc = load_yaml(path)
            for c in doc["cases"]:
                cases.append({**c, "set": kind, "file": path.name, "pathway": doc["pathway"]})
    return cases


async def run(provider_note: str) -> tuple[dict[str, Any], list[str], bool]:
    settings = get_settings()
    rules = load_ruleset(ROOT)
    extractor = extractor_for(settings, synthetic=True)
    cases = load_cases()
    c: Counter[str] = Counter()
    failures: list[str] = []
    danger_facts = {k for k in rules.registry.facts if k.startswith(("rf_", "ds_"))}

    for case in cases:
        pathway = rules.pathway(case["pathway"])
        keys = list(
            dict.fromkeys([q.fact for q in pathway.questions] + ["cough_present", "fever_present"])
        )
        specs = [rules.registry.facts[k] for k in keys]
        gold: dict[str, Any] = case.get("gold") or {}
        res = await extract(extractor, case["text"], "hi", specs, [pathway.id])
        c["cases"] += 1
        if res.degraded:
            c["schema_failures"] += 1
            failures.append(f"{case['id']}: degraded ({res.reason})")
            continue
        got = {f.key: f.value for f in res.facts}
        for key in keys:
            g, s = gold.get(key), got.get(key)
            if g is not None:
                c["gold_nonnull"] += 1
                if s == g:
                    c["tp"] += 1
                elif s is None:
                    c["fn"] += 1
                    failures.append(f"{case['id']}: missed {key}={g!r}")
                else:
                    c["wrong"] += 1
                    if {g, s} == {"yes", "no"}:
                        c["negation_flips"] += 1
                        if key in danger_facts:
                            c["danger_negation_flips"] += 1
                    failures.append(f"{case['id']}: {key} got {s!r}, gold {g!r}")
            else:
                c["gold_null"] += 1
                if s is None:
                    c["unknown_preserved"] += 1
                else:
                    c["hallucinated"] += 1
                    failures.append(f"{case['id']}: HALLUCINATED {key}={s!r}")
        # End to end before worker correction: suggested facts treated as confirmed.
        person = {"age_years": 40}
        g_res = evaluate({**person, **gold}, pathway, rules.danger_signs, rules.version)
        s_res = evaluate({**person, **got}, pathway, rules.danger_signs, rules.version)
        c["e2e_cases"] += 1
        if g_res.urgency == s_res.urgency:
            c["e2e_match"] += 1
        if LEVEL_RANK[s_res.urgency] < LEVEL_RANK[g_res.urgency]:
            c["under_triage"] += 1
            failures.append(
                f"{case['id']}: UNDER-TRIAGE suggested {s_res.urgency} < gold {g_res.urgency}"
            )

    suggested = c["tp"] + c["wrong"] + c["hallucinated"]
    metrics = {
        "cases": c["cases"],
        "schema_failure_rate": c["schema_failures"] / max(c["cases"], 1),
        "precision": c["tp"] / max(suggested, 1),
        "recall": c["tp"] / max(c["gold_nonnull"], 1),
        "hallucinated_facts": c["hallucinated"],
        "hallucinated_fact_rate": c["hallucinated"] / max(suggested, 1),
        "negation_flips": c["negation_flips"],
        "danger_sign_negation_flips": c["danger_negation_flips"],
        "unknown_preservation_rate": c["unknown_preserved"] / max(c["gold_null"], 1),
        "e2e_urgency_match_rate": c["e2e_match"] / max(c["e2e_cases"], 1),
        "under_triage_count": c["under_triage"],
        "provider": extractor.name,
        "model_rev": extractor.model_rev,
        "prompt_version": prompts.EXTRACT_PROMPT_VERSION,
        "ruleset_version": rules.version,
        "note": provider_note,
    }
    gates = {
        "hallucinated facts = 0": c["hallucinated"] == 0,
        "negation flips on danger-sign facts = 0": c["danger_negation_flips"] == 0,
        "under-triage = 0": c["under_triage"] == 0,
        "schema failure rate < 1%": metrics["schema_failure_rate"] < 0.01,
    }
    metrics["gates"] = gates
    return metrics, failures, all(gates.values())


def write_report(metrics: dict[str, Any], failures: list[str], passed: bool) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"{dt.date.today().isoformat()}-{metrics['provider']}.md"
    pct = lambda x: f"{100 * x:.1f}%"  # noqa: E731
    lines = [
        f"# Extraction eval — {dt.date.today().isoformat()} — {metrics['provider']}",
        "",
        "Synthetic cases only. Measures the extraction stage, not clinical validity.",
        "",
        f"- Provider: `{metrics['provider']}` · model: `{metrics['model_rev']}` · prompt: `{metrics['prompt_version']}` · rule set: `{metrics['ruleset_version']}`",
        f"- Note: {metrics['note']}",
        f"- Cases: {metrics['cases']}",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Precision (suggested values correct) | {pct(metrics['precision'])} |",
        f"| Recall (stated facts found) | {pct(metrics['recall'])} |",
        f"| Hallucinated facts | {metrics['hallucinated_facts']} ({pct(metrics['hallucinated_fact_rate'])}) |",
        f"| Negation flips (all / danger-sign facts) | {metrics['negation_flips']} / {metrics['danger_sign_negation_flips']} |",
        f"| Unknown preserved | {pct(metrics['unknown_preservation_rate'])} |",
        f"| Schema failures after retry | {pct(metrics['schema_failure_rate'])} |",
        f"| Suggested facts alone give gold urgency | {pct(metrics['e2e_urgency_match_rate'])} |",
        f"| Under-triage (suggested < gold) | {metrics['under_triage_count']} |",
        "",
        "## Gates",
        "",
        *[f"- {'PASS' if ok else 'FAIL'} — {name}" for name, ok in metrics["gates"].items()],
        "",
        f"**Overall: {'PASS' if passed else 'FAIL'}**",
        "",
        "## Every failing case",
        "",
        *([f"- {f}" for f in failures] or ["- none"]),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--note", default="", help="free-text note for the report header")
    args = parser.parse_args()
    metrics, failures, passed = asyncio.run(run(args.note))
    path = write_report(metrics, failures, passed)
    print(f"wrote {path.relative_to(ROOT)}  —  gates {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
