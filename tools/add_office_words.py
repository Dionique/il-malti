#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Добавить в data/words.js слова из списка «офис и работа».

Источники:
  * список слов — от учителя;
  * род и множественное существительных — Викисловарь, где нет — по правилу
    (слова на -a, -joni, -ità женские), помечено в AGENTS.md;
  * парадигмы глаголов — конъюгатор verb.mt; у «заимствованных» глаголов
    (iċċekkja, iddiskuta, …) verb.mt их не содержит, поэтому собраны по
    образцу n-/t-/j- + основа и требуют проверки носителем;
  * артикль — по правилу из tools/make_forms.py (то же, что проверяет тест).

    python3 tools/add_office_words.py --dry
    python3 tools/add_office_words.py
"""

import importlib.util
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORDS = os.path.join(ROOT, "data/words.js")

# (mt, ru, род, множественное) — множественное None, если его нет
NOUNS = [
    ("baġit", "бюджет", "m", "baġits"),
    ("bord", "правление, совет директоров", "m", "bords"),
    ("deċiżjoni", "решение", "f", "deċiżjonijiet"),
    ("direttur", "директор", "m", "diretturi"),
    ("Ewropa", "Европа", "f", None),
    ("imejl", "электронное письмо", "m", "imejls"),
    ("istrateġija", "стратегия", "f", "istrateġiji"),
    ("kors", "курс", "m", "korsijiet"),
    ("kumpanija", "компания", "f", "kumpaniji"),
    ("maniġer", "менеджер", "m", "maniġers"),
    ("persuna", "человек", "f", "persuni"),
    ("pjan", "план", "m", "pjanijiet"),
    ("posta", "почта", "f", None),
    ("riżultat", "результат", "m", "riżultati"),
    ("sieħeb", "партнёр", "m", "sħab"),
    ("taħriġ", "обучение, тренинг", "m", None),
    ("telefown", "телефон", "m", "telefowns"),
    ("tim", "команда", "m", "tims"),
]

# (mt, ru, 3-е лицо ед. ч., семь лиц имперфетта)
VERBS = [
    ("bagħat", "отправлять", "jibgħat",
     "nibgħat, tibgħat, jibgħat, tibgħat, nibagħtu, tibagħtu, jibagħtu"),
    ("fetaħ", "открывать", "jiftaħ",
     "niftaħ, tiftaħ, jiftaħ, tiftaħ, niftħu, tiftħu, jiftħu"),
    ("ħaddem", "нанимать", "jħaddem",
     "nħaddem, tħaddem, jħaddem, tħaddem, nħaddmu, tħaddmu, jħaddmu"),
    ("mess", "касаться, наступать", "jmiss",
     "mmiss, tmiss, jmiss, tmiss, mmissu, tmissu, jmissu"),
    ("mexxa", "управлять, вести", "jmexxi",
     "mmexxi, tmexxi, jmexxi, tmexxi, mmexxu, tmexxu, jmexxu"),
    ("organizza", "организовывать", "jorganizza",
     "norganizza, torganizza, jorganizza, torganizza, norganizzaw, torganizzaw, jorganizzaw"),
    ("wasal", "прибывать", "jasal",
     "nasal, tasal, jasal, tasal, naslu, taslu, jaslu"),
    ("iċċekkja", "проверять", "jiċċekkja",
     "niċċekkja, tiċċekkja, jiċċekkja, tiċċekkja, niċċekkjaw, tiċċekkjaw, jiċċekkjaw"),
    ("iddiskuta", "обсуждать", "jiddiskuti",
     "niddiskuti, tiddiskuti, jiddiskuti, tiddiskuti, niddiskutu, tiddiskutu, jiddiskutu"),
    ("ikkomunika", "общаться", "jikkomunika",
     "nikkomunika, tikkomunika, jikkomunika, tikkomunika, nikkomunikaw, tikkomunikaw, jikkomunikaw"),
    ("iltaqa'", "встречаться", "jiltaqa'",
     "niltaqa', tiltaqa', jiltaqa', tiltaqa', niltaqgħu, tiltaqgħu, jiltaqgħu"),
    ("ippreżenta", "представлять", "jippreżenta",
     "nippreżenta, tippreżenta, jippreżenta, tippreżenta, nippreżentaw, tippreżentaw, jippreżentaw"),
    ("irċieva", "получать", "jirċievi",
     "nirċievi, tirċievi, jirċievi, tirċievi, nirċievu, tirċievu, jirċievu"),
    ("irrisponda", "отвечать", "jirrispondi",
     "nirrispondi, tirrispondi, jirrispondi, tirrispondi, nirrispondu, tirrispondu, jirrispondu"),
]

# (mt, ru, женская форма, множественное) — None, если форма не меняется
ADJECTIVES = [
    ("dieħel", "входящий, следующий", "dieħla", "dieħlin"),
    ("finanzjarju", "финансовый", "finanzjarja", "finanzjarji"),
    ("ieħor", "другой, прошлый", "oħra", "oħrajn"),
    ("internazzjonali", "международный", None, None),
    ("kull", "каждый", None, None),
]

# (mt, ru, тема)
OTHERS = [
    ("dalwaqt", "скоро", "time"),
    ("illum", "сегодня", "time"),
    ("kuljum", "каждый день", "time"),
    ("malajr", "быстро", "everyday"),
    ("bi", "с помощью, посредством", "prep"),
    ("li", "который, что", "base"),
    ("mingħand", "от (людей, компаний)", "prep"),
    ("se", "частица будущего времени", "base"),
    ("żewġ", "два (перед существительным)", "numbers"),
]

TOPIC = "office"


def article_for(stem):
    spec = importlib.util.spec_from_file_location(
        "mf", os.path.join(ROOT, "tools/make_forms.py"))
    mf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mf)
    return mf.article_for(stem)


def main():
    dry = "--dry" in sys.argv
    have = set()
    for line in open(WORDS, encoding="utf-8"):
        m = re.search(r'\{ mt: "([^"]+)"', line)
        if m:
            have.add(m.group(1))

    lines, skipped = [], []
    for mt, ru, g, pl in NOUNS:
        if mt in have:
            skipped.append(mt)
            continue
        art = article_for(mt) + mt
        tail = ', pl: "%s"' % pl if pl else ""
        lines.append('    { mt: "%s",%sru: "%s",%stopic: "%s", pos: "noun", g: "%s", art: "%s"%s },'
                     % (mt, " " * max(1, 14 - len(mt)), ru, " " * max(1, 22 - len(ru)),
                        TOPIC, g, art, tail))
    for mt, ru, form3, pres in VERBS:
        if mt in have:
            skipped.append(mt)
            continue
        lines.append('    { mt: "%s",%sru: "%s",%stopic: "verb", pos: "verb", forms: "%s", pres: "%s" },'
                     % (mt, " " * max(1, 14 - len(mt)), ru, " " * max(1, 22 - len(ru)),
                        form3, pres))
    for mt, ru, fem, pl in ADJECTIVES:
        if mt in have:
            skipped.append(mt)
            continue
        tail = ', forms: "%s, %s"' % (fem, pl) if fem and pl else ""
        lines.append('    { mt: "%s",%sru: "%s",%stopic: "adj", pos: "adj"%s },'
                     % (mt, " " * max(1, 14 - len(mt)), ru, " " * max(1, 22 - len(ru)), tail))
    for mt, ru, topic in OTHERS:
        if mt in have:
            skipped.append(mt)
            continue
        lines.append('    { mt: "%s",%sru: "%s",%stopic: "%s" },'
                     % (mt, " " * max(1, 14 - len(mt)), ru, " " * max(1, 22 - len(ru)), topic))

    print("записей: %d (сущ %d, глаг %d, прил %d, прочее %d)"
          % (len(lines), len(NOUNS), len(VERBS), len(ADJECTIVES), len(OTHERS)))
    print("уже были: %d %s" % (len(skipped), skipped))
    print()
    for l in lines:
        print("  " + l)
    if dry:
        print("\n(сухой прогон, файл не изменён)")
        return 0

    text = open(WORDS, encoding="utf-8").read()
    marker = "\n];"
    assert marker in text, "не найден конец массива WORDS"
    block = ("\n    // ---- офис и работа: список учителя ----\n"
             + "\n".join(lines) + "\n")
    open(WORDS, "w", encoding="utf-8").write(text.replace(marker, block + marker, 1))
    print("\nдописано в %s" % os.path.relpath(WORDS, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
