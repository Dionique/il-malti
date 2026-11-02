#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Обновить парадигмы глаголов в data/words.js по verb.mt.

Что делает:
  * берёт со страницы глагола имперфетт (7 лиц, положительная форма);
  * записывает их в поле pres в порядке 1s,2s,3m,3f,1p,2p,3p;
  * глаголы, которых на сайте нет, не трогает;
  * «noqgħod» — это форма, а не слово: заменяется на словарную статью qagħad.

    python3 tools/update_verbs_from_verbmt.py --dry   # показать, что изменится
    python3 tools/update_verbs_from_verbmt.py         # записать

Источник форм: verb.mt — конъюгатор «Għidha bil-Malti» (Reuben De Giorgio),
при поддержке Aġenzija Nazzjonali tal-Litteriżmu.
"""

import importlib.util
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORDS = os.path.join(ROOT, "data/words.js")

# глаголы, где сайт расходится с общепринятой формой — оставляем нашу
KEEP_OURS = {"qara": "сайт даёт jqari, общепринято jaqra"}

# словарная статья, которой на сайте нет, но она нужна как слово
NEW_ENTRIES = {
    "qagħad": '  { mt: "qagħad",   ru: "оставаться, жить",        topic: "verb", pos: "verb", forms: "joqgħod", pres: "%s" },',
}


def load_checker():
    path = os.path.join(ROOT, "tools/check_verbs_against_verbmt.py")
    spec = importlib.util.spec_from_file_location("chk", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def norm(text):
    """апостроф сайта -> наш, чтобы сравнение не спотыкалось."""
    return text.replace("\u2019", "'").replace("\u02bc", "'").strip()


def main():
    dry = "--dry" in sys.argv
    chk = load_checker()

    lines = open(WORDS, encoding="utf-8").read().split("\n")
    changed, kept, missing = [], [], []

    for i, line in enumerate(lines):
        m = re.search(r'\{ mt: "([^"]+)"', line)
        if not m or 'pos: "verb"' not in line:
            continue
        verb = m.group(1)
        if verb in KEEP_OURS:
            kept.append((verb, KEEP_OURS[verb]))
            continue
        url, html = chk.page_url(verb)
        if not html:
            missing.append(verb)
            continue
        forms = [norm(f) for f in chk.imperfect(html)]
        if len(forms) != 7:
            missing.append(verb)
            continue
        new_pres = ", ".join(forms)
        old = re.search(r'pres: "([^"]*)"', line)
        old_pres = old.group(1) if old else None
        if old_pres == new_pres:
            continue
        changed.append((verb, old_pres, new_pres))
        if not dry:
            if old:
                lines[i] = re.sub(r'pres: "[^"]*"', 'pres: "%s"' % new_pres, line)
            else:
                lines[i] = line.replace(" }", ', pres: "%s" }' % new_pres, 1)

    # «noqgħod» — форма глагола qagħad, а не отдельное слово
    replaced = False
    for i, line in enumerate(lines):
        if re.search(r'\{ mt: "noqgħod"', line):
            qaghad = None
            for verb, old, new in changed:
                if verb == "qagħad":
                    qaghad = new
            if qaghad is None:
                url, html = chk.page_url("qagħad")
                qaghad = ", ".join(norm(f) for f in chk.imperfect(html)) if html else None
            if qaghad:
                lines[i] = NEW_ENTRIES["qagħad"] % qaghad
                replaced = True
            break

    print("обновлено парадигм: %d" % len(changed))
    for verb, old, new in changed:
        print("  %-9s %s" % (verb, new))
        if old:
            print("            было: %s" % old)
    print("оставлено нашим: %d %s" % (len(kept), [k for k, _ in kept]))
    print("нет на сайте (не тронуты): %d %s" % (len(missing), missing))
    print("noqgħod → qagħad: %s" % ("да" if replaced else "нет"))

    if dry:
        print("\n(сухой прогон, файл не изменён)")
        return 0
    open(WORDS, "w", encoding="utf-8").write("\n".join(lines))
    print("\nзаписано %s" % os.path.relpath(WORDS, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
