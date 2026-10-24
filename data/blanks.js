// Упражнение «Imla l-vojt» — заполнить пропуски нужной формой.
//
// Идея: дано предложение с пропусками и подсказка в скобках (словарная форма).
// Лицо и число нужно определить по подлежащему самому — в вопросе подсказка
// о лице НЕ показывается, она раскрывается только в разборе.
//
// BLANK_FORMS — выверенные вручную парадигмы. Ключи:
//   1s 2s 3m 3f 1p 2p 3p  — глагол, имперфетт (несовершенное время)
//   m f pl                — существительное / прилагательное
//
// Первые восемь предложений и их ответы взяты из учебного задания, поэтому
// формы в них — эталон. Остальные формы выведены по стандартным правилам
// (префиксы n-/t-/j-, ассимиляция t- с шипящими, i- вместо j- у удвоенных
// корней) и требуют проверки носителем.

window.BLANK_FORMS = {
  // ---- глаголы из задания ----
  libes:   { "1s": "nilbes",   "2s": "tilbes",    "3m": "jilbes",    "3f": "tilbes",    "1p": "nilbsu",    "2p": "tilbsu",    "3p": "jilbsu" },
  ħareġ:   { "1s": "noħroġ",   "2s": "toħroġ",    "3m": "joħroġ",    "3f": "toħroġ",    "1p": "noħorġu",   "2p": "toħorġu",   "3p": "joħorġu" },
  żamm:    { "1s": "nżomm",    "2s": "żżomm",     "3m": "jżomm",     "3f": "żżomm",     "1p": "nżommu",    "2p": "żżommu",    "3p": "jżommu" },
  ħadem:   { "1s": "naħdem",   "2s": "taħdem",    "3m": "jaħdem",    "3f": "taħdem",    "1p": "naħdmu",    "2p": "taħdmu",    "3p": "jaħdmu" },
  sarraf:  { "1s": "nsarraf",  "2s": "ssarraf",   "3m": "jsarraf",   "3f": "ssarraf",   "1p": "nsarrfu",   "2p": "ssarrfu",   "3p": "jsarrfu" },
  xtara:   { "1s": "nixtri",   "2s": "tixtri",    "3m": "jixtri",    "3f": "tixtri",    "1p": "nixtru",    "2p": "tixtru",    "3p": "jixtru" },
  daħal:   { "1s": "nidħol",   "2s": "tidħol",    "3m": "jidħol",    "3f": "tidħol",    "1p": "nidħlu",    "2p": "tidħlu",    "3p": "jidħlu" },
  waqaf:   { "1s": "nieqaf",   "2s": "tieqaf",    "3m": "jieqaf",    "3f": "tieqaf",    "1p": "nieqfu",    "2p": "tieqfu",    "3p": "jieqfu" },
  xarrab:  { "1s": "nxarrab",  "2s": "xxarrab",   "3m": "jxarrab",   "3f": "xxarrab",   "1p": "nxarrbu",   "2p": "xxarrbu",   "3p": "jxarrbu" },
  ħasel:   { "1s": "naħsel",   "2s": "taħsel",    "3m": "jaħsel",    "3f": "taħsel",    "1p": "naħslu",    "2p": "taħslu",    "3p": "jaħslu" },
  mess:    { "1s": "nmiss",    "2s": "tmiss",     "3m": "jmiss",     "3f": "tmiss",     "1p": "nmissu",    "2p": "tmissu",    "3p": "jmissu" },
  ħassar:  { "1s": "nħassar",  "2s": "tħassar",   "3m": "iħassar",   "3f": "tħassar",   "1p": "nħassru",   "2p": "tħassru",   "3p": "iħassru" },
  wasal:   { "1s": "nasal",    "2s": "tasal",     "3m": "jasal",     "3f": "tasal",     "1p": "naslu",     "2p": "taslu",     "3p": "jaslu" },
  ħabb:    { "1s": "nħobb",    "2s": "tħobb",     "3m": "iħobb",     "3f": "tħobb",     "1p": "nħobbu",    "2p": "tħobbu",    "3p": "iħobbu" },
  ħabbat:  { "1s": "nħabbat",  "2s": "tħabbat",   "3m": "iħabbat",   "3f": "tħabbat",   "1p": "nħabbtu",   "2p": "tħabbtu",   "3p": "iħabbtu" },

  // ---- существительные и прилагательные ----
  kamra:   { "sg_art": "il-kamra",   "pl_art": "il-kmamar",   "sg": "kamra",   "pl": "kmamar" },
  karozza: { "sg_art": "il-karozza", "pl_art": "il-karozzi",  "sg": "karozza", "pl": "karozzi" },
  tifel:   { "sg_art": "it-tifel",   "pl_art": "it-tfal",     "sg": "tifel",   "pl": "tfal" },
  belt:    { "sg_art": "il-belt",    "pl_art": "il-bliet",    "sg": "belt",    "pl": "bliet" },
  ilma:    { "sg_art": "l-ilma",     "sg": "ilma" },
  kbir:    { "m": "kbir",  "f": "kbira",  "pl": "kbar" },
  żgħir:   { "m": "żgħir", "f": "żgħira", "pl": "żgħar" },
  nadif:   { "m": "nadif", "f": "nadifa", "pl": "nodfa" },
  ġdid:    { "m": "ġdid",  "f": "ġdida",  "pl": "ġodda" }
};

