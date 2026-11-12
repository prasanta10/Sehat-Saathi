from app.domain.facts import FactValue
from app.rules.engine import TriageResult, evaluate
from app.rules.loader import RuleSet


def triage(rs: RuleSet, facts: dict[str, FactValue], pathway: str | None) -> TriageResult:
    return evaluate(facts, rs.pathway(pathway) if pathway else None, rs.danger_signs, rs.version)
