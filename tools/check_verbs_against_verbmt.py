#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сверить спряжение глаголов словаря с verb.mt (конъюгатор «Għidha bil-Malti»).

Читает data/words.js, находит страницу глагола на verb.mt и сравнивает
имперфетт (настоящее время), положительную форму: 3m, 3f, 3p — то, что
хранится в поле pres.

    python3 tools/check_verbs_against_verbmt.py            # только расхождения
    python3 tools/check_verbs_against_verbmt.py --full     # все глаголы
    python3 tools/check_verbs_against_verbmt.py --forms ħa # показать все 7 лиц

Сеть: сайт чужой, поэтому запросы идут по одному с паузой.
"""

import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://verb.mt"
UA = "Mozilla/5.0 (compatible; il-malti check; +https://github.com/Dionique/il-malti)"
PERSONS = ["1s", "2s", "3m", "3f", "1p", "2p", "3p"]

# первая буква -> каталоги на сайте (għerq и zokk); «għ» — две буквы
DIRS = {
    "a": ["a"], "b": ["b", "b2"], "ċ": ["c", "c2"], "d": ["d", "d2"],
    "e": ["e"], "f": ["f", "f2"], "ġ": ["g", "g2"], "g": ["ge", "ge2"],
    "għ": ["gh"], "h": ["h"], "ħ": ["he"], "i": ["i"], "j": ["j"],
    "k": ["k", "k2"], "l": ["l", "l2"], "m": ["m1", "m2"], "n": ["n", "n2"],
    "o": ["o"], "p": ["p1", "p2"], "q": ["q"], "r": ["r", "r2"],
    "s": ["s1", "s2"], "t": ["t", "t2"], "u": ["u"], "v": ["v", "v2"],
    "w": ["w"], "x": ["x", "x2"], "ż": ["z", "z2"], "z": ["ze"],
}


def translit(text):
    """мальтийская буква -> латиница для адреса страницы."""
    out = text.lower()
    for src, dst in (("għ", "gh"), ("ħ", "h"), ("ġ", "g"), ("ż", "z"), ("ċ", "c"),
                     ("à", "a"), ("è", "e"), ("ì", "i"), ("ò", "o"), ("ù", "u")):
        out = out.replace(src, dst)
    return re.sub(r"[^a-z'-]", "", out)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", errors="replace")


def paras(html):
    """все <p>…</p> в порядке следования, без разметки."""
    return [re.sub(r"<[^>]+>", "", p).strip()
            for p in re.findall(r"<p[^>]*>(.*?)</p>", html, re.S)]


def imperfect(html):
    """7 форм положительного имперфетта со страницы verb.mt.

    Разметка — не таблица, а плоские <p>: сначала идёт имперфетт, поэтому
    первый «pożittiv» на странице — это он («imperfett» — заголовок, не <p>).
    """
    items = paras(html)
    for i, text in enumerate(items):
        if text == "pożittiv":
            forms = items[i + 1:i + 8]
            if len(forms) == 7 and all(f and f.isprintable() for f in forms):
                return forms
    return None


def page_url(verb):
    """пробуем каталоги по первой букве (у «għ» их один, у «m» — два)."""
    first = "għ" if verb.startswith("għ") else verb[0]
    for d in DIRS.get(first, []):
        url = "%s/%s/%s" % (BASE, d, urllib.parse.quote(translit(verb)))
        try:
            html = fetch(url)
        except urllib.error.HTTPError:
            continue
        time.sleep(0.6)
        if imperfect(html):
            return url, html
    return None, None


def main():
    full = "--full" in sys.argv
    show = sys.argv[sys.argv.index("--forms") + 1] if "--forms" in sys.argv else None

    words = {}
    for line in open(os.path.join(ROOT, "data/words.js"), encoding="utf-8"):
        m = re.search(r'\{ mt: "([^"]+)"', line)
        if not m or 'pos: "verb"' not in line:
            continue
        p = re.search(r'pres: "([^"]*)"', line)
        words[m.group(1)] = [x.strip() for x in p.group(1).split(",")] if p else []

    print("глаголов в словаре: %d" % len(words))
    if show:
        url, html = page_url(show)
        if not html:
            print("  страница не найдена: %s" % show)
            return 1
        forms = imperfect(html)
        print("  %s — %s" % (show, url))
        for p, f in zip(PERSONS, forms):
            print("     %-3s %s" % (p, f))
        return 0

    ok = miss = bad = 0
    for verb, ours in words.items():
        url, html = page_url(verb)
        if not html:
            miss += 1
            print("  нет на сайте:  %-10s (у нас %s)" % (verb, ", ".join(ours) or "—"))
            continue
        site = imperfect(html)
        ours3 = ours
        site3 = [site[2], site[3], site[6]]
        if ours3 and ours3 == site3:
            ok += 1
            if full:
                print("  совпало:       %-10s %s" % (verb, ", ".join(site3)))
        elif not ours3:
            ok += 1
            print("  без pres:      %-10s на сайте: %s" % (verb, ", ".join(site3)))
        else:
            bad += 1
            print("  РАСХОЖДЕНИЕ:   %-10s у нас %-28s сайт %s"
                  % (verb, ", ".join(ours3), ", ".join(site3)))
    print()
    print("совпало: %d | нет на сайте: %d | расхождений: %d" % (ok, miss, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
