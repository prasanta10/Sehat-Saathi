# Extraction eval — 2026-11-12 — openai_compatible

Synthetic cases only. Measures the extraction stage, not clinical validity.

- Provider: `openai_compatible` · model: `qwen2.5-7b-instruct-awq` · prompt: `extract_v2` · rule set: `sha256:788e34239d230036`
- Note: Qwen2.5-7B-Instruct-AWQ (b2503754), vLLM 0.33 xgrammar no-free-whitespace, GPU 1 at 50%; prompt extract_v2; fixed-slot schema; AI may not deny red flags/danger signs
- Cases: 70

| Metric | Value |
| --- | --- |
| Precision (suggested values correct) | 92.6% |
| Recall (stated facts found) | 79.6% |
| Hallucinated facts | 9 (4.7%) |
| Negation flips (all / danger-sign facts) | 5 / 0 |
| Unknown preserved | 98.9% |
| Schema failures after retry | 0.0% |
| Suggested facts alone give gold urgency | 91.4% |
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
- a06: HALLUCINATED cough_duration_days=10
- a06: missed fever_present='yes'
- a06: missed fever_duration_days=10
- a06: cough_present got 'yes', gold 'no'
- a11: missed night_sweats='no'
- a13: HALLUCINATED rf_coughing_blood_cup='yes'
- a13: missed cough_duration_days=14
- a13: missed cough_present='yes'
- a16: missed significant_weight_loss='no'
- a18: HALLUCINATED cough_duration_days=3
- a19: missed cough_duration_days=14
- t01: fever_present got 'no', gold 'yes'
- t03: significant_weight_loss got 'no', gold 'yes'
- t06: missed blood_in_sputum='no'
- t10: missed cough_present='yes'
- t13: HALLUCINATED rf_coughing_blood_cup='yes'
- t13: missed cough_duration_days=7
- t13: missed blood_in_sputum='yes'
- t13: missed cough_present='yes'
- t14: missed cough_duration_days=14
- t14: missed cough_present='yes'
- t15: fever_present got 'no', gold 'yes'
- t15: missed significant_weight_loss='yes'
- t17: missed cough_duration_days=14
- t20: missed cough_present='yes'
- t21: missed cough_duration_days=21
- t21: missed cough_present='yes'
- t22: missed cough_duration_days=21
- t23: missed fever_present='yes'
- t23: missed fever_duration_days=30
- t25: missed cough_duration_days=14
- t25: missed night_sweats='yes'
- t25: missed cough_present='yes'
- t27: HALLUCINATED rf_coughing_blood_cup='yes'
- t27: missed cough_duration_days=21
- t27: missed cough_present='yes'
- t28: HALLUCINATED rf_coughing_blood_cup='yes'
- t30: missed blood_in_sputum='no'
- t33: HALLUCINATED rf_coughing_blood_cup='yes'
- t33: fever_present got 'no', gold 'yes'
- t33: missed fever_duration_days=10
- t37: missed fever_present='yes'
- t37: missed fever_duration_days=30
- t37: missed night_sweats='yes'
- t39: missed cough_present='yes'
- t40: missed fever_present='no'
- t41: missed night_sweats='yes'
- t43: HALLUCINATED rf_coughing_blood_cup='yes'
- t43: missed cough_duration_days=14
- t43: missed cough_present='yes'
- adv01: HALLUCINATED blood_in_sputum='yes'
