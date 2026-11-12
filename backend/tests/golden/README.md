# Golden cases

One YAML file per pathway (`<pathway_id>.yaml`) plus `universal_danger_signs.yaml`. Facts in →
expected urgency and fired rule IDs. The same files are run by the TypeScript evaluator (Phase 8),
so both engines must agree on every case.

Every rule needs at least: one `firing` case, one `boundary` near-miss on each numeric threshold
(e.g. 13 vs 14 days), and one `unknown` case where a fact the rule needs is not known. Every
universal danger sign needs a `firing` case. `test_golden.py` enforces this coverage.

Facts are worker-confirmed values; omit a key to mean "unknown". All people are synthetic.

Format: optional file-level `base` facts; each case lists `facts` that override the base and
`unset` keys removed from it (`no_base: true` starts from nothing). `expect` holds `urgency` and
optionally `fired` (exact set), `reason`, `minimum_level`, `missing_includes`, `missing_first`.
