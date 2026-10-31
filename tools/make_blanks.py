#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Собрать упражнение «Заполнить пропуски» (data/blanks.js).

Два источника:

  workbook — восемь предложений из учебного задания и пять на существительные
             и прилагательные. Ответы в них эталонные, взяты из задания.
  derived  — упражнения на остальные лица, построенные из тех же парадигм:
             подставляем подлежащее (местоимение или существительное) и
             подобранное дополнение. Формы глаголов при этом не выдумываются
             заново — берутся из BLANK_FORMS.

Формы глаголов, которых нет в задании, выведены по стандартным правилам
(префиксы n-/t-/j-, ассимиляция t- с шипящими, i- вместо j- у удвоенных
корней) и требуют проверки носителем. Поэтому у каждого упражнения есть
поле src.

Usage:
    python3 tools/make_blanks.py            # записать data/blanks.js
    python3 tools/make_blanks.py --sample   # показать примеры
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = "data/blanks.js"

# ---- парадигмы -------------------------------------------------------------
# 1s 2s 3m 3f 1p 2p 3p — имперфетт; m f pl — существительное/прилагательное.
FORMS = {
    "libes":   {"1s": "nilbes",   "2s": "tilbes",    "3m": "jilbes",    "3f": "tilbes",    "1p": "nilbsu",    "2p": "tilbsu",    "3p": "jilbsu"},
    "ħareġ":   {"1s": "noħroġ",   "2s": "toħroġ",    "3m": "joħroġ",    "3f": "toħroġ",    "1p": "noħorġu",   "2p": "toħorġu",   "3p": "joħorġu"},
    "żamm":    {"1s": "nżomm",    "2s": "żżomm",     "3m": "jżomm",     "3f": "żżomm",     "1p": "nżommu",    "2p": "żżommu",    "3p": "jżommu"},
    "ħadem":   {"1s": "naħdem",   "2s": "taħdem",    "3m": "jaħdem",    "3f": "taħdem",    "1p": "naħdmu",    "2p": "taħdmu",    "3p": "jaħdmu"},
    "sarraf":  {"1s": "nsarraf",  "2s": "ssarraf",   "3m": "jsarraf",   "3f": "ssarraf",   "1p": "nsarrfu",   "2p": "ssarrfu",   "3p": "jsarrfu"},
    "xtara":   {"1s": "nixtri",   "2s": "tixtri",    "3m": "jixtri",    "3f": "tixtri",    "1p": "nixtru",    "2p": "tixtru",    "3p": "jixtru"},
    "daħal":   {"1s": "nidħol",   "2s": "tidħol",    "3m": "jidħol",    "3f": "tidħol",    "1p": "nidħlu",    "2p": "tidħlu",    "3p": "jidħlu"},
    "waqaf":   {"1s": "nieqaf",   "2s": "tieqaf",    "3m": "jieqaf",    "3f": "tieqaf",    "1p": "nieqfu",    "2p": "tieqfu",    "3p": "jieqfu"},
    "xarrab":  {"1s": "nxarrab",  "2s": "xxarrab",   "3m": "jxarrab",   "3f": "xxarrab",   "1p": "nxarrbu",   "2p": "xxarrbu",   "3p": "jxarrbu"},
    "ħasel":   {"1s": "naħsel",   "2s": "taħsel",    "3m": "jaħsel",    "3f": "taħsel",    "1p": "naħslu",    "2p": "taħslu",    "3p": "jaħslu"},
    "mess":    {"1s": "nmiss",    "2s": "tmiss",     "3m": "jmiss",     "3f": "tmiss",     "1p": "nmissu",    "2p": "tmissu",    "3p": "jmissu"},
    "ħassar":  {"1s": "nħassar",  "2s": "tħassar",   "3m": "iħassar",   "3f": "tħassar",   "1p": "nħassru",   "2p": "tħassru",   "3p": "iħassru"},
    "wasal":   {"1s": "nasal",    "2s": "tasal",     "3m": "jasal",     "3f": "tasal",     "1p": "naslu",     "2p": "taslu",     "3p": "jaslu"},
    "ħabb":    {"1s": "nħobb",    "2s": "tħobb",     "3m": "iħobb",     "3f": "tħobb",     "1p": "nħobbu",    "2p": "tħobbu",    "3p": "iħobbu"},
    "ħabbat":  {"1s": "nħabbat",  "2s": "tħabbat",   "3m": "iħabbat",   "3f": "tħabbat",   "1p": "nħabbtu",   "2p": "tħabbtu",   "3p": "iħabbtu"},

    "kamra":   {"sg_art": "il-kamra",   "pl_art": "il-kmamar",   "sg": "kamra",   "pl": "kmamar"},
    "karozza": {"sg_art": "il-karozza", "pl_art": "il-karozzi",  "sg": "karozza", "pl": "karozzi"},
    "tifel":   {"sg_art": "it-tifel",   "pl_art": "it-tfal",     "sg": "tifel",   "pl": "tfal"},
    "belt":    {"sg_art": "il-belt",    "pl_art": "il-bliet",    "sg": "belt",    "pl": "bliet"},
    "ilma":    {"sg_art": "l-ilma",     "sg": "ilma"},
    "kbir":    {"m": "kbir",  "f": "kbira",  "pl": "kbar"},
    "żgħir":   {"m": "żgħir", "f": "żgħira", "pl": "żgħar"},
    "nadif":   {"m": "nadif", "f": "nadifa", "pl": "nodfa"},
    "ġdid":    {"m": "ġdid",  "f": "ġdida",  "pl": "ġodda"}
}

