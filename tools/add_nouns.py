#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Добавить в data/words.js слова учителя: единственное и множественное число.

Источники:
  * список пар — от учителя (папка /tmp/nouns/list.txt);
  * переводы — Google Translate, проверены Gemini и Викисловарём;
  * род — Викисловарь, где нет — по окончанию (слова на -a женские);
  * артикль — по правилу из tools/make_forms.py (то же, что проверяется тестом);
  * женские формы прилагательных — Викисловарь и Gemini.

    python3 tools/add_nouns.py --dry   # показать записи
    python3 tools/add_nouns.py         # дописать в data/words.js
"""

import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORDS = os.path.join(ROOT, "data/words.js")

# (mt, pl, ru, род) — существительные
NOUNS = [
    ("baħri", "baħrin", "моряк", "m"),
    ("bniedem", "bnedmin", "человек", "m"),
    ("qassis", "qassisin", "священник", "m"),
    ("Mellieħi", "Mellieħin", "житель Меллехьи", "m"),
    ("Żebbuġi", "Żebbuġin", "житель Зеббуджа", "m"),
    ("Għawdxi", "Għawdxin", "гозитянин", "m"),
    ("Naxxari", "Naxxarin", "житель Нашшара", "m"),
    ("Mosti", "Mostin", "житель Мосты", "m"),
    ("Belti", "Beltin", "житель Валлетты", "m"),
    ("papra", "papri", "утка", "f"),
    ("ġgant", "ġganti", "великан", "m"),
    ("lista", "listi", "список", "f"),
    ("naspla", "naspli", "мушмула", "f"),
    ("pastizz", "pastizzi", "мальтийский пирожок", "m"),
    ("perit", "periti", "мастер, техник", "m"),
    ("periklu", "perikli", "опасность", "m"),
    ("peduna", "peduni", "носок", "f"),
    ("kalzetta", "kalzetti", "носок", "f"),
    ("pavaljun", "pavaljuni", "павильон", "m"),
    ("pass", "passi", "шаг", "m"),
    ("pakkett", "pakketti", "пакет, посылка", "m"),
    ("platt", "platti", "тарелка", "m"),
    ("presepju", "presepji", "вертеп", "m"),
    ("xadin", "xadini", "обезьяна", "m"),
    ("valur", "valuri", "ценность", "m"),
    ("tank", "tankijiet", "бак, танк", "m"),
    ("klassi", "klassijiet", "класс", "f"),
    ("kok", "kokijiet", "повар", "m"),
    ("pin", "pinnijiet", "булавка", "m"),
    ("fann", "fannijiet", "вентилятор, веер", "m"),
    ("friġġ", "friġġijiet", "холодильник", "m"),
    ("żrinġ", "żrinġijiet", "лягушка", "m"),
    ("attitudni", "attitudnijiet", "отношение", "f"),
    ("attivita", "attivitajiet", "деятельность", "f"),
    ("diffikulta", "diffikultajiet", "трудность", "f"),
    ("opportunita", "opportunitajiet", "возможность", "f"),
    ("responsabbiltà", "responsabbiltajiet", "ответственность", "f"),
    ("kwalità", "kwalitajiet", "качество", "f"),
    ("komunità", "komunitajiet", "сообщество", "f"),
    ("awtorità", "awtoritajiet", "власть", "f"),
    ("personalità", "personalitajiet", "личность", "f"),
    ("identità", "identitajiet", "идентичность", "f"),
    ("possibbiltà", "possibbiltajiet", "возможность", "f"),
    ("prijorità", "prijoritajiet", "приоритет", "f"),
    ("basket", "basktijiet", "баскетбол", "m"),
    ("ġlekk", "ġlekkijiet", "куртка", "m"),
    ("ganċ", "ganċijiet", "крючок", "m"),
    ("gvern", "gvernijiet", "правительство", "m"),
    ("gowl", "gowlijiet", "гол", "m"),
    ("għaġeb", "għeġubijiet", "удивление", "m"),
    ("imqass", "imqassijiet", "ножницы", "m"),
    ("irdum", "irdumijiet", "обрыв", "m"),
    ("interruzzjoni", "interruzzjonijiet", "перерыв", "f"),
    ("mużew", "mużewijiet", "музей", "m"),
    ("nazzjon", "nazzjonijiet", "нация", "m"),
    ("nuċċali", "nuċċalijiet", "очки", "m"),
    ("palk", "palkijiet", "сцена, подиум", "m"),
    ("premju", "premjijiet", "приз", "m"),
    ("rimm", "rimmijiet", "обод, кромка", "m"),
    ("uniformi", "uniformijiet", "форма, униформа", "f"),
    ("xelter", "xeltrijiet", "укрытие, убежище", "m"),
]

# (mt, женская форма, множественное, ru)
ADJECTIVES = [
    ("kiesaħ", "kiesħa", "kesħin", "холодный"),
    ("sbejjaħ", "sbejħa", "sbejħin", "хорошенький"),
    ("imbierek", "imbierka", "imberkin", "благословенный"),
    ("tawwali", "tawwalja", "tawwalin", "удлинённый"),
    ("imxarrab", "imxarrba", "imxarrbin", "мокрый"),
    ("imxengel", "imxengla", "imxenglin", "покачивающийся"),
    ("mgħawweġ", "mgħawġa", "mgħawġin", "согнутый, кривой"),
    ("ferħan", "ferħana", "ferħanin", "радостный"),
    ("maħmuġ", "maħmuġa", "maħmuġin", "грязный"),
    ("imqaċċat", "imqaċċata", "imqaċċtin", "обрезанный"),
]

TOPIC = "plural"   # новая тема «Единственное и множественное»


def article_for(stem):
    """то же правило, что проверяет tools/make_forms.py --check."""
    spec = importlib.util.spec_from_file_location(
        "mf", os.path.join(ROOT, "tools/make_forms.py"))
    mf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mf)
    return mf.article_for(stem)


def main():
    dry = "--dry" in sys.argv
    have = set()
    for line in open(WORDS, encoding="utf-8"):
        import re
        m = re.search(r'\{ mt: "([^"]+)"', line)
        if m:
            have.add(m.group(1))

    lines = []
    skipped = []
    fill = []
    for mt, pl, ru, g in NOUNS:
        if mt in have:
            skipped.append(mt)
            continue
        art = article_for(mt) + mt   # правило даёт приставку, в данных — форма целиком
        lines.append('    { mt: "%s",%sru: "%s",%stopic: "%s", pos: "noun", g: "%s", art: "%s", pl: "%s" },'
                     % (mt, " " * max(1, 14 - len(mt)), ru,
                        " " * max(1, 20 - len(ru)), TOPIC, g, art, pl))
    for mt, fem, pl, ru in ADJECTIVES:
        if mt in have:
            fill.append((mt, fem, pl))
            continue
        lines.append('    { mt: "%s",%sru: "%s",%stopic: "adj", pos: "adj", forms: "%s, %s" },'
                     % (mt, " " * max(1, 14 - len(mt)), ru,
                        " " * max(1, 20 - len(ru)), fem, pl))

    print("записей: %d (существительных %d, прилагательных %d)"
          % (len(lines), len(NOUNS), len(ADJECTIVES)))
    print("уже были (пропущены): %d %s" % (len(skipped), skipped))
    print()
    for l in lines:
        print("  " + l)
    if fill:
        print("дополнить формы у существующих прилагательных: %d" % len(fill))
        for mt, fem, pl in fill:
            print("  %-12s forms: \"%s, %s\"" % (mt, fem, pl))
    if dry:
        print("\n(сухой прогон, файл не изменён)")
        return 0

    text = open(WORDS, encoding="utf-8").read()
    marker = "\n];"
    assert marker in text, "не найден конец массива WORDS"
    block = ("\n    // ---- единственное и множественное: список учителя ----\n"
             + "\n".join(lines) + "\n")
    text = text.replace(marker, block + marker, 1)
    # у существующих прилагательных множественное из списка могло быть не заполнено
    import re as _re
    out = []
    for line in text.split("\n"):
        m = _re.search(r'\{ mt: "([^"]+)"', line)
        for mt, fem, pl in fill:
            if m and m.group(1) == mt and "forms:" in line:
                line = _re.sub(r'forms: "[^"]*"', 'forms: "%s, %s"' % (fem, pl), line)
        out.append(line)
    text = "\n".join(out)
    open(WORDS, "w", encoding="utf-8").write(text)
    print("\nдописано в %s" % os.path.relpath(WORDS, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
