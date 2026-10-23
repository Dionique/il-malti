#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the morphology drills (`data/forms.js`).

Three exercise sets:

  agreement  [сущ] + [прил] + [глаг]  -> род, форма прил., форма глаг., перевод
             два шаблона:
               связка : Il-kamra hija kbira.      (сущ + hu/hija/huma + прил)
               глагол : It-tifel kbir jikteb.     (сущ + прил + глаг)
  plural     [сущ]                    -> форма мн. ч. и форма мн. ч. с артиклем
  prep       [предлог] + [сущ с арт.]  -> слитная форма (tal-, mis-, għall-...)

Maltese is derived from data in data/words.js (gender, article, plural,
adjective and verb forms). Russian is curated in the tables below.

Usage:
    python3 tools/make_forms.py
    python3 tools/make_forms.py --sample
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = "data/forms.js"

# Связка «быть»: hu / hija / huma
COPULA = ["hu", "hija", "huma"]

# ---- согласование: (сущ., прилаг., глагол, перевод) ------------------------
# kind "copula": прилагательное идёт после связки
COPULA_ITEMS = [
    ("kamra", "żgħir", "Комната маленькая."),
    ("kamra", "nadif", "Комната чистая."),
    ("dar", "kbir", "Дом большой."),
    ("dar", "ġdid", "Дом новый."),
    ("dar", "qadim", "Дом старый."),
    ("triq", "twil", "Дорога длинная."),
    ("triq", "qasir", "Дорога короткая."),
    ("karozza", "ġdid", "Машина новая."),
    ("karozza", "abjad", None),
    ("kċina", "nadif", "Кухня чистая."),
    ("sodda", "maħmuġ", "Кровать грязная."),
    ("mejda", "baxx", "Стол низкий."),
    ("muntanja", "għoli", "Гора высокая."),
    ("knisja", "qadim", "Церковь старая."),
    ("fjura", "sabiħ", "Цветок красивый."),
    ("sema", "ċar", "Небо ясное."),
    ("riħ", "qawwi", "Ветер сильный."),
    ("ikel", "tajjeb", "Еда хорошая."),
    ("ikel", "ħażin", "Еда плохая."),
    ("te", "sħun", "Чай горячий."),
    ("ilma", "kiesaħ", "Вода холодная."),
    ("tuffieħa", "ħelu", "Яблоко сладкое."),
    ("kafè", "morr", "Кофе горький."),
    ("laringa", "qares", "Апельсин кислый."),
    ("kelb", "kbir", "Собака большая."),
    ("qattus", "żgħir", "Кот маленький."),
    ("ħuta", "żgħir", "Рыба маленькая."),
    ("belt", "kbir", "Город большой."),
    ("kamra", "kiesaħ", "Комната холодная."),
    ("ħabib", "tajjeb", "Друг хороший."),
    ("ħabiba", "sabiħ", "Подруга красивая."),
    ("student", "ġdid", "Студент новый."),
]

# kind "verb": прилагательное перед глаголом
VERB_ITEMS = [
    ("tifel", "kbir", "kiteb", "Большой мальчик пишет."),
    ("tifla", "żgħir", "kiteb", "Маленькая девочка пишет."),
    ("tifel", "żgħir", "qara", "Маленький мальчик читает."),
    ("tifla", "kbir", "qara", "Большая девочка читает."),
    ("mara", "sabiħ", "tkellem", "Красивая женщина говорит."),
    ("raġel", "twil", "mexa", "Высокий мужчина идёт."),
    ("mara", "twil", "mexa", "Высокая женщина идёт."),
    ("tifel", "ġdid", "tgħallem", "Новый мальчик учится."),
    ("tifla", "ġdid", "tgħallem", "Новая девочка учится."),
    ("nanna", "qadim", "raqad", "Старая бабушка спит."),
    ("nanu", "qadim", "raqad", "Старый дедушка спит."),
    ("kelb", "kbir", "kiel", "Большая собака ест."),
    ("qattus", "żgħir", "xorob", "Маленький кот пьёт."),
    ("omm", "tajjeb", "sajjar", "Хорошая мама готовит."),
    ("nanna", "tajjeb", "ħasel", "Хорошая бабушка моет."),
    ("tifla", "nadif", "ħasel", "Чистая девочка моет."),
    ("mara", "ġdid", "ħadem", "Новая женщина работает."),
    ("raġel", "kbir", "ħadem", "Большой мужчина работает."),
    ("student", "ġdid", "qara", "Новый студент читает."),
    ("tifel", "twil", "mexa", "Высокий мальчик идёт."),
]

