#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate pronunciation transcriptions for every Maltese string in the app.

Reads data/words.js and data/sentences.js, converts each `mt:` value into
  * IPA      - letter-to-phoneme mapping, stress marked with U+02C8
  * Russian  - practical "how to read it" transcription, stress marked with
               combining acute U+0301
and writes data/ipa.js as `window.IPA_DATA = { "<mt>": {ipa, ru}, ... }`.

Implemented sound changes
  * silent `h` and `għ`
  * final obstruent devoicing (b>p, d>t, v>f, g>k, ġ>ċ, ż>s) - as in Maltese
  * geminates split across the syllable boundary (tufˈfiɛħa)
  * word stress: penultimate syllable by default, overridable in STRESS_FROM_END

Known approximations (documented in the UI): vowel length is not marked,
`għ` is rendered silent, `q` is a glottal stop, `w` is non-syllabic ў.

Usage:
    python3 tools/make_transcription.py
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = ["data/words.js", "data/sentences.js", "data/dialogues.js"]
# phrases of the noun+verb exercise live under a "phrase" key
PHRASE_SOURCES = ["data/pairs.js", "data/forms.js", "data/blanks.js"]
TARGET = "data/ipa.js"

# Longest match first: digraphs and letters with diacritics come before letters.
IPA_MAP = [
    ("għ", ""), ("ie", "iɛ"), ("gh", ""),
    ("à", "a"), ("è", "ɛ"), ("ì", "i"), ("ò", "ɔ"), ("ù", "u"),
    ("a", "a"), ("b", "b"), ("ċ", "t͡ʃ"), ("d", "d"), ("e", "ɛ"), ("f", "f"),
    ("ġ", "d͡ʒ"), ("g", "ɡ"), ("h", ""), ("ħ", "ħ"), ("i", "i"), ("j", "j"),
    ("k", "k"), ("l", "l"), ("m", "m"), ("n", "n"), ("o", "ɔ"), ("p", "p"),
    ("q", "ʔ"), ("r", "r"), ("s", "s"), ("t", "t"), ("u", "u"), ("v", "v"),
    ("w", "w"), ("x", "ʃ"), ("ż", "z"), ("z", "t͡s"),
]

RU_MAP = [
    ("għ", ""), ("ie", "ие"), ("gh", ""),
    ("à", "а"), ("è", "э"), ("ì", "и"), ("ò", "о"), ("ù", "у"),
    ("a", "а"), ("b", "б"), ("ċ", "ч"), ("d", "д"), ("e", "э"), ("f", "ф"),
    ("ġ", "дж"), ("g", "г"), ("h", ""), ("ħ", "х"), ("i", "и"), ("j", "й"),
    ("k", "к"), ("l", "л"), ("m", "м"), ("n", "н"), ("o", "о"), ("p", "п"),
    ("q", "ъ"), ("r", "р"), ("s", "с"), ("t", "т"), ("u", "у"), ("v", "в"),
    ("w", "ў"), ("x", "ш"), ("ż", "з"), ("z", "ц"),
]

IPA_DEVOICE = {"b": "p", "d": "t", "v": "f", "g": "k", "ġ": "t͡ʃ", "ż": "s"}
RU_DEVOICE = {"b": "п", "d": "т", "v": "ф", "g": "к", "ġ": "ч", "ż": "с"}

RU_GLIDE_MERGE = {"а": "я", "э": "е", "и": "и", "о": "ё", "у": "ю"}
RU_VOWELS = "аэиоу"

# Syllables counted from the end where the stress falls (default: 2).
STRESS_FROM_END = {
    "ajruport": 1, "biljett": 1, "butir": 1, "għasfur": 1, "inbid": 1,
    "qamar": 1, "qasir": 1, "qattus": 1, "ristorant": 1, "sabiħ": 1,
    "tadam": 1, "ukoll": 1, "vapur": 1, "xarabank": 1, "ħabib": 1,
    "ħanut": 1, "ħażin": 1, "maħmuġ": 1, "marid": 1, "nadif": 1,
    "nofsinhar": 1,
}

# Words whose IPA stress mark must sit at an explicit source index, for the
# cases where the penultimate/from-end rule puts the mark mid-cluster.
STRESS_AT_INDEX = {
    "biljett": 3,        # bilˈjɛtt, not biˈljɛtt
    "filgħaxija": 3,     # filˈaʃija (the mark goes before the silent għ)
    "għaxija": 0,        # ˈaʃija
}

VOWEL = re.compile(r"ie|[aeiouàèìòù]", re.IGNORECASE)
ACCENTED = str.maketrans({"à": "a", "è": "e", "ì": "i", "ò": "o", "ù": "u"})
ACUTE = "\u0301"
STRESS = "\u02c8"


def phonemes(word, table):
    """[(source_index, source_unit, rendered_value)] using longest match."""
    out = []
    i = 0
    low = word.lower()
    while i < len(low):
        for key, val in table:
            if low.startswith(key, i):
                out.append((i, key, val))
                i += len(key)
                break
        else:
            out.append((i, low[i], low[i]))
            i += 1
    return out


