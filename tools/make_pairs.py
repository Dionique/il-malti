#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the noun + verb exercise (`data/pairs.js`).

Each item is a short sentence "Il-mara tikteb." with three things to work out:
the gender of the subject, the agreeing verb form and the translation.

The Maltese side is derived from data in data/words.js:
  * noun article  - the stored `art` field, recomputed by the rule below and
                    cross-checked against every noun in the dictionary
  * plural article - the same rule applied to the plural stem
  * verb form      - the `pres` paradigm (3sg m, 3sg f, 3pl)

The Russian side is curated in RU3 / RU_PL below.

Usage:
    python3 tools/make_pairs.py            # write data/pairs.js
    python3 tools/make_pairs.py --check    # only validate the article rule
    python3 tools/make_pairs.py --sample   # print a review sample
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = "data/pairs.js"

SUN = set("ċdnrstxżz")
MOON = set("bfġgghħjklmpqvw"[:0] + "bfġghħjklmpqvw")

# Russian present, 3rd person: (singular, plural)
RU_V = {
    "kiteb": ("пишет", "пишут"), "qara": ("читает", "читают"),
    "kiel": ("ест", "едят"), "xorob": ("пьёт", "пьют"),
    "ra": ("видит", "видят"), "sema'": ("слушает", "слушают"),
    "tkellem": ("говорит", "говорят"), "mar": ("идёт", "идут"),
    "ġie": ("приходит", "приходят"), "ħadem": ("работает", "работают"),
    "tgħallem": ("учится", "учатся"), "fehem": ("понимает", "понимают"),
    "raqad": ("спит", "спят"), "mexa": ("идёт пешком", "идут пешком"),
    "sajjar": ("готовит", "готовят"), "ħasel": ("моет", "моют"),
    "għex": ("живёт", "живут"), "ħabb": ("любит", "любят"),
    "stenna": ("ждёт", "ждут"),
}

# verb -> nouns that make a sensible subject with it
PAIRS = [
    ("kiteb",   ["mara", "tifla", "tifel", "student", "raġel"]),
    ("qara",    ["tifla", "student", "mara", "raġel"]),
    ("kiel",    ["tifel", "mara", "kelb", "qattus", "tifla"]),
    ("xorob",   ["tifel", "mara", "kelb", "qattus"]),
    ("ra",      ["tifel", "mara", "nanu"]),
    ("sema'",   ["tifla", "mara", "nanu"]),
    ("tkellem", ["mara", "raġel", "omm", "missier", "student"]),
    ("mar",     ["tifel", "mara", "raġel", "student"]),
    ("ġie",     ["tifel", "mara", "ħabib", "ħabiba"]),
    ("ħadem",   ["mara", "raġel", "missier", "omm", "student"]),
    ("tgħallem", ["tifel", "tifla", "student"]),
    ("fehem",   ["tifel", "mara", "student"]),
    ("raqad",   ["tifel", "tifla", "qattus", "kelb"]),
    ("mexa",    ["tifel", "mara", "nanu"]),
    ("sajjar",  ["omm", "nanna", "mara"]),
    ("ħasel",   ["omm", "tifla", "nanna"]),
    ("għex",    ["nanu", "nanna", "mara"]),
    ("ħabb",    ["omm", "nanna", "mara"]),
    ("stenna",  ["mara", "raġel", "tifel"]),
]

# plural subjects: (noun mt, plural form, Russian plural, [verbs])
PLURALS = [
    ("tifel",   "tfal",     "дети",     ["kiteb", "mar", "raqad", "kiel"]),
    ("mara",    "nisa",     "женщины",  ["kiteb", "ħadem", "tkellem"]),
    ("kelb",    "klieb",    "собаки",   ["kiel", "raqad"]),
    ("qattus",  "qtates",   "коты",     ["raqad", "kiel"]),
    ("student", "studenti", "студенты", ["kiteb", "tgħallem"]),
]


def article_for(stem):
    """Definite article form, used for singular and plural stems alike.

    l-    before a vowel and before għ
    l-i   before s + consonant (l-iskola, l-isptar, l-istudent)
    iX-   assimilated to the following sun letter (it-tifel, ix-xemx)
    il-   otherwise
    """
    if not stem:
        return "il-"
    low = stem.lower()
    first = low[0]
    if first in "aeiouàèìòù" or low.startswith("għ"):
        return "l-"
    if first == "s" and len(low) > 1 and low[1] not in "aeiouàèìòù":
        return "l-i"
    if first in SUN:
        return "i" + first + "-"
    return "il-"


