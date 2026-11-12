import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "evals"))
from asr_metrics import cer, key_fact_survival, wer


def test_wer_and_cer() -> None:
    assert wer("teen hafte se khansi hai", "teen hafte se khansi hai") == 0
    assert wer("teen hafte se khansi hai", "do hafte se khansi hai") == 0.2
    assert 0 < cer("बुखार नहीं है", "बुखार नही है") < 0.2


def test_key_fact_survival_catches_dropped_negation_and_wrong_duration() -> None:
    ref = "Teen hafte se khansi hai, bukhar nahi hai."
    assert key_fact_survival(ref, "teen hafte se khansi hai bukhar nahi hai")
    assert not key_fact_survival(ref, "Teen hafte se khansi hai, bukhar hai.")  # lost "nahi"
    assert not key_fact_survival(ref, "Do hafte se khansi hai, bukhar nahi hai.")  # 21 -> 14