LABELS = {
    "1s": "1 л. ед. ч. (jien)", "2s": "2 л. ед. ч. (inti)",
    "3m": "3 л. ед. ч., м. р. (hu)", "3f": "3 л. ед. ч., ж. р. (hi)",
    "1p": "1 л. мн. ч. (aħna)", "2p": "2 л. мн. ч. (intom)",
    "3p": "3 л. мн. ч. (huma)",
    "sg_art": "ед. ч. с артиклем", "pl_art": "мн. ч. с артиклем",
    "sg": "ед. ч.", "pl": "мн. ч.", "m": "м. род", "f": "ж. род"
}

# подлежащее по лицу: местоимение для 1-го и 2-го лица,
# существительное для 3-го — чтобы лицо надо было определять, как в задании
SUBJ = {
    "1s": ("Jien", "Я"),
    "2s": ("Inti", "Ты"),
    "3m": ("It-tifel", "Мальчик"),
    "3f": ("Il-mara", "Женщина"),
    "1p": ("Aħna", "Мы"),
    "2p": ("Intom", "Вы"),
    "3p": ("It-tfal", "Дети")
}

# ---- упражнения из задания (эталон) ---------------------------------------
WORKBOOK = [
    ("Oħti {0} sew qabel {1} tixtri.", [("libes", "3f", []), ("ħareġ", "3f", [])],
     "Oħti tilbes sew qabel toħroġ tixtri.",
     "Моя сестра хорошо одевается, прежде чем выйти за покупками."),
    ("Inti {0} il-kwiet u {1} bil-għaqal.", [("żamm", "2s", ["iżżomm"]), ("ħadem", "2s", [])],
     "Inti żżomm il-kwiet u taħdem bil-għaqal.",
     "Ты сохраняешь спокойствие и работаешь с умом."),
    ("Aħna {0} l-flus biex {1} li jkollna bżonn.", [("sarraf", "1p", ["insarrfu"]), ("xtara", "1p", [])],
     "Aħna nsarrfu l-flus biex nixtru li jkollna bżonn.",
     "Мы обмениваем деньги, чтобы купить то, что нам нужно."),
    ("Kif it-tfal {0} l-iskola {1} mil-logħob.", [("daħal", "3p", []), ("waqaf", "3p", [])],
     "Kif it-tfal jidħlu l-iskola jieqfu mil-logħob.",
     "Как только дети входят в школу, они бросают игру."),
    ("Ommi {0} xi ħwejjeġ qabel {1} bil-magna.", [("xarrab", "3f", ["ixxarrab"]), ("ħasel", "3f", [])],
     "Ommi xxarrab xi ħwejjeġ qabel taħsel bil-magna.",
     "Мама замачивает вещи, прежде чем стирать в машине."),
    ("Jekk id-dubbiena {0} il-frott, dan {1}.", [("mess", "3f", []), ("ħassar", "3m", [])],
     "Jekk id-dubbiena tmiss il-frott, dan iħassar.",
     "Если муха коснётся фрукта, он испортится."),
    ("Ħafna mit-turisti li {0} Malta fis-sajf {1} x-xemx.", [("wasal", "3p", []), ("ħabb", "3p", [])],
     "Ħafna mit-turisti li jaslu Malta fis-sajf iħobbu x-xemx.",
     "Многие туристы, приезжающие на Мальту летом, любят солнце."),
    ("Qabel {0} xi mkien, {1} il-bieb.", [("daħal", "2s", []), ("ħabbat", "2s", [])],
     "Qabel tidħol xi mkien, tħabbat il-bieb.",
     "Прежде чем войти куда-либо, постучи в дверь."),

    ("Id-dar hija {0}.", [("kbir", "f", [])], "Id-dar hija kbira.", "Дом большой.",
     "прилагательное согласуется с существительным: dar — женского рода"),
    ("{0} hija żgħira.", [("kamra", "sg_art", [])], "Il-kamra hija żgħira.", "Комната маленькая.",
     "определённый артикль перед комнатой"),
    ("Dawn huma {0}.", [("tifel", "pl", [])], "Dawn huma tfal.", "Это дети.",
     "dawn — множественное число, значит и существительное во множественном"),
    ("It-toroq huma {0}.", [("nadif", "pl", [])], "It-toroq huma nodfa.", "Улицы чистые.",
     "прилагательное во множественном числе"),
    ("{0} hija ġdida.", [("karozza", "sg_art", [])], "Il-karozza hija ġdida.", "Машина новая.",
     "артикль перед karozza")
]

