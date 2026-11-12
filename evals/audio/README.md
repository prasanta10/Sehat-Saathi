# Audio eval set (not yet collected)

Volunteer recordings of a subset of the text cases, with written consent for this purpose only
(no real patients; open question O5). Place files here as `<case_id>__<speaker_id>.wav|webm`
with a `manifest.yaml`:

```yaml
- file: a01__s01.webm
  case: a01            # id in evals/cases/text/*.yaml (gives the reference text and gold facts)
  speaker: s01         # pseudonymous
  device: "low-cost Android, outdoor"
  consent_form: "on file with the team (not in git)"
```

Audio files are git-ignored. `evals/asr_metrics.py` provides WER, CER and key-fact survival;
the ASR run is wired into `make eval` once recordings and the GPU host (O1) exist.