RU_PL = {
    "numru": "числа", "kulur": "цвета", "omm": "мамы", "missier": "папы",
    "tifel": "мальчики", "tifla": "девочки", "iben": "сыновья", "bint": "дочери",
    "ħu": "братья", "oħt": "сёстры", "nanu": "дедушки", "nanna": "бабушки",
    "ziju": "дяди", "zija": "тёти", "raġel": "мужчины", "mara": "женщины",
    "familja": "семьи", "ħabib": "друзья", "ħabiba": "подруги", "tuffieħa": "яблоки",
    "laringa": "апельсины", "banana": "бананы", "bajda": "яйца", "kejk": "торты",
    "jum": "дни", "lejl": "ночи", "ġimgħa": "недели", "xahar": "месяцы",
    "sena": "годы", "siegħa": "часы", "minuta": "минуты", "ras": "головы",
    "għajn": "глаза", "widna": "уши", "sinna": "зубы", "ilsien": "языки",
    "id": "руки", "riġel": "ноги", "qalb": "сердца", "wiċċ": "лица",
    "dar": "дома", "kamra": "комнаты", "kċina": "кухни", "sodda": "кровати",
    "mejda": "столы", "siġġu": "стулья", "bieb": "двери", "tieqa": "окна",
    "ċavetta": "ключи", "lampa": "лампы", "ħajt": "стены", "mera": "зеркала",
    "telefon": "телефоны", "kompjuter": "компьютеры", "kewkba": "звёзды", "baħar": "моря",
    "xmara": "реки", "muntanja": "горы", "siġra": "деревья", "fjura": "цветы",
    "kelb": "собаки", "qattus": "коты", "għasfur": "птицы", "ħuta": "рыбы",
    "żiemel": "лошади", "baqra": "коровы", "nagħġa": "овцы", "belt": "города",
    "raħal": "деревни", "triq": "улицы", "pjazza": "площади", "ħanut": "магазины",
    "suq": "рынки", "skola": "школы", "knisja": "церкви", "sptar": "больницы",
    "bank": "банки", "ristorant": "рестораны", "lukanda": "отели", "ajruport": "аэропорты",
    "gżira": "острова", "karozza": "машины", "xarabank": "автобусы", "ajruplan": "самолёты",
    "vapur": "корабли", "rota": "велосипеды", "ferrovija": "поезда", "biljett": "билеты",
    "vjaġġ": "поездки", "bagalja": "чемоданы", "ktieb": "книги", "ittra": "письма",
    "isem": "имена", "film": "фильмы", "student": "студенты",
}

# ---- предлоги --------------------------------------------------------------
# (написание, стебель, кончается на согласную, форма перед гласной, перевод)
# Правило стыковки:
#   слово на согласную: стебель + артикль без начальной «i»   (ta + l-kulur = tal-kulur)
#   стебель на согласную + «l-» удваивает l                   (mi + l + l-belt = mill-belt)
#   слово на гласную: особая форма                            (ta' l-omm, fl-ilma)
PREPS = [
    dict(display="ta'",  stem="ta",  cons=False, vowel="ta' l-", full="ta'",
         meaning="«чей», принадлежность"),
    dict(display="ma'",  stem="ma",  cons=False, vowel="ma' l-", full="ma'",
         meaning="с (кем, чем)"),
    dict(display="fi",   stem="fi",  cons=False, vowel="fl-",   full="fi",
         meaning="в (где)"),
    dict(display="minn", stem="mi",  cons=True,  vowel="mill-", full="minn",
         meaning="из, от"),
    dict(display="lil",  stem="li",  cons=True,  vowel="lill-", full="lil",
         meaning="кому, к"),
    dict(display="għal", stem="għa", cons=True,  vowel="għall-", full="għal",
         meaning="для, за"),
]