def devoice(parts, table):
    """Devoice the last *letter* of the segment, skipping trailing punctuation."""
    for i in range(len(parts) - 1, -1, -1):
        idx, key, val = parts[i]
        if key.isalpha():
            return parts[:i] + [(idx, key, table.get(key, val))] + parts[i + 1:]
    return parts


def vowel_units(word):
    return [(m.start(), m.end()) for m in VOWEL.finditer(word)]


def stress_info(word):
    """(onset, vowel_start, vowel_end, syllable_count) or None."""
    units = vowel_units(word)
    if not units:
        return None

    low = word.lower()
    idx = None
    for i, ch in enumerate(low):
        if ch in "àèìòù":
            for j, (s, e) in enumerate(units):
                if s <= i < e:
                    idx = j
                    break
            break

    if idx is None:
        plain = low.translate(ACCENTED)
        from_end = STRESS_FROM_END.get(plain, 2)
        idx = max(0, len(units) - from_end)

    vstart, vend = units[idx]
    onset = units[idx - 1][1] if idx > 0 else 0
    return onset, vstart, vend, len(units)


def explicit_stress_index(word):
    return STRESS_AT_INDEX.get(word.lower().translate(ACCENTED))


def effective_vstart(word):
    """Character index of the stressed vowel, honouring STRESS_AT_INDEX."""
    info = stress_info(word)
    if not info or info[3] <= 1:
        return None
    explicit = explicit_stress_index(word)
    if explicit is not None:
        for start, _ in vowel_units(word):
            if start >= explicit:
                return start
    return info[1]


def ipa_segment(word):
    parts = devoice(phonemes(word, IPA_MAP), IPA_DEVOICE)
    info = stress_info(word)

    stress_at = None
    if info and info[3] > 1:
        explicit = explicit_stress_index(word)
        if explicit is not None:
            stress_at = explicit
        else:
            onset, vstart, _, _ = info
            run = word[onset:vstart]
            stress_at = onset + 1 if len(run) >= 2 and len(set(run)) == 1 else onset

    out = []
    for idx, key, val in parts:
        if stress_at is not None and idx == stress_at:
            out.append(STRESS)
        out.append(val)
    return "".join(out)


def ru_segment(word):
    parts = devoice(phonemes(word, RU_MAP), RU_DEVOICE)
    stressed_src = effective_vstart(word)

    chars = []
    for idx, key, val in parts:
        if key == "q" and idx == 0:
            val = ""
        stressed = stressed_src is not None and idx == stressed_src
        for ci, ch in enumerate(val):
            chars.append([ch, stressed and ci == len(val) - 1])

    merged = []
    i = 0
    while i < len(chars):
        ch, stressed = chars[i]
        if ch == "й" and i + 1 < len(chars) and chars[i + 1][0] in RU_VOWELS:
            nxt, nst = chars[i + 1]
            merged.append([RU_GLIDE_MERGE[nxt], stressed or nst])
            i += 2
        else:
            merged.append([ch, stressed])
            i += 1

    out = []
    for ch, stressed in merged:
        out.append(ch)
        if stressed:
            out.append(ACUTE)
    return "".join(out)


def convert(phrase):
    """Convert a full string; spaces and hyphens stay as segment borders."""
    ipa, ru = [], []
    token = []

    def flush():
        seg = "".join(token)
        token.clear()
        ipa.append(ipa_segment(seg))
        ru.append(ru_segment(seg))

    for ch in phrase:
        if ch in " -":
            flush()
            ipa.append(ch)
            ru.append(ch)
        else:
            token.append(ch)
    flush()
    return "".join(ipa), "".join(ru)


def collect_phrases():
    phrases, seen = [], set()
    for rel in SOURCES:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            text = fh.read()
        for m in re.finditer(r'mt:\s*"((?:[^"\\]|\\.)*)"', text):
            value = m.group(1).replace('\\"', '"')
            if value not in seen:
                seen.add(value)
                phrases.append(value)
    for rel in PHRASE_SOURCES:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        # ключ может быть в кавычках ("phrase") или без (full:)
        for m in re.finditer(r'(?:"phrase"|"full"|full)\s*:\s*"((?:[^"\\]|\\.)*)"', text):
            value = m.group(1).replace('\\"', '"')
            if value not in seen:
                seen.add(value)
                phrases.append(value)
    return phrases


def main():
    phrases = collect_phrases()
    if not phrases:
        print("no phrases found", file=sys.stderr)
        return 1

    lines = ["window.IPA_DATA = {"]
    for phrase in phrases:
        ipa, ru = convert(phrase)
        lines.append(
            '  %s: { ipa: %s, ru: %s },'
            % (json.dumps(phrase, ensure_ascii=False),
               json.dumps("[" + ipa + "]", ensure_ascii=False),
               json.dumps(ru, ensure_ascii=False))
        )
    lines.append("};")

    with open(os.path.join(ROOT, TARGET), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("wrote %s: %d phrases" % (TARGET, len(phrases)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
