#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Трассировка требований: specs/ <-> код.

Для каждого требования из specs/ ищет способ проверки:

  тест      подпись check("REQ-...") в tests/smoke.py — проверка в браузере
  инструмент  упоминание в tools/*.py — проверка данных или парадигм
  конвейер    упоминание в bin/deploy — шаг публикации

Падает, если:
  * у требования нет ни одного способа проверки;
  * есть проверка без требования;
  * идентификатор объявлен дважды.

Запускается как отдельный шаг и первым делом в bin/deploy.

    python3 tools/check_specs.py
"""

import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPECS = os.path.join(ROOT, "specs")
SMOKE = os.path.join(ROOT, "tests", "smoke.py")

REQ = re.compile(r"\bREQ-[A-Z]+-\d+\b")
SPEC_HEAD = re.compile(r"^###\s+(REQ-[A-Z]+-\d+)\s+—\s+(.+)$")
# только вызовы нашей проверки, не page.check(...)
TEST_LABEL = re.compile(r'(?<!\.)\bcheck\("(REQ-[A-Z]+-\d+)([^"]*)"')


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def spec_requirements():
    """{req: (файл, формулировка)} + список дублей."""
    found, dupes = {}, []
    for name in sorted(os.listdir(SPECS)):
        if not name.endswith(".md") or name == "README.md":
            continue
        for line in read(os.path.join(SPECS, name)).splitlines():
            m = SPEC_HEAD.match(line.strip())
            if not m:
                continue
            rid, title = m.group(1), m.group(2).strip()
            if rid in found:
                dupes.append((rid, found[rid][0], name))
            found[rid] = (name, title)
    return found, dupes


def test_checks():
    """{req: [подписи]} из tests/smoke.py."""
    out = defaultdict(list)
    for m in TEST_LABEL.finditer(read(SMOKE)):
        out[m.group(1)].append(m.group(2).strip())
    return out


def tool_checks():
    """{req: {файл}} из tools/ и bin/."""
    out = defaultdict(set)
    for d in ("tools", "bin"):
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            path = os.path.join(base, name)
            if not os.path.isfile(path):
                continue
            for rid in REQ.findall(read(path)):
                out[rid].add(name)
    return out


def unlabeled_checks():
    """Вызовы check() без идентификатора требования."""
    out = []
    for m in re.finditer(r'(?<!\.)\bcheck\("([^"]+)"', read(SMOKE)):
        if not m.group(1).startswith("REQ-"):
            out.append(m.group(1))
    return out


def main():
    specs, dupes = spec_requirements()
    tests = test_checks()
    tools = tool_checks()

    by_area = defaultdict(list)
    problems = []

    for rid, (fname, title) in sorted(specs.items()):
        n_tests = len(tests.get(rid, []))
        n_tools = len(tools.get(rid, set()))
        if n_tests:
            how = "тест" if n_tools == 0 else "тест+инструмент"
        elif n_tools:
            how = "инструмент" if "deploy" not in tools[rid] else "конвейер"
        else:
            how = "НЕТ"
            problems.append("требование %s (%s) не проверяется ничем" % (rid, title))
        by_area[rid.split("-")[1]].append((rid, n_tests, how))

    for rid, a, b in dupes:
        problems.append("идентификатор %s объявлен дважды: %s и %s" % (rid, a, b))

    for rid in sorted(set(tests) - set(specs)):
        problems.append("проверка %s есть в тестах, но требования нет" % rid)
    for rid in sorted(set(tools) - set(specs)):
        problems.append("идентификатор %s упомянут в %s, но требования нет"
                        % (rid, ", ".join(sorted(tools[rid]))))

    for label in unlabeled_checks():
        problems.append("проверка без требования: «%s»" % label)

    total_checks = sum(len(v) for v in tests.values())
    print("требований: %d | проверок в тестах: %d | файлов-инструментов: %d"
          % (len(specs), total_checks, len({f for s in tools.values() for f in s})))
    print()
    print("%-9s %-6s %-16s %s" % ("область", "всего", "способ", "требования без проверки"))
    for area in sorted(by_area):
        items = by_area[area]
        empty = [r for r, n, h in items if h == "НЕТ"]
        how = defaultdict(int)
        for _, _, h in items:
            how[h] += 1
        print("%-9s %-6d %-16s %s" % (
            area, len(items),
            ", ".join("%s:%d" % (k, v) for k, v in sorted(how.items())),
            ", ".join(empty) if empty else "нет"))
    print()

    if problems:
        for p in problems:
            print("  " + p)
        print()
        print("трассировка нарушена: %d проблем" % len(problems))
        return 1

    print("покрытие полное: каждое требование проверяется, лишних проверок нет")
    return 0


if __name__ == "__main__":
    sys.exit(main())