# ---- дополнение и русские формы для порождения -----------------------------
# (дополнение на мальтийском, дополнение по-русски, формы глагола в русском)
DERIVE = [
    ("libes",  "sew",        "хорошо", "одеваюсь", "одеваешься", "одевается", "одеваемся", "одеваетесь", "одеваются"),
    ("ħareġ",  "id-dar",     "из дома", "выхожу", "выходишь", "выходит", "выходим", "выходите", "выходят"),
    ("żamm",   "il-ktieb",   "книгу",  "держу", "держишь", "держит", "держим", "держите", "держат"),
    ("ħadem",  "ħafna",      "много",  "работаю", "работаешь", "работает", "работаем", "работаете", "работают"),
    ("sarraf", "il-flus",    "деньги", "обмениваю", "обмениваешь", "обменивает", "обмениваем", "обмениваете", "обменивают"),
    ("xtara",  "il-ħobż",    "хлеб",   "покупаю", "покупаешь", "покупает", "покупаем", "покупаете", "покупают"),
    ("daħal",  "il-kamra",   "в комнату", "вхожу", "входишь", "входит", "входим", "входите", "входят"),
    ("waqaf",  "hawn",       "здесь",  "останавливаюсь", "останавливаешься", "останавливается",
     "останавливаемся", "останавливаетесь", "останавливаются"),
    ("xarrab", "il-ħwejjeġ", "одежду", "мочу", "мочишь", "мочит", "мочим", "мочите", "мочат"),
    ("ħasel",  "il-karozza", "машину", "мою", "моешь", "моет", "моем", "моете", "моют"),
    ("mess",   "il-frott",   "фрукты", "трогаю", "трогаешь", "трогает", "трогаем", "трогаете", "трогают"),
    ("ħassar", "kollox",     "всё",    "порчу", "портишь", "портит", "портим", "портите", "портят"),
    ("wasal",  "Malta",      "на Мальту", "приезжаю", "приезжаешь", "приезжает", "приезжаем", "приезжаете", "приезжают"),
    ("ħabb",   "il-Malti",   "мальтийский", "люблю", "любишь", "любит", "любим", "любите", "любят"),
    ("ħabbat", "il-bieb",    "в дверь", "стучу", "стучишь", "стучит", "стучим", "стучите", "стучат")
]

