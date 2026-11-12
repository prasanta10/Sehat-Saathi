# Extraction eval — 2026-11-12 — openai_compatible

Synthetic cases only. Measures the extraction stage, not clinical validity.

- Provider: `openai_compatible` · model: `qwen2.5-7b-instruct-awq` · prompt: `extract_v2` · rule set: `sha256:788e34239d230036`
- Note: Qwen2.5-7B-Instruct-AWQ (commit b2503754) on vLLM 0.33, GPU 1 at 50%; prompt extract_v2; bounded schema; AI may not deny red flags/danger signs
- Cases: 70

| Metric | Value |
| --- | --- |
| Precision (suggested values correct) | 93.4% |
| Recall (stated facts found) | 60.3% |
| Hallucinated facts | 5 (4.1%) |
| Negation flips (all / danger-sign facts) | 2 / 0 |
| Unknown preserved | 99.3% |
| Schema failures after retry | 11.4% |
| Suggested facts alone give gold urgency | 95.2% |
| Under-triage (suggested < gold) | 0 |

## Gates

- FAIL — hallucinated facts = 0
- PASS — negation flips on danger-sign facts = 0
- PASS — under-triage = 0
- FAIL — schema failure rate < 1%

**Overall: FAIL**

## Every failing case

- a02: missed cough_duration_days=21
- a02: missed night_sweats='yes'
- a02: missed cough_present='yes'
- a03: missed cough_duration_days=2
- a04: missed fever_present='yes'
- a05: missed cough_duration_days=30
- a06: missed fever_present='yes'
- a06: missed fever_duration_days=10
- a08: HALLUCINATED tb_household_contact='yes'
- a09: missed cough_duration_days=5
- a09: missed cough_present='yes'
- a11: missed night_sweats='no'
- a13: degraded (invalid_output)
- a15: HALLUCINATED rf_breathless='yes'
- a15: missed cough_present='yes'
- a16: degraded (invalid_output)
- a18: HALLUCINATED cough_duration_days=3
- a19: missed cough_duration_days=14
- t01: degraded (invalid_output)
- t03: significant_weight_loss got 'no', gold 'yes'
- t05: missed fever_present='no'
- t05: missed significant_weight_loss='yes'
- t05: missed cough_present='yes'
- t06: missed cough_duration_days=4
- t06: missed blood_in_sputum='no'
- t06: missed fever_present='no'
- t06: missed night_sweats='yes'
- t07: missed cough_present='yes'
- t08: missed fever_present='yes'
- t08: missed cough_present='yes'
- t09: missed fever_present='no'
- t10: missed cough_present='yes'
- t11: missed cough_duration_days=14
- t12: degraded (invalid_output)
- t13: missed blood_in_sputum='yes'
- t13: missed cough_present='yes'
- t14: missed cough_duration_days=14
- t14: missed cough_present='yes'
- t15: missed cough_duration_days=10
- t15: missed fever_present='yes'
- t15: missed fever_duration_days=14
- t15: missed significant_weight_loss='yes'
- t16: degraded (invalid_output)
- t17: missed cough_duration_days=14
- t18: missed cough_duration_days=21
- t18: missed fever_present='no'
- t18: missed tb_household_contact='yes'
- t18: missed cough_present='yes'
- t20: missed blood_in_sputum='no'
- t20: missed fever_present='no'
- t20: missed cough_present='yes'
- t21: missed cough_duration_days=21
- t21: missed cough_present='yes'
- t22: missed cough_duration_days=21
- t22: missed cough_present='yes'
- t23: degraded (invalid_output)
- t24: missed cough_present='yes'
- t25: missed fever_present='no'
- t25: missed tb_household_contact='yes'
- t26: missed cough_duration_days=14
- t27: HALLUCINATED rf_coughing_blood_cup='yes'
- t27: missed cough_duration_days=21
- t27: missed cough_present='yes'
- t28: missed cough_duration_days=10
- t29: missed fever_present='no'
- t30: missed cough_duration_days=7
- t30: missed blood_in_sputum='no'
- t33: degraded (invalid_output)
- t36: missed cough_duration_days=10
- t38: significant_weight_loss got 'no', gold 'yes'
- t39: degraded (invalid_output)
- t40: missed cough_duration_days=21
- t40: missed fever_present='no'
- t40: missed cough_present='yes'
- t41: missed cough_duration_days=14
- t41: missed night_sweats='yes'
- t42: HALLUCINATED rf_breathless='yes'
- t42: cough_duration_days got 7, gold 30
- t42: missed fever_present='yes'
- t42: missed fever_duration_days=7
- t42: missed tb_household_contact='yes'
- t42: missed cough_present='yes'
- t43: missed cough_duration_days=14
- t43: missed cough_present='yes'
- t44: missed cough_duration_days=10
- t45: missed cough_duration_days=14
- t45: missed cough_present='yes'
- adv05: missed cough_present='yes'
