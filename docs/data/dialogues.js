// Короткие повседневные диалоги: фразы в контексте вместе с переводом.
//
// Формат: lines — реплики по очереди, who: "A" или "B".
// Диалоги написаны на базовой лексике из data/words.js; всё, чего не хватало,
// добавлено в словарь отдельно. Мальтийский требует проверки носителем.

window.DIALOGUES = [
  {
    id: "greet",
    title: "Приветствие и знакомство",
    topic: "greet",
    note: "jisimni — «меня зовут», от isem (имя). Буквально «моё имя».",
    lines: [
      { who: "A", mt: "Bonġu! Kif int?", ru: "Доброе утро! Как ты?" },
      { who: "B", mt: "Jien tajjeb, grazzi. U int?", ru: "Я хорошо, спасибо. А ты?" },
      { who: "A", mt: "Tajjeb ukoll, grazzi.", ru: "Тоже хорошо, спасибо." },
      { who: "B", mt: "Kif jismek?", ru: "Как тебя зовут?" },
      { who: "A", mt: "Jisimni Anna. U int?", ru: "Меня зовут Анна. А тебя?" },
      { who: "B", mt: "Jisimni Pawlu. Minn fejn int?", ru: "Меня зовут Павлу. Откуда ты?" },
      { who: "A", mt: "Jien minn Russja. Narak!", ru: "Я из России. Увидимся!" }
    ]
  },
  {
    id: "cafe",
    title: "В кафе",
    topic: "food",
    note: "Kemm jiswa? — «сколько стоит». Jiswa — форма глагола «стоить».",
    lines: [
      { who: "A", mt: "Bonġu! Xi trid?", ru: "Доброе утро! Что ты хочешь?" },
      { who: "B", mt: "Irrid kafè, jekk jogħġbok.", ru: "Я хочу кофе, пожалуйста." },
      { who: "A", mt: "U xi trid tiekol?", ru: "А что ты хочешь поесть?" },
      { who: "B", mt: "Irrid kejk.", ru: "Я хочу пирог." },
      { who: "A", mt: "Kafè u kejk. Dan jiswa tliet ewro.", ru: "Кофе и пирог. Это стоит три евро." },
      { who: "B", mt: "Hawn. Grazzi ħafna!", ru: "Вот. Большое спасибо!" },
      { who: "A", mt: "Ta' xejn. Saħħa!", ru: "Не за что. Пока!" }
    ]
  },
  {
    id: "shop",
    title: "В магазине",
    topic: "place",
    note: "Għandek...? — «у тебя есть...?». От għandek (иметь).",
    lines: [
      { who: "A", mt: "Jekk jogħġbok, għandek ħobż?", ru: "Извините, у вас есть хлеб?" },
      { who: "B", mt: "Iva, għandi. Kemm trid?", ru: "Да, есть. Сколько хотите?" },
      { who: "A", mt: "Irrid tnejn, jekk jogħġbok. Kemm jiswa?", ru: "Я хочу два, пожалуйста. Сколько стоит?" },
      { who: "B", mt: "Jiswa żewġ ewro.", ru: "Стоит два евро." },
      { who: "A", mt: "Hawn. Grazzi!", ru: "Вот. Спасибо!" },
      { who: "B", mt: "Grazzi. Saħħa!", ru: "Спасибо. Пока!" }
    ]
  },
  {
    id: "directions",
    title: "Как пройти",
    topic: "place",
    note: "aqleb — повелительная форма от qaleb (поворачивать).",
    lines: [
      { who: "A", mt: "Skużani, fejn hi l-knisja?", ru: "Извините, где церковь?" },
      { who: "B", mt: "Mur dritt, imbagħad aqleb lejn ix-xellug.", ru: "Иди прямо, потом поверни налево." },
      { who: "A", mt: "Hawn qrib?", ru: "Это близко?" },
      { who: "B", mt: "Iva, ħdejn il-bank.", ru: "Да, рядом с банком." },
      { who: "A", mt: "Grazzi ħafna!", ru: "Большое спасибо!" },
      { who: "B", mt: "Ta' xejn.", ru: "Не за что." }
    ]
  },
  {
    id: "hotel",
    title: "В отеле",
    topic: "travel",
    note: "it-tieni sular — второй этаж. tiegħek — «твой».",
    lines: [
      { who: "A", mt: "Bonswa. Għandi kamra hawn.", ru: "Добрый вечер. У меня здесь комната." },
      { who: "B", mt: "Kif jismek?", ru: "Как вас зовут?" },
      { who: "A", mt: "Jisimni Anna.", ru: "Меня зовут Анна." },
      { who: "B", mt: "Iva. Il-kamra tiegħek hija fuq it-tieni sular.", ru: "Да. Ваша комната на втором этаже." },
      { who: "A", mt: "Fejn hi l-lukanda tal-ajruport?", ru: "Где отель у аэропорта?" },
      { who: "B", mt: "Hija qrib il-baħar.", ru: "Он рядом с морем." },
      { who: "A", mt: "Grazzi ħafna!", ru: "Большое спасибо!" }
    ]
  },
  {
    id: "taxi",
    title: "В такси",
    topic: "travel",
    note: "Ħmistax-il ewro — «пятнадцать евро»: перед существительным форма -il.",
    lines: [
      { who: "A", mt: "Bonswa! Irrid immur l-ajruport.", ru: "Добрый вечер! Я хочу поехать в аэропорт." },
      { who: "B", mt: "Iva, ejja.", ru: "Да, поехали." },
      { who: "A", mt: "Kemm jiswa?", ru: "Сколько стоит?" },
      { who: "B", mt: "Ħmistax-il ewro.", ru: "Пятнадцать евро." },
      { who: "A", mt: "Tajjeb. Grazzi.", ru: "Хорошо. Спасибо." },
      { who: "B", mt: "Ta' xejn. Wasalna!", ru: "Не за что. Приехали!" }
    ]
  },
  {
    id: "phone",
    title: "Телефонный разговор",
    topic: "office",
    note: "Narak fi ftit minuti — «увидимся через несколько минут».",
    lines: [
      { who: "A", mt: "Allo?", ru: "Алло?" },
      { who: "B", mt: "Allo, jien Pawlu. Kif int?", ru: "Алло, это Павлу. Как ты?" },
      { who: "A", mt: "Tajjeb, grazzi. Fejn int?", ru: "Хорошо, спасибо. Где ты?" },
      { who: "B", mt: "Jien hawn ħdejn il-bank.", ru: "Я здесь, рядом с банком." },
      { who: "A", mt: "Narak fi ftit minuti.", ru: "Увидимся через несколько минут." },
      { who: "B", mt: "Tajjeb. Saħħa!", ru: "Хорошо. Пока!" }
    ]
  },
  {
    id: "doctor",
    title: "У врача",
    topic: "body",
    note: "X'għandek? — «что с тобой?», буквально «что ты имеешь».",
    lines: [
      { who: "A", mt: "Bonġu. Jien marid.", ru: "Доброе утро. Я болен." },
      { who: "B", mt: "X'għandek?", ru: "Что с тобой?" },
      { who: "A", mt: "Għandi uġigħ f'rasi.", ru: "У меня болит голова." },
      { who: "B", mt: "Trid ilma?", ru: "Хочешь воды?" },
      { who: "A", mt: "Iva, grazzi.", ru: "Да, спасибо." },
      { who: "B", mt: "Mur id-dar u strieħ.", ru: "Иди домой и отдохни." }
    ]
  },
  {
    id: "office",
    title: "На работе",
    topic: "office",
    note: "fl-għaxra — «в десять». Kamra tal-laqgħa — переговорная.",
    lines: [
      { who: "A", mt: "Bonġu. Għandna laqgħa llum?", ru: "Доброе утро. У нас сегодня совещание?" },
      { who: "B", mt: "Iva, fl-għaxra.", ru: "Да, в десять." },
      { who: "A", mt: "Fejn hi l-kamra tal-laqgħa?", ru: "Где переговорная?" },
      { who: "B", mt: "Fuq it-tieni sular.", ru: "На втором этаже." },
      { who: "A", mt: "Grazzi. Narak hemm.", ru: "Спасибо. Увидимся там." },
      { who: "B", mt: "Narak hemm!", ru: "Увидимся там!" }
    ]
  },
  {
    id: "weather",
    title: "Погода и планы",
    topic: "weather",
    note: "tiddi — «светит», от глагола со значением «сиять».",
    lines: [
      { who: "A", mt: "Kif inhi t-temp illum?", ru: "Какая сегодня погода?" },
      { who: "B", mt: "Ix-xemx tiddi.", ru: "Солнце светит." },
      { who: "A", mt: "Sabiħ! Irrid immur il-baħar.", ru: "Красиво! Я хочу поехать на море." },
      { who: "B", mt: "Tajjeb! Ejja.", ru: "Хорошо! Пойдём." },
      { who: "A", mt: "Trid tiġi?", ru: "Ты хочешь пойти?" },
      { who: "B", mt: "Iva, ejja!", ru: "Да, пойдём!" }
    ]
  },

  {
    id: "restaurant",
    title: "В ресторане",
    topic: "food",
    note: "Kemm intom? — «сколько вас?». Hawn hu — «вот он».",
    lines: [
      { who: "A", mt: "Bonswa. Irrid mejda, jekk jogħġbok.", ru: "Добрый вечер. Я хочу столик, пожалуйста." },
      { who: "B", mt: "Kemm intom?", ru: "Сколько вас?" },
      { who: "A", mt: "Tnejn.", ru: "Двое." },
      { who: "B", mt: "Hawn, jekk jogħġbok. Dan hu l-menu.", ru: "Вот, пожалуйста. Это меню." },
      { who: "A", mt: "Grazzi. Irrid il-ħut u l-ilma.", ru: "Спасибо. Я хочу рыбу и воду." },
      { who: "B", mt: "Tajjeb. Narak.", ru: "Хорошо. Скоро вернусь." }
    ]
  },
  {
    id: "family",
    title: "Разговор о семье",
    topic: "family",
    note: "aħwa — множественное от ħu (брат) и oħt (сестра).",
    lines: [
      { who: "A", mt: "Għandek aħwa?", ru: "У тебя есть братья или сёстры?" },
      { who: "B", mt: "Iva, għandi tnejn.", ru: "Да, у меня двое." },
      { who: "A", mt: "Fejn jgħixu?", ru: "Где они живут?" },
      { who: "B", mt: "Jgħixu il-Malta.", ru: "Они живут на Мальте." },
      { who: "A", mt: "U int?", ru: "А ты?" },
      { who: "B", mt: "Jien noqgħod il-belt.", ru: "Я живу в городе." }
    ]
  },
  {
    id: "bus",
    title: "В автобусе",
    topic: "travel",
    note: "Il-Belt — так мальтийцы называют Валлетту, столицу.",
    lines: [
      { who: "A", mt: "Skużani, dan ix-xarabank imur il-Belt?", ru: "Извините, этот автобус идёт в Валлетту?" },
      { who: "B", mt: "Iva, imur il-Belt.", ru: "Да, идёт в Валлетту." },
      { who: "A", mt: "Kemm jiswa l-biljett?", ru: "Сколько стоит билет?" },
      { who: "B", mt: "Tnejn ewro.", ru: "Два евро." },
      { who: "A", mt: "Hawn. Grazzi.", ru: "Вот. Спасибо." },
      { who: "B", mt: "Ta' xejn.", ru: "Не за что." }
    ]
  },
  {
    id: "bank",
    title: "В банке",
    topic: "office",
    note: "Insarraf — «я обменяю», первое лицо от sarraf.",
    lines: [
      { who: "A", mt: "Bonġu. Irrid insarraf il-flus.", ru: "Доброе утро. Я хочу обменять деньги." },
      { who: "B", mt: "Kemm trid?", ru: "Сколько вы хотите?" },
      { who: "A", mt: "Mitt ewro.", ru: "Сто евро." },
      { who: "B", mt: "Tajjeb. Hawn hu.", ru: "Хорошо. Вот." },
      { who: "A", mt: "Grazzi ħafna!", ru: "Большое спасибо!" },
      { who: "B", mt: "Ta' xejn. Saħħa!", ru: "Не за что. Пока!" }
    ]
  },
  {
    id: "birthday",
    title: "День рождения",
    topic: "greet",
    note: "Awguri — поздравление. Kemm għandek snin? — «сколько тебе лет».",
    lines: [
      { who: "A", mt: "Awguri!", ru: "Поздравляю!" },
      { who: "B", mt: "Grazzi ħafna!", ru: "Большое спасибо!" },
      { who: "A", mt: "Kemm għandek snin?", ru: "Сколько тебе лет?" },
      { who: "B", mt: "Għandi tletin sena.", ru: "Мне тридцать лет." },
      { who: "A", mt: "Dan huwa rigal.", ru: "Это подарок." },
      { who: "B", mt: "Grazzi! Int tajjeb ħafna.", ru: "Спасибо! Ты очень добрый." }
    ]
  },
  {
    id: "colleague",
    title: "Знакомство с коллегой",
    topic: "office",
    note: "Piċir! — «приятно познакомиться».",
    lines: [
      { who: "A", mt: "Dan huwa l-kollega ġdid tiegħi.", ru: "Это мой новый коллега." },
      { who: "B", mt: "Piċir! Jien Pawlu.", ru: "Приятно! Я Павлу." },
      { who: "A", mt: "Piċir, Pawlu.", ru: "Приятно, Павлу." },
      { who: "B", mt: "Minn fejn int?", ru: "Откуда ты?" },
      { who: "A", mt: "Jien minn Russja.", ru: "Я из России." },
      { who: "B", mt: "Sabiħ! Jien minn Malta.", ru: "Здорово! Я с Мальты." }
    ]
  },
  {
    id: "help",
    title: "Просьба о помощи",
    topic: "place",
    note: "Tista' tgħin? — «можешь помочь?»",
    lines: [
      { who: "A", mt: "Skużani, tista' tgħin?", ru: "Извините, можете помочь?" },
      { who: "B", mt: "Iva, xi trid?", ru: "Да, что вы хотите?" },
      { who: "A", mt: "Fejn hu l-istazzjon?", ru: "Где станция?" },
      { who: "B", mt: "Mur dritt u aqleb lejn il-lemin.", ru: "Иди прямо и поверни направо." },
      { who: "A", mt: "Grazzi ħafna!", ru: "Большое спасибо!" },
      { who: "B", mt: "Ta' xejn.", ru: "Не за что." }
    ]
  },
  {
    id: "rain",
    title: "Дождь и планы",
    topic: "weather",
    note: "Qed tagħmel ix-xita — «идёт дождь», дословно «делает дождь».",
    lines: [
      { who: "A", mt: "Qed tagħmel ix-xita.", ru: "Идёт дождь." },
      { who: "B", mt: "Iva, u hawn ir-riħ.", ru: "Да, и ветер." },
      { who: "A", mt: "L-ilma huwa kiesaħ.", ru: "Вода холодная." },
      { who: "B", mt: "Ajma!", ru: "Ой!" },
      { who: "A", mt: "Tajjeb. Narak għada.", ru: "Ладно. Увидимся завтра." },
      { who: "B", mt: "Narak għada!", ru: "Увидимся завтра!" }
    ]
  },
  {
    id: "pharmacy",
    title: "В аптеке",
    topic: "body",
    note: "Għal xiex? — «от чего?». Għal rasi — «от головы».",
    lines: [
      { who: "A", mt: "Bonġu. Għandi bżonn il-pilloli.", ru: "Доброе утро. Мне нужны таблетки." },
      { who: "B", mt: "Għal xiex?", ru: "От чего?" },
      { who: "A", mt: "Għal rasi.", ru: "От головы." },
      { who: "B", mt: "Hawn. Dan jiswa ħames ewro.", ru: "Вот. Это стоит пять евро." },
      { who: "A", mt: "Hawn. Grazzi.", ru: "Вот. Спасибо." },
      { who: "B", mt: "Saħħa!", ru: "Пока!" }
    ]
  },
  {
    id: "meeting",
    title: "Договориться о встрече",
    topic: "time",
    note: "Fi tlieta — «в три». Fil-kafè — «в кафе».",
    lines: [
      { who: "A", mt: "Narak għada?", ru: "Увидимся завтра?" },
      { who: "B", mt: "Iva, fi tlieta.", ru: "Да, в три." },
      { who: "A", mt: "Fejn?", ru: "Где?" },
      { who: "B", mt: "Fil-kafè, ħdejn il-bank.", ru: "В кафе, рядом с банком." },
      { who: "A", mt: "Tajjeb. Narak hemm.", ru: "Хорошо. Увидимся там." },
      { who: "B", mt: "Narak!", ru: "Увидимся!" }
    ]
  },
  {
    id: "numbers",
    title: "Числа и покупки",
    topic: "number",
    note: "Kemm jiswa? — «сколько стоит». erba' — форма числа «четыре» перед существительным.",
    lines: [
      { who: "A", mt: "Kemm jiswa dan?", ru: "Сколько это стоит?" },
      { who: "B", mt: "Jiswa ħames ewro.", ru: "Стоит пять евро." },
      { who: "A", mt: "Għandi biss tliet ewro.", ru: "У меня только три евро." },
      { who: "B", mt: "Tajjeb, erba' ewro.", ru: "Ладно, четыре евро." },
      { who: "A", mt: "Hawn. Grazzi!", ru: "Вот. Спасибо!" },
      { who: "B", mt: "Grazzi. Saħħa!", ru: "Спасибо. Пока!" }
    ]
  },
  {
    id: "chores",
    title: "Домашние дела",
    topic: "house",
    note: "Qed + глагол — «делаю прямо сейчас»: qed nnaddaf — я убираю.",
    lines: [
      { who: "A", mt: "X'qed tagħmel?", ru: "Что ты делаешь?" },
      { who: "B", mt: "Qed nnaddaf il-kamra.", ru: "Я убираю комнату." },
      { who: "A", mt: "U wara?", ru: "А потом?" },
      { who: "B", mt: "Wara nsajjar l-ikel.", ru: "Потом я готовлю еду." },
      { who: "A", mt: "Jien naħsel il-karozza.", ru: "Я мою машину." },
      { who: "B", mt: "Tajjeb! Grazzi.", ru: "Хорошо! Спасибо." }
    ]
  },
  {
    id: "clock",
    title: "Который час и встреча",
    topic: "time",
    note: "Kemm hu l-ħin? — «который час». Часы женского рода: hija tlieta.",
    lines: [
      { who: "A", mt: "Kemm hu l-ħin?", ru: "Который час?" },
      { who: "B", mt: "Hija tlieta.", ru: "Три часа." },
      { who: "A", mt: "Meta hija l-laqgħa?", ru: "Когда совещание?" },
      { who: "B", mt: "Fil-ħamsa.", ru: "В пять." },
      { who: "A", mt: "Tajjeb. Narak hemm.", ru: "Хорошо. Увидимся там." },
      { who: "B", mt: "Narak hemm!", ru: "Увидимся там!" }
    ]
  },
  {
    id: "smalltalk",
    title: "Как дела",
    topic: "greet",
    note: "Mhux ħażin — «неплохо», дословно «не плохо».",
    lines: [
      { who: "A", mt: "Kif int illum?", ru: "Как ты сегодня?" },
      { who: "B", mt: "Tajjeb, grazzi. U int?", ru: "Хорошо, спасибо. А ты?" },
      { who: "A", mt: "Mhux ħażin.", ru: "Неплохо." },
      { who: "B", mt: "X'hemm ġdid?", ru: "Что нового?" },
      { who: "A", mt: "Xejn.", ru: "Ничего." },
      { who: "B", mt: "Tajjeb. Narak!", ru: "Хорошо. Увидимся!" }
    ]
  },
  {
    id: "seasons",
    title: "Времена года",
    topic: "weather",
    note: "ix-xitwa — зима, is-sajf — лето. Оба слова с определённым артиклем.",
    lines: [
      { who: "A", mt: "Kif inhi t-temp?", ru: "Какая погода?" },
      { who: "B", mt: "Qed tagħmel ix-xita.", ru: "Идёт дождь." },
      { who: "A", mt: "F'dan iż-żmien spiss tagħmel ix-xita.", ru: "В это время часто идёт дождь." },
      { who: "B", mt: "Iva, ix-xitwa hija kiesħa.", ru: "Да, зима холодная." },
      { who: "A", mt: "Fis-sajf huwa sħun ħafna.", ru: "Летом очень жарко." },
      { who: "B", mt: "Iva, u l-baħar huwa sħun.", ru: "Да, и море тёплое." }
    ]
  },
  {
    id: "school",
    title: "В школе",
    topic: "place",
    note: "l-għalliem — учитель. eżami tal-Malti — экзамен по мальтийскому.",
    lines: [
      { who: "A", mt: "Fejn hi l-iskola?", ru: "Где школа?" },
      { who: "B", mt: "Hija ħdejn il-bank.", ru: "Она рядом с банком." },
      { who: "A", mt: "Għandek eżami llum?", ru: "У тебя сегодня экзамен?" },
      { who: "B", mt: "Iva, eżami tal-Malti.", ru: "Да, экзамен по мальтийскому." },
      { who: "A", mt: "Kif hu l-għalliem?", ru: "Какой учитель?" },
      { who: "B", mt: "Tajjeb ħafna.", ru: "Очень хороший." }
    ]
  },
  {
    id: "taste",
    title: "Еда и вкусы",
    topic: "food",
    note: "jien bil-ġuħ — «я голоден», дословно «я с голодом».",
    lines: [
      { who: "A", mt: "Trid tiekol?", ru: "Хочешь есть?" },
      { who: "B", mt: "Iva, jien bil-ġuħ.", ru: "Да, я голоден." },
      { who: "A", mt: "Trid il-ħut jew il-laħam?", ru: "Хочешь рыбу или мясо?" },
      { who: "B", mt: "Il-ħut, jekk jogħġbok.", ru: "Рыбу, пожалуйста." },
      { who: "A", mt: "U t-tuffieħa?", ru: "А яблоко?" },
      { who: "B", mt: "Le, grazzi. Irrid il-kafè.", ru: "Нет, спасибо. Я хочу кофе." }
    ]
  },
  {
    id: "clothes",
    title: "Одежда",
    topic: "things",
    note: "qmis — рубашка, qalziet — брюки. Оба слова мужского рода.",
    lines: [
      { who: "A", mt: "Dan il-qmis huwa ġdid?", ru: "Эта рубашка новая?" },
      { who: "B", mt: "Iva, ġdid.", ru: "Да, новая." },
      { who: "A", mt: "U l-qalziet?", ru: "А брюки?" },
      { who: "B", mt: "Dan huwa qadim.", ru: "Они старые." },
      { who: "A", mt: "Irrid nixtri qmis ġdid ukoll.", ru: "Я тоже хочу купить новую рубашку." },
      { who: "B", mt: "Ejja fil-ħanut.", ru: "Пойдём в магазин." }
    ]
  },
  {
    id: "computer",
    title: "За компьютером",
    topic: "office",
    note: "mhux qed jaħdem — «не работает», дословно «не делает».",
    lines: [
      { who: "A", mt: "Il-kompjuter tiegħi mhux qed jaħdem.", ru: "Мой компьютер не работает." },
      { who: "B", mt: "Għandek fajl importanti?", ru: "У тебя есть важный файл?" },
      { who: "A", mt: "Iva, għandi dokument importanti.", ru: "Да, у меня важный документ." },
      { who: "B", mt: "Dan huwa problema kbira.", ru: "Это большая проблема." },
      { who: "A", mt: "Iva, problema kbira.", ru: "Да, большая проблема." },
      { who: "B", mt: "Irrid nara dan.", ru: "Мне надо это посмотреть." }
    ]
  },
  {
    id: "party",
    title: "Праздник и подарок",
    topic: "greet",
    note: "il-festa — праздник. Forsi — «может быть».",
    lines: [
      { who: "A", mt: "Il-festa hija għada?", ru: "Праздник завтра?" },
      { who: "B", mt: "Iva, għada filgħaxija.", ru: "Да, завтра вечером." },
      { who: "A", mt: "Irrid nixtri rigal.", ru: "Я хочу купить подарок." },
      { who: "B", mt: "X'trid tixtri?", ru: "Что ты хочешь купить?" },
      { who: "A", mt: "Forsi ktieb.", ru: "Может быть, книгу." },
      { who: "B", mt: "Tajjeb ħafna!", ru: "Очень хорошо!" }
    ]
  },
  {
    id: "petrol",
    title: "На заправке",
    topic: "travel",
    note: "ħanut tal-petrol — заправка, дословно «магазин бензина».",
    lines: [
      { who: "A", mt: "Għandek karozza?", ru: "У тебя есть машина?" },
      { who: "B", mt: "Iva, imma hija qadima.", ru: "Да, но она старая." },
      { who: "A", mt: "Trid petrol?", ru: "Тебе нужен бензин?" },
      { who: "B", mt: "Iva, il-karozza għandha bżonn petrol.", ru: "Да, машине нужен бензин." },
      { who: "A", mt: "Hawn ħanut tal-petrol qrib.", ru: "Здесь рядом заправка." },
      { who: "B", mt: "Tajjeb. Ejja.", ru: "Хорошо. Поехали." }
    ]
  },
  {
    id: "appointment",
    title: "Запись к врачу",
    topic: "body",
    note: "it-tabib — врач. Għada filgħodu — «завтра утром».",
    lines: [
      { who: "A", mt: "Irrid appuntament mat-tabib.", ru: "Я хочу запись к врачу." },
      { who: "B", mt: "Meta trid?", ru: "Когда ты хочешь?" },
      { who: "A", mt: "Għada filgħodu.", ru: "Завтра утром." },
      { who: "B", mt: "Fi tlieta, jekk jogħġbok.", ru: "В три, пожалуйста." },
      { who: "A", mt: "Tajjeb. Grazzi.", ru: "Хорошо. Спасибо." },
      { who: "B", mt: "Saħħa!", ru: "Пока!" }
    ]
  }
];
