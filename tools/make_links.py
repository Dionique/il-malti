#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Link every sentence to the vocabulary entries it uses.

Reads data/words.js and data/sentences.js, matches each token of each sentence
against the word list (inflected forms, plurals, article forms and the alias
table below) and writes data/links.js:

    window.SENTENCE_LINKS = {
      "Minn fejn int?": { words: ["minn fejn", "fejn", "int"], unknown: [] },
      ...
    }

`words` holds the `mt` values of matched vocabulary entries, `unknown` the
tokens that could not be matched (they are reported to stderr as well).

Usage:
    python3 tools/make_links.py            # write data/links.js
    python3 tools/make_links.py --report   # only print the unmatched tokens
"""

import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = ["data/words.js", "data/sentences.js"]
TARGET = "data/links.js"

# Inflected forms met in the sentences that are not listed in the word entry.
# Left side: the form found in a sentence. Right side: the `mt` of the entry.
ALIASES = {
    # verbs, 1st/2nd/3rd person present
    "nixrob": "xorob", "tixrob": "xorob",
    "niekol": "kiel", "tiekol": "kiel",
    "nara": "ra", "tara": "ra", "narak": "ra", "rajt": "ra", "rajna": "ra",
    "naqra": "qara",
    "naħdem": "ħadem", "taħdem": "ħadem", "jaħdem": "ħadem",
    "nitkellem": "tkellem", "titkellem": "tkellem", "tkellmu": "tkellem",
    "nitgħallmu": "tgħallem", "titgħallem": "tgħallem",
    "nistudja": "tgħallem",
    "jgħix": "għex", "jgħixu": "għex",
    "mmorru": "mar", "tmur": "mar", "mur": "mar",
    "nistax": "seta'", "tista'": "seta'",
    "tagħmel": "għamel", "nagħmel": "għamel",
    "tgħid": "qal", "ngħid": "qal",
    "trid": "ried", "tridu": "ried", "irrid": "ried", "irridu": "ried",
    "nixtieq": "ried", "jixtieq": "ried",
    "taf": "jaf", "naf": "jaf", "nafx": "jaf",
    "nifhimx": "fehem",
    "jismek": "sema'", "jisimni": "isem",
    "aqleb": "qaleb",
    "agħtini": "ta",
    # притяжательные формы (суффикс -i "мой")
    "ommi": "omm", "missieri": "missier", "oħti": "oħt", "ħija": "ħu",
    # женский род и числительные в конструкте
    "kbira": "kbir", "ħelwa": "ħelu",
    "żewġt": "tnejn", "itfal": "tifel",
    "ħames": "ħamsa", "għaxar": "għaxra",
    # прочее
    "banju": "kamra",
    # "иметь": вся парадигма għandi / għandek / ... -> kellu
    "għandi": "kellu", "għandek": "kellu", "għandu": "kellu",
    "għandha": "kellu", "għandna": "kellu", "għandhom": "kellu",
    "m'għandix": "kellu",
    # варианты местоимений
    "huwa": "hu", "hija": "hi",
    # наречия и служебные слова
    "illum": "llum",
    # варианты из живых фраз
    "vera": "veru",
    # формы из диалогов
    "wasalna": "wasal",
    "imur": "mar",
    "jogħġbok": "jekk jogħġbok",
    "insarraf": "sarraf",
    "tliet": "tlieta",
    "x'": "xiex",
    "mitt": "mija",
    "tgħin": "għen",
    "jgħin": "għen",
    "rasi": "ras",
    "tiġi": "ġie",
    "inhi": "hi",
    "jisimni": "isem",
    "jismek": "sema'",
    "żewġ": "tnejn",
    "immur": "mar",
    "qtates": "qattus",
    "għaxart": "għaxra",
    "nixrobx": "xorob",
    "tixrobx": "xorob",
    # Названия дней. Оставляем только формы, которые иначе свяжутся не с тем
    # словом: «t-tlieta» похоже на число «tlieta». Для «l-ġimgħa» алиаса НЕТ:
    # это омоним, «l-ġimgħa» — и пятница, и определённая форма слова «неделя».
    "t-tnejn": "it-Tnejn",
    "l-ħamis": "il-Ħamis",
    # язык и страны
    "malti": "Malti", "bil-malti": "Malti", "l-malti": "Malti",
    "maltija": "Malti",
    "bl-ingliż": "Ingliż", "ingliż": "Ingliż",
    "il-malta": "Malta", "malta": "Malta",
    "russja": "Russja",
}

# Forms that are function words / particles / proper names and carry no item.
IGNORED = {
    "ma", "m'", "qed", "l", "il", "ta", "ta'", "fi", "f'", "bil", "bl",
    "minn", "li", "biex", "sa", "ġo", "fuq", "taħt", "ma'",
    "anna", "birkirkara", "f'birkirkara", "pawlu", "anna ivanova",
}

# Prefixes attached with a hyphen (il-ħobż, is-sinjura, fil-kamra).
CLITICS = {
    "il", "l", "is", "ix", "iċ", "iż", "id", "in", "ir", "it", "iz",
    "bil", "bl", "fil", "tal", "mal", "lis", "lil",
}

VOWELS = "aeiouàèìòù"

PUNCT = re.compile(r"^[«\"'(\[]+|[»\".,!?;:)\]]+$")


def load(path, varname):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        text = fh.read()
    body = re.search(r"=\s*\[(.*)\]\s*;?\s*$", text, re.S)
    if not body:
        raise SystemExit("cannot parse %s" % path)
    items = []
    for m in re.finditer(r'\{([^{}]*)\}', body.group(1), re.S):
        rec = {}
        for fm in re.finditer(r'(\w+):\s*"((?:[^"\\]|\\.)*)"', m.group(1)):
            rec[fm.group(1)] = fm.group(2).replace('\\"', '"')
        if rec:
            items.append(rec)
    return items


def tokens(sentence):
    out = []
    for raw in sentence.split():
        tok = PUNCT.sub("", raw).strip()
        if tok:
            out.append(tok)
    return out


def forms_of(entry):
    """All surface forms of a vocabulary entry."""
    out = set()
    base = entry["mt"]
    out.add(base)
    if entry.get("pl"):
        out.add(entry["pl"])
    if entry.get("art"):
        out.add(entry["art"])
    if entry.get("forms"):
        for part in entry["forms"].split(","):
            out.add(part.strip())
    return {f for f in out if f}


def strip_clitic(token):
    """il-ħobż -> ħobż, fil-kamra -> kamra; keeps the original too."""
    out = {token}
    if "-" in token:
        head, _, tail = token.partition("-")
        if tail:
            out.add(tail)
            if head in CLITICS:
                out.add(tail)
    if "'" in token:
        _, _, tail = token.partition("'")
        if tail:
            out.add(tail)
    return out


def build_index(words):
    index = {}
    for w in words:
        for form in forms_of(w):
            index.setdefault(form.lower(), w["mt"])
    for form, target in ALIASES.items():
        index.setdefault(form.lower(), target)
    return index


def main():
    report_only = "--report" in sys.argv
    words = load("data/words.js", "WORDS")
    sentences = load("data/sentences.js", "SENTENCES")
    index = build_index(words)
    known_targets = {w["mt"] for w in words}

    links = {}
    unmatched = Counter()
    per_sentence = []

    for s in sentences:
        raw = s["mt"].split(" ")
        cleaned = [PUNCT.sub("", p).strip() for p in raw]
        matched, unknown = [], []
        positions = {}

        def record(hit, idx):
            if hit not in matched:
                matched.append(hit)
            positions.setdefault(hit, [])
            if idx not in positions[hit]:
                positions[hit].append(idx)

        i = 0
        while i < len(cleaned):
            low = cleaned[i].lower()
            if not low:
                i += 1
                continue

            # сначала пробуем словосочетание из двух токенов
            bigram = None
            if i + 1 < len(cleaned) and cleaned[i + 1]:
                bigram = low + " " + cleaned[i + 1].lower()
            hit = index.get(bigram) if bigram else None
            if hit:
                record(hit, i)
                record(hit, i + 1)
                i += 2
                continue

            hit = index.get(low)
            if not hit:
                for variant in strip_clitic(low):
                    hit = index.get(variant)
                    if hit:
                        break
            if not hit and low in IGNORED:
                i += 1
                continue
            if hit:
                record(hit, i)
            else:
                unknown.append(raw[i])
                unmatched[low] += 1
            i += 1

        links[s["mt"]] = {"words": matched, "pos": positions, "unknown": unknown}
        per_sentence.append((s["mt"], matched, unknown))

    total = sum(len(m) + len(u) for _, m, u in per_sentence)
    unknown_total = sum(len(u) for _, _, u in per_sentence)
    covered = total - unknown_total
    ratio = (covered / total * 100) if total else 0

    print("sentences          : %d" % len(sentences))
    print("tokens             : %d" % total)
    print("matched to vocab   : %d (%.1f%%)" % (covered, ratio))
    print("unmatched tokens   : %d unique %d" % (unknown_total, len(unmatched)))
    print()
    print("top unmatched (fix these with ALIASES / add to words):")
    for tok, n in unmatched.most_common(40):
        print("  %-16s %d" % (tok, n))

    empty = [mt for mt, m, _ in per_sentence if not m]
    if empty:
        print()
        print("sentences with no vocabulary at all (%d):" % len(empty))
        for mt in empty:
            print("  " + mt)

    if report_only:
        return 0

    lines = ["window.SENTENCE_LINKS = {"]
    for s in sentences:
        rec = links[s["mt"]]
        lines.append(
            "  %s: { words: %s, pos: %s, unknown: %s },"
            % (json.dumps(s["mt"], ensure_ascii=False),
               json.dumps(rec["words"], ensure_ascii=False),
               json.dumps(rec["pos"], ensure_ascii=False),
               json.dumps(rec["unknown"], ensure_ascii=False))
        )
    lines.append("};")
    with open(os.path.join(ROOT, TARGET), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print()
    print("wrote %s" % TARGET)
    # REQ-DATA-04: связи фраз со словарём; REQ-SENT-01 зависит от результата

    missing = [w for w in links.values() for w in w["words"] if w not in known_targets]
    if missing:
        print("WARNING: links point to unknown entries: %s" % sorted(set(missing)))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
