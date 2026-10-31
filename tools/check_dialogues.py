#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверить диалоги: у каждой реплики есть перевод и вся лексика есть в словаре.

REQ-DLG-01 (перевод у каждой реплики) и REQ-DLG-05 (лексика в словаре).

Диалоги не проходят через make_links (они не участвуют в гейте по знакомым
словам), поэтому проверяем отдельно. Разбор идёт по тексту файла, потому что
структура вложенная (у диалога есть lines), а общий загрузчик данных её не
разбирает.

    python3 tools/check_dialogues.py
"""

import importlib.util
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIALOGUES = os.path.join(ROOT, "data/dialogues.js")


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ml = load_module(os.path.join(ROOT, "tools/make_links.py"), "make_links")
    words = ml.load("data/words.js", "WORDS")
    index = ml.build_index(words)

    text = open(DIALOGUES, encoding="utf-8").read()
    mts = re.findall(r'mt:\s*"((?:[^"\\]|\\.)*)"', text)
    rus = re.findall(r'ru:\s*"((?:[^"\\]|\\.)*)"', text)

    print("реплик: %d | переводов: %d" % (len(mts), len(rus)))
    problems = []

    if len(mts) != len(rus):
        problems.append("число реплик и переводов не совпадает")
    if any(not r.strip() for r in rus):
        problems.append("есть пустые переводы")

    def known(low):
        if low in ml.IGNORED:
            return True
        if index.get(low):
            return True
        for variant in ml.strip_clitic(low):
            if index.get(variant):
                return True
        # составные через дефис проверяем по частям: dsatax-il
        if "-" in low:
            return all(known(p) for p in low.split("-") if p)
        return False

    unknown = {}
    total = 0
    for mt in mts:
        for tok in ml.tokens(mt.replace('\\"', '"')):
            total += 1
            if not known(tok.lower()):
                unknown[tok] = unknown.get(tok, 0) + 1

    print("слов в репликах: %d" % total)
    if unknown:
        problems.append("нет в словаре: " + ", ".join(sorted(unknown)))
    else:
        print("все слова диалогов есть в словаре")

    if problems:
        print()
        for p in problems:
            print("  ПРОБЛЕМА: " + p)
        return 1
    print("диалоги в порядке")
    return 0


if __name__ == "__main__":
    sys.exit(main())