def load_words():
    text = open(os.path.join(ROOT, "data/words.js"), encoding="utf-8").read()
    body = re.search(r"=\s*\[(.*)\]\s*;?\s*$", text, re.S).group(1)
    out = []
    for m in re.finditer(r"\{([^{}]*)\}", body, re.S):
        rec = {}
        for fm in re.finditer(r'(\w+):\s*"((?:[^"\\]|\\.)*)"', m.group(1)):
            rec[fm.group(1)] = fm.group(2).replace('\\"', '"')
        if rec:
            out.append(rec)
    return out


def validate_articles(words):
    bad = []
    for w in words:
        if w.get("pos") != "noun" or not w.get("art"):
            continue
        expected = article_for(w["mt"]) + w["mt"]
        if expected != w["art"]:
            bad.append((w["mt"], w["art"], expected))
    return bad


def main():
    words = load_words()
    by_mt = {w["mt"]: w for w in words}

    bad = validate_articles(words)
    print("проверка правила артикля: %d существительных" % sum(
        1 for w in words if w.get("pos") == "noun" and w.get("art")))
    if bad:
        print("  расхождений: %d" % len(bad))
        for mt, have, got in bad[:20]:
            print("    %-12s в словаре %-12s правило даёт %s" % (mt, have, got))
    else:
        print("  расхождений нет — правило воспроизводит все артикли словаря")

    if "--check" in sys.argv:
        return 1 if bad else 0

    items = []

    def add(noun_mt, verb_mt, number, plural_form=None, ru_plural=None):
        noun = by_mt.get(noun_mt)
        verb = by_mt.get(verb_mt)
        if not noun or not verb or not verb.get("pres"):
            print("  пропуск: %s + %s" % (noun_mt, verb_mt), file=sys.stderr)
            return
        forms = [f.strip() for f in verb["pres"].split(",")]
        if len(forms) != 3:
            print("  пропуск (нет парадигмы): %s" % verb_mt, file=sys.stderr)
            return

        if number == "sg":
            stem = noun["mt"]
            subject = noun["art"]
            gender = noun.get("g")
            ru_noun = noun["ru"].split(",")[0].split(";")[0].strip()
            ru_noun = re.sub(r"\s*\([^)]*\)", "", ru_noun)
            form = forms[0] if gender == "m" else forms[1]
            ru_subject = ru_noun
        else:
            stem = plural_form
            subject = article_for(stem) + stem
            gender = "pl"
            form = forms[2]
            ru_subject = ru_plural

        items.append({
            "subject": subject,
            "verbMt": verb["mt"],
            "nounRu": ru_subject,
            "verbRu": re.sub(r"\s*\([^)]*\)", "",
                             verb["ru"].split(",")[0].split(";")[0].strip()),
            "phrase": "%s %s." % (subject[0].upper() + subject[1:], form),
            "ru": "%s %s." % (ru_subject[0].upper() + ru_subject[1:],
                             RU_V[verb_mt][0 if number == "sg" else 1]),
            "noun": noun_mt,
            "verb": verb_mt,
            "number": number,
            "gender": gender,
            "form": form,
            "forms": forms,
        })

    for verb_mt, nouns in PAIRS:
        for noun_mt in nouns:
            add(noun_mt, verb_mt, "sg")

    for noun_mt, plural, ru_plural, verbs in PLURALS:
        for verb_mt in verbs:
            add(noun_mt, verb_mt, "pl", plural, ru_plural)

    # уникальность по фразе
    seen, final = set(), []
    for it in items:
        if it["phrase"] in seen:
            continue
        seen.add(it["phrase"])
        final.append(it)

    if "--sample" in sys.argv:
        print()
        print("примеры упражнений (%d всего, показаны первые 20):" % len(final))
        print()
        for it in final[:20]:
            print("  %s" % it["phrase"])
            print("     род: %s   форма: %s   перевод: %s" % (
                {"m": "м. род", "f": "ж. род", "pl": "мн. ч."}[it["gender"]],
                it["form"], it["ru"]))
            print("     выбор: %s" % " / ".join(it["forms"]))
            print()
        return 0

    lines = ["window.PAIRS = ["]
    for it in final:
        lines.append("  " + json.dumps(it, ensure_ascii=False) + ",")
    lines.append("];")
    with open(os.path.join(ROOT, TARGET), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("записано %s: %d упражнений" % (TARGET, len(final)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
