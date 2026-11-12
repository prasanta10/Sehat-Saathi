# Extraction eval — 2026-11-12 — openai_compatible

Synthetic cases only. Measures the extraction stage, not clinical validity.

- Provider: `openai_compatible` · model: `qwen2.5-7b-instruct-awq` · prompt: `extract_v2` · rule set: `sha256:6cf17d3e8fb52e72`
- Note: Qwen2.5-7B-Instruct-AWQ (b2503754); prompt extract_v2; fixed slots; deterministic checks with spelling-tolerant evidence terms (nasal marks/nukta ignored, Devanagari loanwords)
- Cases: 70

| Metric | Value |
| --- | --- |
| Precision (suggested values correct) | 99.4% |
| Recall (stated facts found) | 75.6% |
| Hallucinated facts | 1 (0.6%) |
| Negation flips (all / danger-sign facts) | 0 / 0 |
| Unknown preserved | 99.9% |
| Schema failures after retry | 0.0% |
| Suggested facts alone give gold urgency | 100.0% |
| Under-triage (suggested < gold) | 0 |

## Gates

- FAIL — hallucinated facts = 0
- PASS — negation flips on danger-sign facts = 0
- PASS — under-triage = 0
- PASS — schema failure rate < 1%

**Overall: FAIL**

## Every failing case

- a02: missed cough_duration_days=21
- a02: missed cough_present='yes'
- a04: missed fever_present='yes'
- a06: missed fever_present='yes'
- a06: missed fever_duration_days=10
- a06: missed cough_present='no'
- a11: missed night_sweats='no'
- a11: missed cough_present='yes'
- a13: missed cough_duration_days=14
- a13: missed cough_present='yes'
- a16: missed significant_weight_loss='no'
- a16: missed cough_present='yes'
- a19: missed cough_duration_days=14
- t01: missed fever_present='yes'
- t03: missed significant_weight_loss='yes'
- t04: missed cough_present='yes'
- t06: missed blood_in_sputum='no'
- t06: missed cough_present='yes'
- t10: missed cough_present='yes'
- t13: missed cough_duration_days=7
- t13: missed blood_in_sputum='yes'
- t13: missed cough_present='yes'
- t14: missed cough_duration_days=14
- t14: missed cough_present='yes'
- t15: missed fever_present='yes'
- t15: missed significant_weight_loss='yes'
- t17: missed cough_duration_days=14
- t20: missed cough_present='yes'
- t21: missed cough_duration_days=21
- t21: missed cough_present='yes'
- t22: missed cough_duration_days=21
- t23: missed fever_present='yes'
- t23: missed fever_duration_days=30
- t24: missed cough_present='yes'
- t25: missed cough_duration_days=14
- t25: missed night_sweats='yes'
- t25: missed cough_present='yes'
- t27: missed cough_duration_days=21
- t27: missed cough_present='yes'
- t28: missed cough_present='yes'
- t30: missed blood_in_sputum='no'
- t33: missed fever_present='yes'
- t33: missed fever_duration_days=10
- t37: missed cough_duration_days=30
- t37: missed fever_present='yes'
- t37: missed fever_duration_days=30
- t37: missed night_sweats='yes'
- t39: missed cough_present='yes'
- t40: missed cough_duration_days=21
- t40: missed fever_present='no'
- t40: missed cough_present='yes'
- t41: missed night_sweats='yes'
- t43: missed cough_duration_days=14
- t43: missed cough_present='yes'
- adv01: HALLUCINATED blood_in_sputum='yes'