// Подписи для разбора: что это была за форма.
window.BLANK_LABELS = {
  "1s": "1 л. ед. ч. (jien)",
  "2s": "2 л. ед. ч. (inti)",
  "3m": "3 л. ед. ч., м. р. (hu)",
  "3f": "3 л. ед. ч., ж. р. (hi)",
  "1p": "1 л. мн. ч. (aħna)",
  "2p": "2 л. мн. ч. (intom)",
  "3p": "3 л. мн. ч. (huma)",
  "sg_art": "ед. ч. с артиклем",
  "pl_art": "мн. ч. с артиклем",
  "sg": "ед. ч.",
  "pl": "мн. ч.",
  "m": "м. род",
  "f": "ж. род"
};

// accept — другие допустимые варианты той же формы (в скобках в задании).
window.BLANKS = [
  {
    sent: "Oħti {0} sew qabel {1} tixtri.",
    blanks: [
      { hint: "libes", key: "3f" },
      { hint: "ħareġ", key: "3f" }
    ],
    full: "Oħti tilbes sew qabel toħroġ tixtri.",
    ru: "Моя сестра хорошо одевается, прежде чем выйти за покупками."
  },
  {
    sent: "Inti {0} il-kwiet u {1} bil-għaqal.",
    blanks: [
      { hint: "żamm", key: "2s", accept: ["iżżomm"] },
      { hint: "ħadem", key: "2s" }
    ],
    full: "Inti żżomm il-kwiet u taħdem bil-għaqal.",
    ru: "Ты сохраняешь спокойствие и работаешь с умом."
  },
  {
    sent: "Aħna {0} l-flus biex {1} li jkollna bżonn.",
    blanks: [
      { hint: "sarraf", key: "1p", accept: ["insarrfu"] },
      { hint: "xtara", key: "1p" }
    ],
    full: "Aħna nsarrfu l-flus biex nixtru li jkollna bżonn.",
    ru: "Мы обмениваем деньги, чтобы купить то, что нам нужно."
  },
  {
    sent: "Kif it-tfal {0} l-iskola {1} mil-logħob.",
    blanks: [
      { hint: "daħal", key: "3p" },
      { hint: "waqaf", key: "3p" }
    ],
    full: "Kif it-tfal jidħlu l-iskola jieqfu mil-logħob.",
    ru: "Как только дети входят в школу, они бросают игру."
  },
  {
    sent: "Ommi {0} xi ħwejjeġ qabel {1} bil-magna.",
    blanks: [
      { hint: "xarrab", key: "3f", accept: ["ixxarrab"] },
      { hint: "ħasel", key: "3f" }
    ],
    full: "Ommi xxarrab xi ħwejjeġ qabel taħsel bil-magna.",
    ru: "Мама замачивает вещи, прежде чем стирать в машине."
  },
  {
    sent: "Jekk id-dubbiena {0} il-frott, dan {1}.",
    blanks: [
      { hint: "mess", key: "3f" },
      { hint: "ħassar", key: "3m" }
    ],
    full: "Jekk id-dubbiena tmiss il-frott, dan iħassar.",
    ru: "Если муха коснётся фрукта, он испортится."
  },
  {
    sent: "Ħafna mit-turisti li {0} Malta fis-sajf {1} x-xemx.",
    blanks: [
      { hint: "wasal", key: "3p" },
      { hint: "ħabb", key: "3p" }
    ],
    full: "Ħafna mit-turisti li jaslu Malta fis-sajf iħobbu x-xemx.",
    ru: "Многие туристы, приезжающие на Мальту летом, любят солнце."
  },
  {
    sent: "Qabel {0} xi mkien, {1} il-bieb.",
    blanks: [
      { hint: "daħal", key: "2s" },
      { hint: "ħabbat", key: "2s" }
    ],
    full: "Qabel tidħol xi mkien, tħabbat il-bieb.",
    ru: "Прежде чем войти куда-либо, постучи в дверь."
  },

  // ---- формы существительных и прилагательных в предложении ----
  {
    sent: "Id-dar hija {0}.",
    blanks: [{ hint: "kbir", key: "f" }],
    full: "Id-dar hija kbira.",
    ru: "Дом большой.",
    note: "прилагательное согласуется с существительным: dar — женского рода"
  },
  {
    sent: "{0} hija żgħira.",
    blanks: [{ hint: "kamra", key: "sg_art" }],
    full: "Il-kamra hija żgħira.",
    ru: "Комната маленькая.",
    note: "определённый артикль перед комнатой"
  },
  {
    sent: "Dawn huma {0}.",
    blanks: [{ hint: "tifel", key: "pl" }],
    full: "Dawn huma tfal.",
    ru: "Это дети.",
    note: "dawn — множественное число, значит и существительное во множественном"
  },
  {
    sent: "It-toroq huma {0}.",
    blanks: [{ hint: "nadif", key: "pl" }],
    full: "It-toroq huma nodfa.",
    ru: "Улицы чистые.",
    note: "прилагательное во множественном числе"
  },
  {
    sent: "{0} hija ġdida.",
    blanks: [{ hint: "karozza", key: "sg_art" }],
    full: "Il-karozza hija ġdida.",
    ru: "Машина новая.",
    note: "артикль перед karozza"
  }
];
