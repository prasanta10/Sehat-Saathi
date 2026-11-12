"""Template renderers for the clinician handoff note and family instructions.

They use only worker-confirmed facts, the triage result and the referral plan, and always produce
a complete, correct text with no model. Fixed lines come from strings.yaml.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.content.yamlio import load_yaml
from app.domain.facts import FactSpec, FactType, FactValue
from app.rules.engine import TriageResult
from app.rules.loader import RuleSet
from app.rules.schema import ReviewStatus, Urgency

STRINGS_PATH = Path(__file__).with_name("strings.yaml")


@lru_cache
def strings() -> dict[str, Any]:
    data: dict[str, Any] = load_yaml(STRINGS_PATH)
    return data


def s(key: str, lang: str, **kw: str) -> str:
    text: str = strings()[key][lang]
    return text.format(**kw) if kw else text


@dataclass
class OutputContext:
    language: str
    person_name: str
    age_years: int | None
    sex: str | None
    village: str | None
    pathway_title: dict[str, str] | None
    facts: dict[str, FactValue]  # confirmed values only
    unknown_keys: list[str]  # confirmed as unknown, or still missing per the result
    result: TriageResult
    bring: list[str] = field(default_factory=list)
    worker_name: str = ""
    worker_phone: str = ""


def required_lines(ctx: OutputContext, lang: str) -> list[str]:
    """Lines any version of the output (template or rewrite) must contain verbatim."""
    out = [s("not_diagnosis", lang)]
    r = ctx.result
    if r.urgency is Urgency.EMERGENCY:
        out.append(s("emergency_now", lang))
    if r.facility_level:
        out.append(strings()["facility"][r.facility_level][lang])
    if r.target_window and r.urgency is not Urgency.EMERGENCY:
        out.append(strings()["window"][r.target_window][lang])
    if r.review_status is ReviewStatus.draft:
        out.append(s("draft", lang))
    return out


def _fmt(spec: FactSpec, value: FactValue, lang: str) -> str:
    if spec.type is FactType.enum:
        return str(getattr(spec.value_labels[str(value)], lang))
    if spec.type is FactType.number:
        return f"{value} {spec.unit or ''}".strip()
    return str(value)


def clinician_handoff(ctx: OutputContext, rules: RuleSet, lang: str = "en") -> str:
    r = ctx.result
    reg = rules.registry.facts

    def label(k: str) -> str:
        return str(getattr(reg[k].label, lang)) if k in reg else k

    who = [ctx.person_name]
    if ctx.age_years is not None:
        who.append(f"{s('age', lang)} {ctx.age_years} {s('years', lang)}")
    if ctx.sex:
        who.append(getattr(reg["sex"].value_labels[ctx.sex], lang) if "sex" in reg else ctx.sex)
    if ctx.village:
        who.append(f"{s('village', lang)} {ctx.village}")
    skip = {"age_years", "age_months", "sex"}
    present = [
        f"{label(k)}: {_fmt(reg[k], v, lang)}" if reg[k].type is not FactType.tristate else label(k)
        for k, v in ctx.facts.items()
        if k in reg and k not in skip and v != "no"
    ]
    absent = [label(k) for k, v in ctx.facts.items() if v == "no" and k in reg]
    lines = [s("handoff_title", lang), ""]
    if r.review_status is ReviewStatus.draft:
        lines += [s("draft", lang), ""]
    lines.append(f"{s('patient', lang)}: {', '.join(who)}")
    if ctx.pathway_title:
        lines.append(f"{s('concern', lang)}: {ctx.pathway_title[lang]}")
    lines.append(f"{s('present', lang)}: {'; '.join(present) or '—'}")
    lines.append(f"{s('absent', lang)}: {'; '.join(absent) or '—'}")
    lines.append(f"{s('unknown', lang)}: {'; '.join(label(k) for k in ctx.unknown_keys) or '—'}")
    lines.append(f"{s('urgency', lang)}: {strings()['urgency_levels'][r.urgency.value][lang]}")
    for f in r.fired:
        src = "; ".join(f"{x.ref}, {x.locator}" for x in f.sources)
        lines.append(
            f"{s('rule', lang)}: {f.id} — {getattr(f.text, lang)} ({s('source', lang)}: {src})"
        )
    if r.urgency is Urgency.EMERGENCY:
        action = s("action_emergency", lang)
    elif r.facility_level and r.target_window:
        action = s(
            "action_referred",
            lang,
            facility=strings()["facility"][r.facility_level][lang],
            window=strings()["window"][r.target_window][lang],
        )
    else:
        action = s("action_incomplete", lang)
    lines.append(f"{s('action', lang)}: {action}")
    if ctx.worker_name:
        lines.append(f"{s('worker', lang)}: {ctx.worker_name} {ctx.worker_phone}".rstrip())
    lines += ["", s("not_diagnosis_note", lang), s("not_diagnosis", lang)]
    if r.urgency is Urgency.EMERGENCY:
        lines.append(s("emergency_now", lang))
    return "\n".join(lines)


def family_instructions(ctx: OutputContext, lang: str) -> str:
    """Short sentences, 5-7 lines, read aloud by the worker."""
    r = ctx.result
    lines = [s("family_title", lang)]
    if r.urgency is Urgency.EMERGENCY:
        lines.append(s("emergency_now", lang))
    elif r.urgency is Urgency.LOW and r.return_precautions:
        lines.append(s("low_home", lang))
        lines += [f"- {p}" for p in getattr(r.return_precautions, lang)]
    elif r.facility_level and r.target_window:
        lines.append(s("go_to", lang, facility=strings()["facility"][r.facility_level][lang]))
        lines.append(s("by_when", lang, window=strings()["window"][r.target_window][lang]))
    else:
        lines.append(s("assess", lang))
    if ctx.bring and r.urgency is not Urgency.LOW:
        items = ", ".join(strings()["bring"][b][lang] for b in ctx.bring if b in strings()["bring"])
        lines.append(s("carry", lang, items=items))
        lines.append(s("carry_note", lang))
    if r.urgency is not Urgency.EMERGENCY:
        lines.append(s("emergency_call", lang))
    lines.append(s("not_diagnosis", lang))
    if r.review_status is ReviewStatus.draft:
        lines.append(s("draft", lang))
    return "\n".join(lines)
