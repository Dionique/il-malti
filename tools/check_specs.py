#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Трассировка требований: specs/ <-> тесты и инструменты.

Проверяет, что в проекте нет:
  * требований без проверки — записали в specs/, но нигде не проверяем;
  * проверок без требования — тест есть, а требования под него нет;
  * повторяющихся идентификаторов.

Идентификатор считается упомянутым, если он встречается в подписи проверки
(tests/smoke.py) или в тексте инструмента (tools/, bin/).

    python3 tools/check_specs.py
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPECS = os.path.join(ROOT, "specs")
CODE_DIRS = ["tests", "tools", "bin", "deploy"]

REQ = re.compile(r"\bREQ-[A-Z]+-\d+\b")


def spec_ids():
    """Все идентификаторы, объявленные в заголовках спецификаций."""
    found = {}
    dupes = []
    for name in sorted(os.listdir(SPECS)):
        if not name.endswith(".md") or name == "README.md":
            continue
        path = os.path.join(SPECS, name)
        for line in open(path, encoding="utf-8"):
            m = re.match(r"^###\s+(REQ-[A-Z]+-\d+)\b", line.strip())
            if m:
                rid = m.group(1)
                if rid in found:
                    dupes.append((rid, found[rid], name))
                found[rid] = name
    return found, dupes


def code_mentions():
    """Идентификаторы, упомянутые в коде проверок."""
    found = {}
    for d in CODE_DIRS:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for root, _, files in os.walk(base):
            for f in files:
                path = os.path.join(root, f)
                try:
                    text = open(path, encoding="utf-8").read()
                except (UnicodeDecodeError, IsADirectoryError):
                    continue
                for rid in REQ.findall(text):
                    found.setdefault(rid, set()).add(os.path.relpath(path, ROOT))
    return found


def main():
    specs, dupes = spec_ids()
    code = code_mentions()

    print("требований в specs/: %d" % len(specs))
    print("идентификаторов в коде: %d" % len(code))

    problems = []

    if dupes:
        for rid, a, b in dupes:
            problems.append("идентификатор %s объявлен дважды: %s и %s" % (rid, a, b))

    orphan_reqs = sorted(set(specs) - set(code))
    if orphan_reqs:
        for rid in orphan_reqs:
            problems.append("требование %s (%s) нигде не проверяется" % (rid, specs[rid]))

    orphan_tests = sorted(set(code) - set(specs))
    if orphan_tests:
        for rid in orphan_tests:
            problems.append("проверка %s есть в %s, но требования нет"
                            % (rid, ", ".join(sorted(code[rid]))))

    if problems:
        print()
        for p in problems:
            print("  " + p)
        print()
        print("трассировка нарушена: %d проблем" % len(problems))
        return 1

    print("трассировка в порядке: каждое требование проверяется, лишних нет")
    return 0


if __name__ == "__main__":
    sys.exit(main())