# какие темы существительных осмысленны с предлогом (None = любые)
PREP_NOUNS = {
    "ta'": ["house", "things", "place", "food", "family"],
    "ma'": ["family", "food"],
    "fi": ["place", "house"],
    "minn": ["place", "house"],
    "lil": ["family"],
    "għal": ["family", "things"],
}

PREP_LIMIT = 28

SUN = set("ċdnrstxżz")


def article_for(stem):
    """Форма артикля: l- / il- / iX- / l-i (перед s+согласная)."""
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


def fuse(prep, art, stem):
    """Слитная форма предлога с определённым артиклем."""
    if art.startswith("l-"):                      # слово начинается на гласную
        return prep["vowel"] + art[2:]
    body = art[1:]                                # il-kulur -> l-kulur
    if prep["cons"] and body.startswith("l-"):
        return prep["stem"] + "l" + body          # mi + l + l-belt = mill-belt
    return prep["stem"] + body


def prep_options(prep, art, stem):
    """Верный вариант + две правдоподобные ошибки (не тот класс артикля)."""
    right = fuse(prep, art, stem)
    cand = [
        right,
        fuse(prep, "il-" + stem, stem),           # как будто слово на лунную букву
        fuse(prep, "l-" + stem, stem),            # как будто слово на гласную
        prep["full"] + "-" + art,                 # без стыковки вообще
    ]
    out = [right]
    for c in cand[1:]:
        if c != right and c not in out:
            out.append(c)
    return out[:3]


def plural_article(stem):
    art = article_for(stem)
    return art + stem


def wrong_articles(stem):
    """Две правдоподобные, но неверные формы артикля для того же слова."""
    right = article_for(stem)
    pool = ["il-", "l-", "is-", "it-", "iż-", "in-", "ix-", "l-i"]
    bad = [a for a in pool if a != right]
    # берём первые два, детерминированно
    return [b + stem for b in bad[:2]]


