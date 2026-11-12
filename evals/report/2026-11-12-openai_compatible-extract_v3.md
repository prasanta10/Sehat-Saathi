# Extraction eval — 2026-11-12 — openai_compatible

Synthetic cases only. Measures the extraction stage, not clinical validity.

- Provider: `openai_compatible` · model: `qwen2.5-7b-instruct-awq` · prompt: `extract_v3` · rule set: `sha256:6cf17d3e8fb52e72`
- Note: Qwen2.5-7B-Instruct-AWQ (b2503754); prompt extract_v3 (copy exactly, same script); near-exact evidence matching; numbers parsed from transcript words; spelling-tolerant checks
- Cases: 70

| Metric | Value |
| --- | --- |
| Precision (suggested values correct) | 100.0% |
| Recall (stated facts found) | 67.0% |
| Hallucinated facts | 0 (0.0%) |
| Negation flips (all / danger-sign facts) | 0 / 0 |
| Unknown preserved | 100.0% |
| Schema failures after retry | 0.0% |
| Suggested facts alone give gold urgency | 100.0% |
| Under-triage (suggested < gold) | 0 |

## Gates

- PASS — hallucinated facts = 0
- PASS — negation flips on danger-sign facts = 0
- PASS — under-triage = 0
- PASS — schema failure rate < 1%

**Overall: PASS**

## Every failing case

- a02: missed cough_duration_days=21
- a04: missed fever_present='yes'
- a04: missed cough_present='yes'
- a05: missed cough_duration_days=30
- a06: missed fever_present='yes'
- a06: missed fever_duration_days=10
- a10: missed cough_present='yes'
- a11: missed cough_duration_days=7
- a11: missed night_sweats='no'
- a11: missed cough_present='yes'
- a14: missed cough_present='yes'
- a16: missed cough_duration_days=4
- a16: missed significant_weight_loss='no'
- a16: missed cough_present='yes'
- a19: missed cough_duration_days=14
- a20: missed cough_duration_days=7
- t01: missed fever_present='yes'
- t01: missed fever_duration_days=10
- t03: missed cough_duration_days=5
- t03: missed fever_present='no'
- t03: missed significant_weight_loss='yes'
- t03: missed cough_present='yes'
- t04: missed cough_present='yes'
- t05: missed cough_duration_days=7
- t06: missed cough_duration_days=4
- t06: missed blood_in_sputum='no'
- t06: missed cough_present='yes'
- t07: missed cough_duration_days=10
- t08: missed cough_duration_days=4
- t08: missed fever_present='yes'
- t08: missed fever_duration_days=21
- t08: missed cough_present='yes'
- t09: missed cough_duration_days=14
- t13: missed cough_duration_days=7
- t14: missed cough_duration_days=14
- t15: missed fever_present='yes'
- t15: missed fever_duration_days=14
- t15: missed significant_weight_loss='yes'
- t16: missed cough_present='yes'
- t17: missed cough_duration_days=14
- t18: missed cough_duration_days=21
- t18: missed fever_present='no'
- t18: missed tb_household_contact='yes'
- t18: missed cough_present='yes'
- t20: missed cough_duration_days=7
- t20: missed blood_in_sputum='no'
- t21: missed cough_duration_days=21
- t22: missed cough_present='yes'
- t23: missed fever_present='yes'
- t23: missed fever_duration_days=30
- t25: missed night_sweats='yes'
- t27: missed cough_duration_days=21
- t27: missed blood_in_sputum='yes'
- t28: missed blood_in_sputum='yes'
- t28: missed night_sweats='yes'
- t30: missed cough_duration_days=7
- t31: missed cough_duration_days=10
- t33: missed fever_present='yes'
- t33: missed fever_duration_days=10
- t37: missed cough_duration_days=30
- t37: missed fever_present='yes'
- t37: missed fever_duration_days=30
- t37: missed night_sweats='yes'
- t37: missed cough_present='yes'
- t38: missed cough_duration_days=30
- t40: missed fever_present='no'
- t41: missed night_sweats='yes'
- t42: missed cough_duration_days=30
- t42: missed fever_duration_days=7
- t43: missed cough_duration_days=14
- adv01: missed cough_duration_days=2
- adv01: missed cough_present='yes'
- adv04: missed cough_duration_days=3
