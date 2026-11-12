"""Deterministic parsing of durations, numbers and yes/no answers in Hindi, Hinglish and English.

The model never converts durations: it returns the phrase ("teen hafte"), this code turns it into
days, and the worker confirms the number. Anything ambiguous returns None (unknown), never a guess.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Number words. Romanised Hindi spellings vary; common variants are listed.
_NUMBER_WORDS: dict[str, float] = {
    # English
    "zero": 0,
    "one": 1,
    "a": 1,
    "an": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "fifteen": 15,
    "twenty": 20,
    "thirty": 30,
    "half": 0.5,
    # Romanised Hindi
    "ek": 1,
    "do": 2,
    "teen": 3,
    "tin": 3,
    "char": 4,
    "chaar": 4,
    "paanch": 5,
    "panch": 5,
    "chhe": 6,
    "chhah": 6,
    "che": 6,
    "saat": 7,
    "sat": 7,
    "aath": 8,
    "aat": 8,
    "nau": 9,
    "das": 10,
    "dus": 10,
    "gyarah": 11,
    "barah": 12,
    "baarah": 12,
    "pandrah": 15,
    "pandra": 15,
    "bees": 20,
    "bis": 20,
    "tees": 30,
    "aadha": 0.5,
    "adha": 0.5,
    "dedh": 1.5,
    "dhai": 2.5,
    # Devanagari
    "एक": 1,
    "दो": 2,
    "तीन": 3,
    "चार": 4,
    "पांच": 5,
    "पाँच": 5,
    "छह": 6,
    "छः": 6,
    "सात": 7,
    "आठ": 8,
    "नौ": 9,
    "दस": 10,
    "ग्यारह": 11,
    "बारह": 12,
    "पंद्रह": 15,
    "पन्द्रह": 15,
    "बीस": 20,
    "तीस": 30,
    "आधा": 0.5,
    "डेढ़": 1.5,
    "ढाई": 2.5,
}

# Units in days. Months and years are approximate; flagged so the worker checks the number.
_UNITS: list[tuple[re.Pattern[str], float, bool]] = [
    (re.compile(r"^(day|days|din|dino|dinon|दिन|दिनों)$"), 1, False),
    (
        re.compile(
            r"^(week|weeks|wk|wks|hafta|hafte|haftey|hafton|हफ्ता|हफ्ते|हफ़्ता|हफ़्ते|हफ्तों|हफ़्तों|सप्ताह|सप्ताहों)$"
        ),
        7,
        False,
    ),
    (re.compile(r"^(month|months|mahina|mahine|mahino|mahinon|महीना|महीने|महीनों|माह)$"), 30, True),
    (re.compile(r"^(year|years|saal|sal|baras|साल|वर्ष|बरस)$"), 365, True),
]

_YES = {"yes", "haan", "han", "ha", "haa", "हाँ", "हां"}
_WEAK_YES = {"hai", "है", "ji", "जी"}  # "is" / polite particle: yes only when nothing negates it
_NO = {"no", "nahi", "nahin", "nahee", "na", "nope", "नहीं", "नही", "ना", "जी नहीं"}
_DONT_KNOW = {
    "don't know",
    "dont know",
    "not sure",
    "pata nahi",
    "pata nahin",
    "maloom nahi",
    "malum nahi",
    "पता नहीं",
    "मालूम नहीं",
    "नहीं पता",
}


@dataclass(frozen=True)
class ParsedNumber:
    value: float
    approximate: bool  # e.g. months converted to days


# Speech transcripts spell freely (पांच / पाँच / पाच, हफ़्ते / हफ्ते, वॉमिटिंग / वोमिटिंग): nasal marks
# and the nukta are dropped, and the "English" vowels ॉ ॅ ऑ ऍ folded to ो े ओ ए, before any
# comparison, on both the input and the word lists.
SPELLING_FOLD: dict[int, str | None] = {
    0x0901: None,  # candrabindu
    0x0902: None,  # anusvara
    0x093C: None,  # nukta
    0x0949: "\u094b",  # ॉ -> ो
    0x0945: "\u0947",  # ॅ -> े
    0x0911: "\u0913",  # ऑ -> ओ
    0x090D: "\u090f",  # ऍ -> ए
}
_SPELLING_MARKS = SPELLING_FOLD


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower().strip().translate(_SPELLING_MARKS)
    text = text.translate(str.maketrans("०१२३४५६७८९", "0123456789"))
    return re.sub(r"\s+", " ", re.sub(r"[.,!?।]", " ", text)).strip()


def _loosen_tables() -> None:
    global _NUMBER_WORDS, _YES, _WEAK_YES, _NO, _DONT_KNOW, _UNITS
    _NUMBER_WORDS = {normalise(k): v for k, v in _NUMBER_WORDS.items()}
    _YES, _WEAK_YES, _NO = ({normalise(w) for w in ws} for ws in (_YES, _WEAK_YES, _NO))
    _DONT_KNOW = {normalise(w) for w in _DONT_KNOW}
    _UNITS = [
        (re.compile(unicodedata.normalize("NFC", p.pattern).translate(_SPELLING_MARKS)), d, a)
        for p, d, a in _UNITS
    ]


def _number(token: str) -> float | None:
    if re.fullmatch(r"\d+(\.\d+)?", token):
        return float(token)
    return _NUMBER_WORDS.get(token)


def _unit(token: str) -> tuple[float, bool] | None:
    for pattern, days, approx in _UNITS:
        if pattern.match(token):
            return days, approx
    return None


def parse_duration_days(text: str) -> ParsedNumber | None:
    """'teen hafte' -> 21, '2 weeks' -> 14, '10 din' -> 10, 'ek mahina' -> 30 (approximate).

    Returns None if the phrase has no clear single quantity, or mixes several ("do ya teen din").
    """
    tokens = normalise(text).split()
    # Two quantities ("do se teen din", "do ya teen din", "teen din aur do hafte") are ambiguous:
    # the worker decides. "a"/"an" only count as a quantity directly before a unit.
    quantities = [
        t
        for i, t in enumerate(tokens)
        if _number(t) is not None
        and not (t in ("a", "an") and (i + 1 >= len(tokens) or _unit(tokens[i + 1]) is None))
    ]
    if len(quantities) > 1:
        return None
    found: list[ParsedNumber] = []
    i = 0
    while i < len(tokens):
        unit = _unit(tokens[i])
        if unit is not None:
            qty = _number(tokens[i - 1]) if i > 0 else None
            if qty is None and i > 0 and tokens[i - 1] in ("ek", "a", "an", "एक"):
                qty = 1
            if qty is None:
                # bare unit: "hafte se" without a number is ambiguous; "a week" handled above
                return None
            days, approx = unit
            found.append(ParsedNumber(round(qty * days, 2), approx))
        i += 1
    if len(found) != 1:
        return None
    value = found[0].value
    if value != int(value):
        return ParsedNumber(value, True)
    return ParsedNumber(int(value), found[0].approximate)


def count_quantities(text: str) -> int:
    """Number of quantities in a phrase ("do ya teen hafte" -> 2)."""
    tokens = normalise(text).split()
    return sum(
        1
        for i, t in enumerate(tokens)
        if _number(t) is not None
        and not (t in ("a", "an") and (i + 1 >= len(tokens) or _unit(tokens[i + 1]) is None))
    )


def parse_number(text: str) -> float | None:
    tokens = normalise(text).split()
    nums = [n for n in (_number(t) for t in tokens) if n is not None]
    return nums[0] if len(nums) == 1 else None


def parse_yes_no(text: str) -> str | None:
    """'yes', 'no' or 'unknown' (explicit don't-know); None if unclear."""
    t = normalise(text)
    if t in _DONT_KNOW or any(p in t for p in _DONT_KNOW):
        return "unknown"
    words = set(t.split())
    neg = bool(words & _NO)
    strong = bool(words & _YES)
    weak = bool(words & _WEAK_YES)
    if neg and strong:
        return None  # "haan... nahi": contradictory, ask again
    if neg:
        return "no"  # "bukhar nahi hai"
    if strong or weak:
        return "yes"
    return None


def has_negation(text: str) -> bool:
    """True if the phrase contains a negation word (nahi, नहीं, no, not, ...)."""
    return bool(set(normalise(text).split()) & (_NO | {"not", "never", "kabhi", "कभी"}))


_loosen_tables()