def main():
    words = load_words()
    by_mt = {w["mt"]: w for w in words}
    sample = "--sample" in sys.argv

    # ---------- согласование ----------
    agreement = []

    def adj_forms(adj):
        forms = [adj["mt"]]
        if adj.get("forms"):
            forms += [f.strip() for f in adj["forms"].split(",")]
        return forms

    for noun_mt, adj_mt, ru in COPULA_ITEMS:
        n, a = by_mt.get(noun_mt), by_mt.get(adj_mt)
        if not n or not a or not n.get("g") or not n.get("art"):
            print("  пропуск:", noun_mt, adj_mt, file=sys.stderr)
            continue
        forms = adj_forms(a)
        if len(forms) < 2:
            print("  пропуск (нет формы ж.р.):", adj_mt, file=sys.stderr)
            continue
        if ru is None:
            continue
        form = forms[0] if n["g"] == "m" else forms[1]
        copula = COPULA[0] if n["g"] == "m" else COPULA[1]
        agreement.append({
            "kind": "copula",
            "subject": n["art"],
            "adj": a["mt"],
            "verb": "hu",
            "gender": n["g"],
            "adjForm": form,
            "adjOptions": forms[:2],
            "verbForm": copula,
            "verbOptions": COPULA,
            "phrase": "%s %s %s." % (n["art"][0].upper() + n["art"][1:], copula, form),
            "ru": ru,
        })

    for noun_mt, adj_mt, verb_mt, ru in VERB_ITEMS:
        n, a, v = by_mt.get(noun_mt), by_mt.get(adj_mt), by_mt.get(verb_mt)
        if not n or not a or not v or not n.get("g") or not n.get("art"):
            print("  пропуск:", noun_mt, adj_mt, verb_mt, file=sys.stderr)
            continue
        forms = adj_forms(a)
        if len(forms) < 2 or not v.get("pres"):
            print("  пропуск:", adj_mt, verb_mt, file=sys.stderr)
            continue
        vforms = [f.strip() for f in v["pres"].split(",")]
        if len(vforms) != 3:
            print("  пропуск (парадигма):", verb_mt, file=sys.stderr)
            continue
        form = forms[0] if n["g"] == "m" else forms[1]
        vform = vforms[0] if n["g"] == "m" else vforms[1]
        agreement.append({
            "kind": "verb",
            "subject": n["art"],
            "adj": a["mt"],
            "verb": v["mt"],
            "gender": n["g"],
            "adjForm": form,
            "adjOptions": forms[:2],
            "verbForm": vform,
            "verbOptions": vforms,
            "phrase": "%s %s %s." % (n["art"][0].upper() + n["art"][1:], form, vform),
            "ru": ru,
        })

    # ---------- множественное ----------
    nouns = [w for w in words
             if w.get("pos") == "noun" and w.get("pl") and w.get("g")]
    plural = []
    for i, n in enumerate(nouns):
        pl = n["pl"]
        art_pl = plural_article(pl)
        total = len(nouns)
        picks = []
        for step in (7, 13):
            j = (i * step + 3) % total
            for _ in range(total):
                if j != i and nouns[j]["pl"] != pl and nouns[j]["pl"] not in picks:
                    picks.append(nouns[j]["pl"])
                    break
                j = (j + 1) % total
        opts = [pl] + picks[:2]
        plural.append({
            "noun": n["mt"],
            "nounRu": re.sub(r"\s*\([^)]*\)", "", n["ru"].split(",")[0].strip()),
            "ruPl": RU_PL.get(n["mt"]),
            "gender": n["g"],
            "subject": n["art"],
            "plural": pl,
            "pluralOptions": opts,
            "definite": art_pl,
            "definiteOptions": [art_pl] + wrong_articles(pl),
        })

    # ---------- предлоги ----------
    prep = []
    for pr in PREPS:
        allowed = PREP_NOUNS.get(pr["display"])
        picked = [n for n in words
                  if n.get("pos") == "noun" and n.get("art") and n.get("g")
                  and (allowed is None or n.get("topic") in allowed)]
        picked = picked[:PREP_LIMIT]
        for n in picked:
            prep.append({
                "prep": pr["display"],
                "meaning": pr["meaning"],
                "subject": n["art"],
                "nounRu": re.sub(r"\s*\([^)]*\)", "", n["ru"].split(",")[0].strip()),
                "fused": fuse(pr, n["art"], n["mt"]),
                "options": prep_options(pr, n["art"], n["mt"]),
            })

    seen, pl2 = set(), []
    for it in prep:
        if it["fused"] in seen:
            continue
        seen.add(it["fused"])
        pl2.append(it)
    prep = pl2

    data = {"agreement": agreement, "plural": plural, "prep": prep}

    if sample:
        print("=== согласование (%d) ===" % len(agreement))
        for it in agreement[:8]:
            print("  %s" % it["phrase"])
            print("     род: %s | прилаг.: %s | глаг.: %s | выбор прил.: %s | выбор глаг.: %s"
                  % (it["gender"], it["adjForm"], it["verbForm"],
                     " / ".join(it["adjOptions"]), " / ".join(it["verbOptions"])))
            print("     перевод: %s" % it["ru"])
        print()
        print("=== множественное (%d) ===" % len(plural))
        for it in plural[:8]:
            print("  %s (%s) -> %s | с артиклем: %s   перевод: %s"
                  % (it["noun"], it["gender"], it["plural"], it["definite"], it["nounRu"]))
            print("     выбор: %s | артикль: %s"
                  % (" / ".join(it["pluralOptions"]), " / ".join(it["definiteOptions"])))
        print()
        print("=== предлоги (%d) ===" % len(prep))
        for it in prep[:12]:
            print("  %-6s + %-14s -> %-18s (%s)   выбор: %s"
                  % (it["prep"], it["subject"], it["fused"], it["meaning"],
                     " / ".join(it["options"])))
        return 0

    lines = ["window.FORMS = {"]
    for key in ("agreement", "plural", "prep"):
        lines.append("  %s: [" % key)
        for it in data[key]:
            lines.append("    " + json.dumps(it, ensure_ascii=False) + ",")
        lines.append("  ],")
    lines.append("};")
    with open(os.path.join(ROOT, TARGET), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("записано %s: согласование %d, мн.ч. %d, предлоги %d"
          % (TARGET, len(agreement), len(plural), len(prep)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
