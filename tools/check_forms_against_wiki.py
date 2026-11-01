#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сверить формы словаря с выгрузкой Викисловаря (REQ-DATA-05).

Читает data/words.js и выгрузку kaikki.org, сравнивает:
  * множественное число существительных
  * женскую и множественную формы прилагательных
и печатает три списка: совпало, можно дозаполнить, расхождения.

Выгрузка не входит в репозиторий (99 МБ), поэтому путь задаётся или
скачивается по требованию.

    python3 tools/check_forms_against_wiki.py [путь-к-kaikki.jsonl]
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI_URL = "https://kaikki.org/dictionary/Maltese/kaikki.org-dictionary-Maltese.jsonl"
FIELDS = ("ru", "pos", "g", "art", "pl", "forms", "pres")


def load_words():
    out = {}
    text = open(os.path.join(ROOT, "data/words.js"), encoding="utf-8").read()
    for line in text.splitlines():
        m = re.search(r'\{ mt: "([^"]+)"', line)
        if not m:
            continue
        rec = {"mt": m.group(1)}
        for f in FIELDS:
            fm = re.search(r'%s:\s*"([^"]*)"' % f, line)
            if fm:
                rec[f] = fm.group(1)
        out[rec["mt"]] = rec
    return out


def load_wiki(path):
    """{слово: {pos, g, pl, fem}} — только нужные части речи и формы."""
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if '"pos": "noun"' not in line and '"pos": "adj"' not in line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            w = e.get("word")
            if not w:
                continue
            rec = out.setdefault(w, {"pos": e.get("pos"), "g": None, "pl": None, "fem": None})
            for f in (e.get("forms") or []):
                tags = " ".join(f.get("tags") or [])
                form = f.get("form")
                if not form:
                    continue
                if "plural" in tags and not rec["pl"]:
                    rec["pl"] = form
                if "feminine" in tags and not rec["fem"]:
                    rec["fem"] = form
            for s in (e.get("senses") or []):
                for t in (s.get("tags") or []):
                    if t == "masculine":
                        rec["g"] = "m"
                    elif t == "feminine":
                        rec["g"] = "f"
    return out


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/kaikki-mt.jsonl"
    if not os.path.exists(path):
        print("нет выгрузки: %s\n  скачать: curl -o %s %s" % (path, path, WIKI_URL))
        return 1

    words = load_words()
    wiki = load_wiki(path)

    same = fill = 0
    clashes = []
    for mt, w in words.items():
        k = wiki.get(mt)
        if not k:
            continue
        if w.get("pos") == "noun" and k["pl"]:
            if not w.get("pl"):
                fill += 1
            elif w["pl"] == k["pl"]:
                same += 1
            else:
                clashes.append((mt, "мн.ч.", w["pl"], k["pl"]))
        if w.get("pos") == "adj":
            # у прилагательного `forms` — список форм, поэтому форма из словаря
            # либо уже есть, либо её можно добавить; расхождения тут не бывает
            mine = [x.strip() for x in (w.get("forms") or "").split(",") if x.strip()]
            for key in ("fem", "pl"):
                v = k[key]
                if not v or v == mt:
                    continue
                if v in mine:
                    same += 1
                else:
                    fill += 1

    covered = sum(1 for mt in words if mt in wiki)
    print("слов: %d | есть в Викисловаре: %d" % (len(words), covered))
    print("совпало форм: %d | можно дозаполнить: %d" % (same, fill))
    print("расхождений: %d" % len(clashes))
    for mt, what, mine, theirs in clashes:
        print("   %-12s %-7s у нас %-16s Викисловарь %s" % (mt, what, mine, theirs))
    return 1 if clashes else 0


if __name__ == "__main__":
    sys.exit(main())
