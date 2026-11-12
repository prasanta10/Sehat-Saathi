"""Invariant 6: no promised money.

Scheme results use only the three statuses; scheme text never says approved/eligible/guaranteed;
amounts appear only quoted from a cited official source with a date; every card has a source."""

import re

from app.config import REPO_ROOT
from app.content.yamlio import load_yaml
from app.rules.schema import Urgency
from app.schemes.matcher import Status, load_schemes, match

PROMISES = re.compile(
    r"\b(approved|eligible|guarantee[ds]?|will (get|receive|be paid))\b|स्वीकृत|पात्र हैं|ज़रूर मिलेगा|मिलेगा ही",
    re.I,
)


def _texts(d: object) -> list[str]:
    if isinstance(d, str):
        return [d]
    if isinstance(d, dict):
        return [
            t
            for k, v in d.items()
            if k not in ("sources", "source", "id", "review")
            for t in _texts(v)
        ]
    if isinstance(d, list):
        return [t for v in d for t in _texts(v)]
    return []


def test_scheme_texts_make_no_promises() -> None:
    for p in (REPO_ROOT / "knowledge" / "schemes").glob("*.yaml"):
        for t in _texts(load_yaml(p)):
            assert not PROMISES.search(t), (p.name, t)


def test_amounts_only_with_source_and_date_and_only_in_amounts() -> None:
    money = re.compile(r"₹|\brs\.?\s?\d|rupee|रुपये|रुपए", re.I)
    for p in (REPO_ROOT / "knowledge" / "schemes").glob("*.yaml"):
        d = load_yaml(p)
        for a in d["amounts"]:
            assert (
                a["source"]["ref"]
                and a["source"]["locator"]
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(a["as_of"]))
            )
        rest = {k: v for k, v in d.items() if k != "amounts"}
        for t in _texts(rest):
            assert not money.search(t), (p.name, t)


def test_only_three_statuses_and_every_card_has_a_source() -> None:
    schemes = load_schemes(REPO_ROOT)
    for urgency in Urgency:
        for facts in (
            {"age_years": 75, "pregnant": "no"},
            {"age_years": 25, "pregnant": "yes"},
            {},
        ):
            for c in match(
                schemes, state="UP", urgency=urgency, facts=facts, pathway_tags={"tb_related"}
            ):
                assert c.status in set(Status)
                assert c.scheme.sources