# индекс русской формы в кортеже ru_forms (0-based):
# 1s 2s 3-е ед. (для м и ж одно) 1p 2p 3-е мн.
RU_KEY = {"1s": 0, "2s": 1, "3m": 2, "3f": 2, "1p": 3, "2p": 4, "3p": 5}


def build():
    items = []

    for row in WORKBOOK:
        sent, blanks, full, ru = row[0], row[1], row[2], row[3]
        note = row[4] if len(row) > 4 else None
        item = {
            "sent": sent,
            "blanks": [{"hint": h, "key": k, "accept": a} if a else {"hint": h, "key": k}
                       for h, k, a in blanks],
            "full": full,
            "ru": ru,
            "src": "workbook"
        }
        if note:
            item["note"] = note
        items.append(item)

    for verb, comp_mt, comp_ru, *ru_forms in DERIVE:
        for key, (subj_mt, subj_ru) in SUBJ.items():
            form = FORMS[verb].get(key)
            if not form:
                continue
            ru_verb = ru_forms[RU_KEY[key]]
            # «работает здесь» — дополнение идёт после глагола
            items.append({
                "sent": "%s {0} %s." % (subj_mt, comp_mt),
                "blanks": [{"hint": verb, "key": key}],
                "full": "%s %s %s." % (subj_mt, form, comp_mt),
                "ru": "%s %s %s." % (subj_ru, ru_verb, comp_ru),
                "src": "derived"
            })
    return items


def main():
    items = build()
    seen, out = set(), []
    for it in items:
        if it["full"] in seen:
            continue
        seen.add(it["full"])
        out.append(it)

    # шаблоны должны различаться: иначе два упражнения выглядят одинаково,
    # и по тексту нельзя понять, какое из них на экране
    tpl = {}
    for it in out:
        tpl.setdefault(it["sent"], []).append(it["blanks"][0]["hint"])
    clashes = {k: v for k, v in tpl.items() if len(set(v)) > 1}
    if clashes:
        print("ОДИНАКОВЫЕ ШАБЛОНЫ с разными подсказками: %d" % len(clashes))
        for k, v in list(clashes.items())[:5]:
            print("   %s -> %s" % (k, v))
        return 1

    # самопроверка: подстановка ответов должна давать полную фразу
    bad = []
    for it in out:
        s = it["sent"]
        for i, b in enumerate(it["blanks"]):
            s = s.replace("{%d}" % i, FORMS[b["hint"]][b["key"]])
        if s.lower() != it["full"].lower():
            bad.append((it["sent"], s, it["full"]))
    print("упражнений: %d (пропусков: %d)" % (len(out), sum(len(x["blanks"]) for x in out)))
    # REQ-DATA-02: подстановка ответов даёт полную фразу; REQ-DATA-03: шаблоны различимы
    print("из задания: %d | построено: %d"
          % (len([x for x in out if x["src"] == "workbook"]),
             len([x for x in out if x["src"] == "derived"])))
    if bad:
        print("РАСХОЖДЕНИЙ: %d" % len(bad))
        for s, got, want in bad[:5]:
            print("   %s -> %s ≠ %s" % (s, got, want))
        return 1
    print("сборка фраз из ответов сходится везде")

    if "--sample" in sys.argv:
        print()
        for it in out[:6] + out[-6:]:
            print("  %-42s %-40s [%s]" % (it["sent"], it["ru"], it["src"]))
        return 0

    lines = ["window.BLANK_FORMS = {"]
    for hint, forms in FORMS.items():
        lines.append("  %s: %s," % (json.dumps(hint, ensure_ascii=False),
                                    json.dumps(forms, ensure_ascii=False)))
    lines.append("};")
    lines.append("")
    lines.append("window.BLANK_LABELS = %s;" % json.dumps(LABELS, ensure_ascii=False))
    lines.append("")
    lines.append("window.BLANKS = [")
    for it in out:
        lines.append("  " + json.dumps(it, ensure_ascii=False) + ",")
    lines.append("];")

    with open(os.path.join(ROOT, TARGET), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("записано %s" % TARGET)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
