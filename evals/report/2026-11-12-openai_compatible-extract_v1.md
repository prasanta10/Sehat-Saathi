# Extraction eval — 2026-11-12 — openai_compatible

Synthetic cases only. Measures the extraction stage, not clinical validity.

- Provider: `openai_compatible` · model: `qwen2.5-7b-instruct-awq` · prompt: `extract_v1` · rule set: `sha256:71ef23550a9ec76b`
- Note: Qwen2.5-7B-Instruct-AWQ (commit b2503754) on vLLM 0.33, RTX 3090 GPU 1 at 50% memory, prompt extract_v1, temperature 0
- Cases: 70

| Metric | Value |
| --- | --- |
| Precision (suggested values correct) | 78.3% |
| Recall (stated facts found) | 56.4% |
| Hallucinated facts | 31 (19.7%) |
| Negation flips (all / danger-sign facts) | 2 / 0 |
| Unknown preserved | 96.1% |
| Schema failures after retry | 2.9% |
| Suggested facts alone give gold urgency | 98.5% |
| Under-triage (suggested < gold) | 0 |

## Gates

- FAIL — hallucinated facts = 0
- PASS — negation flips on danger-sign facts = 0
- PASS — under-triage = 0
- FAIL — schema failure rate < 1%

**Overall: FAIL**

## Every failing case

- a01: missed cough_present='yes'
- a02: missed cough_duration_days=21
- a02: missed night_sweats='yes'
- a02: missed cough_present='yes'
- a03: missed cough_present='yes'
- a04: missed fever_present='yes'
- a04: missed cough_present='yes'
- a05: missed cough_present='yes'
- a06: missed fever_present='yes'
- a07: missed tb_household_contact='yes'
- a08: missed cough_duration_days=14
- a09: missed cough_duration_days=5
- a09: missed fever_present='no'
- a09: missed cough_present='yes'
- a10: degraded (provider_unavailable)
- a11: missed cough_duration_days=7
- a11: missed night_sweats='no'
- a11: missed cough_present='yes'
- a12: HALLUCINATED cough_duration_days=21
- a13: missed cough_duration_days=14
- a15: missed cough_present='yes'
- a16: missed significant_weight_loss='no'
- a18: missed fever_duration_days=3
- a19: missed cough_duration_days=14
- a19: missed cough_present='yes'
- t01: missed fever_present='yes'
- t01: missed cough_present='yes'
- t03: HALLUCINATED rf_breathless='no'
- t03: significant_weight_loss got 'no', gold 'yes'
- t04: missed cough_duration_days=4
- t04: missed fever_present='no'
- t05: missed cough_duration_days=7
- t05: missed fever_present='no'
- t05: missed cough_present='yes'
- t06: missed cough_present='yes'
- t07: missed cough_present='yes'
- t10: missed cough_duration_days=21
- t10: missed blood_in_sputum='no'
- t10: missed night_sweats='yes'
- t10: missed cough_present='yes'
- t11: missed cough_duration_days=14
- t13: missed cough_duration_days=7
- t14: missed cough_duration_days=14
- t15: cough_duration_days got 14, gold 10
- t15: missed fever_present='yes'
- t15: missed fever_duration_days=14
- t15: missed significant_weight_loss='yes'
- t15: missed cough_present='yes'
- t16: HALLUCINATED rf_breathless='no'
- t16: HALLUCINATED rf_coughing_blood_cup='no'
- t16: missed blood_in_sputum='no'
- t16: missed fever_present='no'
- t17: missed cough_duration_days=14
- t19: HALLUCINATED rf_breathless='no'
- t19: missed cough_duration_days=5
- t20: missed fever_present='no'
- t21: missed cough_duration_days=21
- t21: missed fever_present='no'
- t21: missed cough_present='yes'
- t22: missed cough_duration_days=21
- t22: missed blood_in_sputum='no'
- t22: missed fever_present='no'
- t22: missed significant_weight_loss='yes'
- t22: missed cough_present='yes'
- t23: HALLUCINATED rf_breathless='no'
- t23: HALLUCINATED rf_coughing_blood_cup='no'
- t23: missed cough_duration_days=13
- t23: missed fever_present='yes'
- t23: missed fever_duration_days=30
- t23: missed cough_present='yes'
- t24: missed cough_duration_days=10
- t24: missed fever_present='no'
- t25: missed cough_duration_days=14
- t25: missed fever_present='no'
- t26: missed cough_duration_days=14
- t27: missed cough_duration_days=21
- t27: missed blood_in_sputum='yes'
- t27: missed fever_present='no'
- t27: missed cough_present='yes'
- t28: missed cough_present='yes'
- t30: missed cough_duration_days=7
- t31: missed fever_present='no'
- t32: missed cough_duration_days=4
- t35: degraded (provider_unavailable)
- t36: missed cough_duration_days=10
- t36: missed fever_present='no'
- t36: missed cough_present='yes'
- t38: missed cough_present='yes'
- t39: HALLUCINATED rf_breathless='no'
- t40: HALLUCINATED rf_breathless='no'
- t40: HALLUCINATED rf_altered_consciousness_convulsions_weakness='no'
- t40: HALLUCINATED rf_coughing_blood_cup='no'
- t40: HALLUCINATED rf_severe_chest_or_abdominal_pain='no'
- t40: HALLUCINATED rf_confined_to_bed='no'
- t40: HALLUCINATED rf_recurrent_vomiting_diarrhoea='no'
- t40: missed cough_duration_days=21
- t40: HALLUCINATED blood_in_sputum='no'
- t40: HALLUCINATED significant_weight_loss='no'
- t40: HALLUCINATED night_sweats='no'
- t40: HALLUCINATED tb_household_contact='no'
- t40: HALLUCINATED past_tb='no'
- t41: missed cough_present='yes'
- t42: HALLUCINATED rf_coughing_blood_cup='yes'
- t42: missed cough_duration_days=30
- t42: missed fever_present='yes'
- t42: missed fever_duration_days=7
- t42: missed cough_present='yes'
- t43: missed cough_duration_days=14
- t43: missed night_sweats='yes'
- t44: missed cough_duration_days=10
- t44: missed fever_present='no'
- t44: missed cough_present='yes'
- t45: HALLUCINATED rf_breathless='no'
- t45: HALLUCINATED rf_altered_consciousness_convulsions_weakness='no'
- t45: HALLUCINATED rf_coughing_blood_cup='no'
- t45: HALLUCINATED rf_severe_chest_or_abdominal_pain='no'
- t45: HALLUCINATED rf_confined_to_bed='no'
- t45: HALLUCINATED rf_recurrent_vomiting_diarrhoea='no'
- t45: missed cough_duration_days=14
- t45: HALLUCINATED blood_in_sputum='no'
- t45: HALLUCINATED significant_weight_loss='no'
- t45: HALLUCINATED night_sweats='no'
- t45: HALLUCINATED tb_household_contact='no'
- t45: HALLUCINATED past_tb='no'
- adv03: missed fever_present='no'
- adv04: missed cough_present='yes'
- adv05: missed cough_duration_days=14
- adv05: cough_present got 'no', gold 'yes'
