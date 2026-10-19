(function () {
  "use strict";

  var WORDS = window.WORDS || [];
  var SENTENCES = window.SENTENCES || [];
  var IPA_DATA = window.IPA_DATA || {};
  var SENTENCE_LINKS = window.SENTENCE_LINKS || {};

  // Сколько незнакомых слов допускается во фразе, чтобы она открылась.
  var MAX_UNFAMILIAR = 1;
  var DEFAULT_SENT_LIMIT = 5;

  var WORD_BY_MT = {};
  WORDS.forEach(function (w) { WORD_BY_MT[w.mt] = w; });

  // обратный индекс: слово -> фразы, в которых оно встречается
  var SENTENCES_BY_WORD = {};
  SENTENCES.forEach(function (s) {
    var link = SENTENCE_LINKS[s.mt];
    if (!link) return;
    (link.words || []).forEach(function (mt) {
      if (!SENTENCES_BY_WORD[mt]) SENTENCES_BY_WORD[mt] = [];
      SENTENCES_BY_WORD[mt].push(s);
    });
  });

  var TOPICS = {
    numbers: "Числа",
    pron: "Местоимения",
    qword: "Вопросительные слова",
    base: "Базовые слова",
    adj: "Прилагательные",
    color: "Цвета",
    family: "Семья",
    food: "Еда и напитки",
    time: "Время и дни",
    body: "Тело",
    house: "Дом",
    nature: "Природа и животные",
    place: "Город и места",
    travel: "Транспорт",
    verb: "Глаголы",
    greet: "Приветствия",
    present: "Настоящее время",
    have: "Иметь (għandi)",
    want: "Хотеть",
    question: "Вопросы",
    weather: "Погода",
    number: "Числа и покупки",
    everyday: "На каждый день"
  };

  var POS = {
    noun: "сущ.",
    verb: "гл.",
    adj: "прил."
  };

  var INTERVALS = [0, 1, 2, 4, 8, 16];
  var DEFAULT_NEW_LIMIT = 10;
  var STORE_KEY = "il-malti-v1";
  var TRANSLIT_KEY = "il-malti-translit";

  var showTranslit = true;
  try {
    showTranslit = localStorage.getItem(TRANSLIT_KEY) !== "0";
  } catch (e) {}

  var EXAMPLES_KEY = "il-malti-examples";
  var showExamples = true;
  try {
    showExamples = localStorage.getItem(EXAMPLES_KEY) !== "0";
  } catch (e) {}

  /* ---------- storage ---------- */

  function freshState() {
    return {
      items: {},
      stats: { word: { ok: 0, no: 0 }, sent: { ok: 0, no: 0 }, pair: { ok: 0, no: 0 } },
      days: {}
    };
  }

  var state = freshState();

  function loadState() {
    try {
      var raw = localStorage.getItem(STORE_KEY);
      if (raw) {
        var parsed = JSON.parse(raw);
        state = Object.assign(freshState(), parsed);
        state.items = parsed.items || {};
        state.days = parsed.days || {};
        state.stats = parsed.stats || {};
        ["word", "sent", "pair"].forEach(function (k) {
          state.stats[k] = state.stats[k] || { ok: 0, no: 0 };
        });
      }
    } catch (e) {}
  }

  function saveState() {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(state));
    } catch (e) {}
  }

  function dayNumber(dt) {
    var d = dt ? new Date(dt) : new Date();
    var local = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    return Math.round(local.getTime() / 86400000);
  }

  function dateKey(dt) {
    var d = dt ? new Date(dt) : new Date();
    var p = function (n) { return String(n).padStart(2, "0"); };
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
  }

  function rec(id) {
    if (!state.items[id]) state.items[id] = { b: 0, d: 0 };
    return state.items[id];
  }

  function isDue(id) {
    var r = state.items[id];
    return !r || r.d <= dayNumber();
  }

  function hasRec(id) {
    return !!state.items[id];
  }

  // Слово, введённое впервые сегодня (по нему ещё не было ответов).
  function isNewWord(w) {
    return !hasRec(wid(w));
  }

  // Слова с наступившим сроком повторения, но уже изученные.
  function isDueReview(w) {
    var r = state.items[wid(w)];
    return !!r && r.d <= dayNumber();
  }

  function newLimit() {
    return state.limit === undefined ? DEFAULT_NEW_LIMIT : state.limit;
  }

  // id записей слов имеют префикс "w:", предложений - "s:".
  function isWordId(id) { return id.indexOf("w:") === 0; }

  function countIntroduced(prefix) {
    var today = dayNumber();
    var n = 0;
    for (var id in state.items) {
      if (id.indexOf(prefix) === 0 && state.items[id].f === today) n++;
    }
    return n;
  }

  function introducedToday() { return countIntroduced("w:"); }

  function introducedSentToday() { return countIntroduced("s:"); }

  function sentLimit() {
    return state.sentLimit === undefined ? DEFAULT_SENT_LIMIT : state.sentLimit;
  }

  function sentRemaining() {
    var limit = sentLimit();
    if (!limit) return Infinity;
    return Math.max(0, limit - introducedSentToday());
  }

  function newRemaining() {
    var limit = newLimit();
    if (!limit) return Infinity;
    return Math.max(0, limit - introducedToday());
  }

  function grade(id, kind, ok) {
    var r = rec(id);
    if (r.f === undefined) r.f = dayNumber();
    r.b = ok ? Math.min(r.b + 1, INTERVALS.length - 1) : 0;
    r.d = dayNumber() + INTERVALS[r.b];
    if (ok) state.stats[kind].ok++; else state.stats[kind].no++;
    var k = dateKey();
    state.days[k] = (state.days[k] || 0) + 1;
    saveState();
  }

  /* ---------- helpers ---------- */

  function $(id) { return document.getElementById(id); }

  function shuffle(a) {
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  function topicLabel(t) { return TOPICS[t] || t; }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  var toastTimer = null;
  function toast(msg) {
    var el = $("toast");
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.hidden = true; }, 2200);
  }

  function translitHtml(mt) {
    var rec = IPA_DATA[mt];
    if (!showTranslit || !rec) return "";
    return '<span class="ipa">' + escapeHtml(rec.ipa) + "</span>" +
      '<span class="ru-say">' + escapeHtml(rec.ru) + "</span>";
  }

  function renderTranslit(el, mt) {
    if (!el) return;
    var html = translitHtml(mt);
    el.innerHTML = html;
    el.hidden = !html;
  }

  // Короткие фразы идут первыми: их легче читать.
  function examplesFor(mt, limit) {
    var list = SENTENCES_BY_WORD[mt] || [];
    return list.slice().sort(function (a, b) {
      return a.mt.split(" ").length - b.mt.split(" ").length || a.mt.length - b.mt.length;
    }).slice(0, limit || 2);
  }

  // Подсветить слово в примере: позиции токенов берём из data/links.js,
  // поэтому подсвечивается именно та форма, что стоит в предложении.
  function highlightExample(s, mt) {
    var parts = s.mt.split(" ");
    var link = SENTENCE_LINKS[s.mt] || {};
    var pos = (link.pos || {})[mt] || [];
    return parts.map(function (part, i) {
      if (pos.indexOf(i) < 0) return escapeHtml(part);
      // выделяем только буквы, знаки препинания оставляем снаружи
      var m = /^([^A-Za-zÀ-ÿĊċĠġĦħŻż]*)(.*?)([^A-Za-zÀ-ÿĊċĠġĦħŻż]*)$/.exec(part);
      if (!m) return escapeHtml(part);
      return escapeHtml(m[1]) + '<b class="hl">' + escapeHtml(m[2]) + "</b>" +
        escapeHtml(m[3]);
    }).join(" ");
  }

  // mode: "none" — не показывать, "front" — только мальтийский, "full" — с переводом
  function renderExamples(mt, mode) {
    if (!showExamples || mode === "none") return "";
    var list = examplesFor(mt, 2);
    if (!list.length) {
      return mode === "full"
        ? '<div class="examples"><div class="ex-empty">Примеров для этого слова пока нет — ' +
          "оно не встречается ни в одной фразе.</div></div>"
        : "";
    }
    return '<div class="examples">' + list.map(function (s) {
      return '<div class="ex"><div class="ex-mt">' + highlightExample(s, mt) + "</div>" +
        (mode === "full"
          ? '<div class="ex-ru">' + escapeHtml(s.ru) + "</div>"
          : "") +
        "</div>";
    }).join("") + "</div>";
  }

  function norm(s) {
    return String(s == null ? "" : s).toLowerCase()
      .replace(/[\u2018\u2019\u00b4`]/g, "'")
      .replace(/[.,!?;:\u00ab\u00bb\u201e\u201c\u201d()\[\]]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  var malteseVoice = null;
  function pickVoice() {
    if (!("speechSynthesis" in window)) return;
    var voices = window.speechSynthesis.getVoices() || [];
    malteseVoice = voices.find(function (v) { return /^mt([-_]|$)/i.test(v.lang); }) || null;
  }

  function speak(text) {
    if (!("speechSynthesis" in window)) { toast("Синтез речи не поддерживается"); return; }
    if (!text) return;
    if (!malteseVoice) pickVoice();
    if (!malteseVoice) { toast("Мальтийский голос (mt) не найден в системе"); return; }
    var u = new SpeechSynthesisUtterance(text);
    u.voice = malteseVoice;
    u.lang = malteseVoice.lang;
    u.rate = 0.9;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
  }

  function fillTopicSelect(sel, arr) {
    if (!sel) return;
    var seen = [];
    arr.forEach(function (x) { if (seen.indexOf(x.topic) === -1) seen.push(x.topic); });
    sel.innerHTML = '<option value="all">Все темы</option>' + seen.map(function (t) {
      return '<option value="' + t + '">' + escapeHtml(topicLabel(t)) + "</option>";
    }).join("");
  }

  /* ---------- tabs ---------- */

  function initTabs() {
    var tabs = $("tabs");
    tabs.addEventListener("click", function (e) {
      var btn = e.target.closest(".tab");
      if (!btn) return;
      selectTab(btn.dataset.tab);
    });
    selectTab("words");
  }

  function selectTab(name) {
    Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (b) {
      b.classList.toggle("active", b.dataset.tab === name);
    });
    Array.prototype.forEach.call(document.querySelectorAll(".view"), function (v) {
      v.hidden = v.id !== "view-" + name;
    });
    if (name === "progress") renderProgress();
    if (name === "words") showWord();
    if (name === "sentences") showSentence();
    if (name === "pairs") showPair();
  }

  /* ---------- words ---------- */

  var wPool = [], wIndex = 0, wTopic = "all", wDir = "mt-ru", wRevealed = false;
  var wBypass = false, wReviewAll = false;

  function wid(w) { return "w:" + w.mt; }

  function initWords() {
    fillTopicSelect($("w-topic"), WORDS);
    $("w-topic").addEventListener("change", function (e) {
      wTopic = e.target.value; wBypass = false; wReviewAll = false; buildWordQueue();
    });
    $("w-dir").addEventListener("change", function (e) { wDir = e.target.value; showWord(); });
    $("w-shuffle").addEventListener("click", function () { shuffle(wPool); wIndex = 0; showWord(); });
    $("w-show").addEventListener("click", revealWord);
    $("w-no").addEventListener("click", function () { answerWord(false); });
    $("w-yes").addEventListener("click", function () { answerWord(true); });
    $("w-speak").addEventListener("click", function () {
      var w = wPool[wIndex];
      if (w) speak(w.mt);
    });
    $("w-examples-toggle").checked = showExamples;
    $("w-examples-toggle").addEventListener("change", function (e) {
      showExamples = e.target.checked;
      try { localStorage.setItem(EXAMPLES_KEY, showExamples ? "1" : "0"); } catch (err) {}
      showWord();
    });
    $("w-translit").checked = showTranslit;
    $("w-translit").addEventListener("change", function (e) {
      showTranslit = e.target.checked;
      try { localStorage.setItem(TRANSLIT_KEY, showTranslit ? "1" : "0"); } catch (err) {}
      showWord();
    });
    $("w-limit").value = String(newLimit());
    $("w-limit").addEventListener("change", function (e) {
      state.limit = Number(e.target.value);
      saveState();
      wBypass = false;
      buildWordQueue();
    });
    $("w-bypass").addEventListener("click", function () {
      wBypass = true;
      buildWordQueue();
    });
    $("w-review-all").addEventListener("click", function () {
      wReviewAll = true;
      buildWordQueue();
    });
    buildWordQueue();
  }

  function buildWordQueue() {
    var pool = WORDS.filter(function (w) { return wTopic === "all" || w.topic === wTopic; });
    wIndex = 0;

    if (!pool.length) { wPool = []; showWord(); return; }

    if (wReviewAll) {
      wPool = shuffle(pool.slice());
      showWord();
      return;
    }

    // Повторения идут первыми: если прервать занятие, они уже сделаны.
    var reviews = pool.filter(isDueReview).sort(function (a, b) {
      return state.items[wid(a)].d - state.items[wid(b)].d;
    });

    var news = shuffle(pool.filter(isNewWord));
    var allowed = wBypass ? news.length : newRemaining();
    if (allowed !== Infinity) news = news.slice(0, allowed);

    wPool = reviews.concat(news);
    showWord();
  }

  function nextDueDate(prefix) {
    var soonest = null;
    for (var id in state.items) {
      if (id.indexOf(prefix) !== 0) continue;
      var d = state.items[id].d;
      if (d > dayNumber() && (soonest === null || d < soonest)) soonest = d;
    }
    if (soonest === null) return "нет запланированных повторений";
    var days = soonest - dayNumber();
    var when = days === 1 ? "завтра" : "через " + days + " дн.";
    var dt = new Date();
    dt.setDate(dt.getDate() + days);
    return when + ", " + dateKey(dt);
  }

  function showWord() {
    var w = wPool[wIndex];
    var card = $("w-card");
    var done = $("w-done");

    if (!w) {
      card.hidden = true;
      $("w-actions").hidden = true;
      $("w-speak-row").hidden = true;
      done.hidden = false;

      var pool = WORDS.filter(function (x) { return wTopic === "all" || x.topic === wTopic; });
      var limit = newLimit();
      var left = pool.filter(isNewWord).length;

      if (wReviewAll) {
        $("w-done-title").textContent = "Повторение завершено";
        $("w-done-text").textContent = "Пройдено слов: " + pool.length + ".";
        $("w-counter").textContent = "";
      } else {
        $("w-done-title").textContent = "На сегодня всё";
        $("w-done-text").textContent = limit
          ? "Новых сегодня: " + introducedToday() + " из " + limit +
            ". Осталось новых слов в теме: " + left +
            ". Следующее повторение: " + nextDueDate("w:") + "."
          : "Следующее повторение: " + nextDueDate("w:") + ".";
        $("w-counter").textContent = "Новых сегодня: " + introducedToday() +
          (limit ? " из " + limit : "") + " · к повторению сейчас: 0";
      }
      wBypass = false;
      return;
    }

    card.hidden = false;
    done.hidden = true;
    $("w-actions").hidden = false;
    $("w-speak-row").hidden = false;
    wRevealed = false;

    var front = wDir === "mt-ru" ? w.mt : w.ru;
    var back = wDir === "mt-ru" ? w.ru : w.mt;

    $("w-front").textContent = front;
    $("w-tag").textContent = topicLabel(w.topic) + (w.pos ? " · " + (POS[w.pos] || w.pos) : "");

    var detail = $("w-back-detail");
    detail.innerHTML = "";
    if (wDir === "mt-ru" && (w.art || w.pl || w.forms)) {
      var bits = [];
      if (w.art) bits.push("Артикль: " + escapeHtml(w.art));
      if (w.pl) bits.push("Мн. ч.: " + escapeHtml(w.pl));
      if (w.forms) bits.push("Формы: " + escapeHtml(w.forms));
      detail.innerHTML = bits.map(function (b) { return "<div>" + b + "</div>"; }).join("");
    }
    $("w-back").textContent = back;
    $("w-back").hidden = true;
    $("w-back-detail").hidden = true;
    renderTranslit($("w-translit-back"), "");
    renderTranslit($("w-translit-front"), wDir === "mt-ru" ? w.mt : "");
    $("w-examples").innerHTML = renderExamples(w.mt, wDir === "mt-ru" ? "front" : "none");

    $("w-show").hidden = false;
    $("w-grade").hidden = true;

    var limit = newLimit();
    var parts = ["В очереди: " + (wPool.length - wIndex)];
    if (wReviewAll) parts.push("режим повторения");
    else {
      if (limit) parts.push("новых сегодня: " + introducedToday() + "/" + limit);
      if (wBypass) parts.push("сверх лимита");
    }
    $("w-counter").textContent = parts.join(" · ");
    card.classList.remove("revealed");
  }

  function revealWord() {
    var w = wPool[wIndex];
    if (!w || wRevealed) return;
    wRevealed = true;
    $("w-back").hidden = false;
    $("w-back-detail").hidden = false;
    if (wDir === "ru-mt") renderTranslit($("w-translit-back"), w.mt);
    $("w-examples").innerHTML = renderExamples(w.mt, "full");
    $("w-show").hidden = true;
    $("w-grade").hidden = false;
    $("w-card").classList.add("revealed");
  }

  function answerWord(ok) {
    var w = wPool[wIndex];
    if (!w) return;
    grade(wid(w), "word", ok);
    wIndex++;
    if (wIndex < wPool.length) { showWord(); return; }

    // Очередь исчерпана: собрать следующую либо показать «на сегодня всё».
    if (wReviewAll) {
      wPool = [];
      wIndex = 0;
      showWord();
      wReviewAll = false;
      return;
    }
    wBypass = false;
    buildWordQueue();
  }

  /* ---------- sentences ---------- */

  var sPool = [], sIndex = 0, sTopic = "all", sMode = "build";
  var sTokens = [], sAnswer = [], sRevealed = false;
  var sBypass = false, sReviewAll = false, sLocked = 0, sUnlocked = 0;

  function sid(s) { return "s:" + s.mt; }

  function slink(s) { return SENTENCE_LINKS[s.mt] || { words: [], unknown: [] }; }

  function linkedOf(s) {
    return slink(s).words.map(function (mt) { return WORD_BY_MT[mt]; })
      .filter(function (w) { return !!w; });
  }

  function unfamiliarOf(s) {
    return linkedOf(s).filter(function (w) { return !hasRec(wid(w)); });
  }

  function familiarOf(s) {
    return linkedOf(s).filter(function (w) { return hasRec(wid(w)); });
  }

  // Фраза открывается, когда в ней не больше MAX_UNFAMILIAR незнакомых слов.
  function isUnlocked(s) { return unfamiliarOf(s).length <= MAX_UNFAMILIAR; }

  function initSentences() {
    fillTopicSelect($("s-topic"), SENTENCES);
    $("s-topic").addEventListener("change", function (e) {
      sTopic = e.target.value; sBypass = false; sReviewAll = false; buildSentencePool();
    });
    $("s-mode").addEventListener("change", function (e) { sMode = e.target.value; showSentence(); });
    $("s-next").addEventListener("click", nextSentence);
    $("s-check").addEventListener("click", checkSentence);
    $("s-reveal").addEventListener("click", revealSentence);
    $("s-again").addEventListener("click", showSentence);
    $("s-speak").addEventListener("click", function () {
      if (sPool[sIndex]) speak(sPool[sIndex].mt);
    });
    $("s-yes").addEventListener("click", function () { gradeSentence(true); });
    $("s-no").addEventListener("click", function () { gradeSentence(false); });
    $("s-limit").value = String(sentLimit());
    $("s-limit").addEventListener("change", function (e) {
      state.sentLimit = Number(e.target.value);
      saveState();
      sBypass = false;
      buildSentencePool();
    });
    $("s-bypass").addEventListener("click", function () { sBypass = true; buildSentencePool(); });
    $("s-review-all").addEventListener("click", function () { sReviewAll = true; buildSentencePool(); });

    renderSpecialKeys($("s-kbd"), function (ch) { insertAtCursor($("s-input"), ch); });
    buildSentencePool();
  }

  // Правильная форма слова после числа: 1 фраза / 2 фразы / 5 фраз.
  function plural(n, one, few, many) {
    var m10 = n % 10, m100 = n % 100;
    if (m10 === 1 && m100 !== 11) return one;
    if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
    return many;
  }

  function hintText(hint) {
    if (!hint.words.length) return "";
    return " Выучи эти слова, чтобы открыть больше фраз: " +
      hint.words.map(function (x) {
        return x.word.mt + " (" + x.word.ru + ") — " + x.count + " " +
          plural(x.count, "фраза", "фразы", "фраз");
      }).join("; ") + ".";
  }

  // Слова, которых не хватает для ближайших закрытых фраз.
  function unlockHint() {
    var all = SENTENCES.filter(function (s) { return sTopic === "all" || s.topic === sTopic; });
    var missing = {};
    var locked = all.filter(function (s) { return !isUnlocked(s); });
    locked.forEach(function (s) {
      var need = unfamiliarOf(s);
      if (need.length > MAX_UNFAMILIAR + 1) return;
      need.forEach(function (w) { missing[w.mt] = (missing[w.mt] || 0) + 1; });
    });
    var top = Object.keys(missing).sort(function (a, b) { return missing[b] - missing[a]; }).slice(0, 6);
    return { locked: locked.length, words: top.map(function (mt) {
      return { word: WORD_BY_MT[mt], count: missing[mt] };
    }) };
  }

  function buildSentencePool() {
    var all = SENTENCES.filter(function (s) { return sTopic === "all" || s.topic === sTopic; });
    sIndex = 0;

    var unlocked = all.filter(isUnlocked);
    sLocked = all.length - unlocked.length;
    sUnlocked = unlocked.length;

    if (sReviewAll) {
      sPool = shuffle(unlocked.slice());
      showSentence();
      return;
    }

    var reviews = unlocked.filter(function (s) {
      var r = state.items[sid(s)];
      return !!r && r.d <= dayNumber();
    }).sort(function (a, b) {
      return state.items[sid(a)].d - state.items[sid(b)].d;
    });

    // Сначала самые "знакомые" фразы: меньше незнакомых слов.
    var news = unlocked.filter(function (s) { return !hasRec(sid(s)); })
      .sort(function (a, b) { return unfamiliarOf(a).length - unfamiliarOf(b).length; });

    var allowed = sBypass ? news.length : sentRemaining();
    if (allowed !== Infinity) news = news.slice(0, allowed);

    sPool = reviews.concat(news);
    showSentence();
  }

  function tokenize(mt) {
    return mt.split(/\s+/).filter(Boolean).map(function (t) {
      return { clean: t.replace(/^[\u00ab"'(]+|[\u00bb".,!?;:)]+$/g, ""), raw: t };
    });
  }

  function showSentence() {
    var s = sPool[sIndex];

    if (!s) {
      $("s-prompt").hidden = true;
      $("s-work").hidden = true;
      $("s-actions").hidden = true;
      $("s-speak-row").hidden = true;
      $("s-done").hidden = false;
      sBypass = false;

      if (sReviewAll) {
        $("s-done-title").textContent = "Повторение завершено";
        $("s-done-text").textContent = "Пройдено фраз: " + sPool.length + ".";
        $("s-counter").textContent = "";
        $("s-done-actions").hidden = true;
        sReviewAll = false;
        return;
      }

      var hint = unlockHint();
      if (sUnlocked === 0) {
        $("s-done").classList.add("locked");
        $("s-done-title").textContent = "Фразы пока закрыты";
        $("s-done-text").textContent =
          "Ни одна фраза этой темы ещё не открыта: в каждой должно быть не больше " +
          MAX_UNFAMILIAR + " незнакомого слова." + hintText(hint);
        $("s-counter").textContent = "";
        $("s-done-actions").hidden = true;
        return;
      }

      $("s-done").classList.remove("locked");
      $("s-done-title").textContent = "На сегодня всё";
      $("s-done-text").textContent =
        "Новых фраз сегодня: " + introducedSentToday() +
        (sentLimit() ? " из " + sentLimit() : "") +
        ". Следующее повторение: " + nextDueDate("s:") + "." + hintText(hint);
      $("s-counter").textContent = "Новых фраз сегодня: " + introducedSentToday() +
        (sentLimit() ? " из " + sentLimit() : "") + " · к повторению сейчас: 0";
      $("s-done-actions").hidden = false;
      return;
    }

    $("s-done").hidden = true;
    $("s-done-actions").hidden = false;
    $("s-prompt").hidden = false;
    $("s-work").hidden = false;
    $("s-actions").hidden = false;
    $("s-speak-row").hidden = false;
    sRevealed = false;

    var linked = linkedOf(s);
    var unfamiliar = unfamiliarOf(s);

    $("s-ru").textContent = s.ru;
    $("s-hint").textContent = "Тема: " + topicLabel(s.topic);

    var parts = ["Фраза " + (sIndex + 1) + " из " + sPool.length];
    if (linked.length) {
      parts.push("знакомые слова: " + (linked.length - unfamiliar.length) + " из " + linked.length);
    }
    if (unfamiliar.length) parts.push("новых: " + unfamiliar.length);
    if (sReviewAll) parts.push("режим повторения");
    if (sBypass) parts.push("сверх лимита");
    parts.push("открыто фраз: " + (SENTENCES.length - sLocked) + " из " + SENTENCES.length);
    $("s-counter").textContent = parts.join(" · ");

    $("s-known").innerHTML = renderNewWords(unfamiliar, false);
    $("s-feedback").textContent = "";
    $("s-feedback").className = "feedback";
    $("s-reveal").hidden = false;
    $("s-grade").hidden = true;
    renderTranslit($("s-translit"), "");

    var isBuild = sMode === "build";
    var isType = sMode === "type";
    var isCard = sMode === "card";

    $("s-build").hidden = !isBuild;
    $("s-type").hidden = !isType;
    $("s-cardbox").hidden = !isCard;
    $("s-check").hidden = isCard;
    $("s-reveal").textContent = isCard ? "Показать ответ" : "Подсказка (показать ответ)";

    if (isBuild) {
      sTokens = tokenize(s.mt);
      sAnswer = [];
      renderBuild();
    } else if (isType) {
      $("s-input").value = "";
      $("s-input").focus();
    } else if (isCard) {
      $("s-mt").textContent = s.mt;
    }
  }

  // Список незнакомых слов фразы. Пока ответ не показан, в режиме ввода
  // и карточки раскрывать их нельзя — это была бы подсказка.
  function renderNewWords(unfamiliar, reveal) {
    if (!unfamiliar.length) return "";
    var show = reveal || sMode === "build";
    return '<span class="new-words">' +
      (show ? "Новые слова: " : "Новых слов во фразе: " + unfamiliar.length + " — ") +
      (show ? unfamiliar.map(function (w) {
        return "<b>" + escapeHtml(w.mt) + "</b> — " + escapeHtml(w.ru);
      }).join(", ") : "нажми «Показать ответ»") +
      "</span>";
  }

  function renderBuild() {
    var chips = $("s-chips");
    var ans = $("s-answer");
    if (!sTokens.length) { chips.innerHTML = ""; ans.innerHTML = ""; return; }
    var order = sTokens.map(function (_, i) { return i; });
    shuffle(order);
    chips.innerHTML = order.map(function (i) {
      return '<button class="chip" data-i="' + i + '">' + escapeHtml(sTokens[i].clean) + "</button>";
    }).join("");
    ans.innerHTML = sAnswer.length
      ? sAnswer.map(function (i) {
        return '<button class="chip placed" data-i="' + i + '">' + escapeHtml(sTokens[i].clean) + "</button>";
      }).join("")
      : '<span class="placeholder">Нажимайте слова по порядку…</span>';
    $("s-build").classList.add("has-answer");
  }

  function onChipClick(e) {
    var btn = e.target.closest(".chip");
    if (!btn) return;
    var i = Number(btn.dataset.i);
    if (btn.classList.contains("placed")) {
      sAnswer = sAnswer.filter(function (x) { return x !== i; });
    } else {
      if (sAnswer.indexOf(i) !== -1) return;
      sAnswer.push(i);
    }
    renderBuild();
  }

  function checkSentence() {
    var s = sPool[sIndex];
    if (!s) return;
    var user;
    if (sMode === "build") {
      user = sAnswer.map(function (i) { return sTokens[i].clean; }).join(" ");
    } else {
      user = $("s-input").value;
    }
    var ok = norm(user) === norm(s.mt);
    feedback(ok, s);
    renderTranslit($("s-translit"), s.mt);
    $("s-known").innerHTML = renderNewWords(unfamiliarOf(s), true);
    grade(sid(s), "sent", ok);
    if (ok) {
      var graded = s;
      window.setTimeout(function () { if (sPool[sIndex] === graded) nextSentence(); }, 900);
    }
  }

  function revealSentence() {
    var s = sPool[sIndex];
    if (!s || sRevealed) return;
    sRevealed = true;
    if (sMode === "build") {
      var order = [];
      var used = {};
      tokenize(s.mt).forEach(function (t) {
        for (var i = 0; i < sTokens.length; i++) {
          if (!used[i] && sTokens[i].clean === t.clean) { used[i] = true; order.push(i); break; }
        }
      });
      sAnswer = order;
      renderBuild();
    } else if (sMode === "type") {
      $("s-input").value = s.mt;
    } else {
      $("s-mt").textContent = s.mt;
    }
    feedback(true, s, true);
    renderTranslit($("s-translit"), s.mt);
    $("s-known").innerHTML = renderNewWords(unfamiliarOf(s), true);
    if (sMode === "card") $("s-grade").hidden = false;
  }

  function feedback(ok, s, revealed) {
    var el = $("s-feedback");
    if (ok && !revealed) {
      el.textContent = "Правильно!";
      el.className = "feedback good";
    } else if (revealed) {
      el.textContent = "Ответ: " + s.mt;
      el.className = "feedback neutral";
    } else {
      el.textContent = "Не так. Правильно: " + s.mt;
      el.className = "feedback bad";
    }
  }

  function gradeSentence(ok) {
    var s = sPool[sIndex];
    if (!s) return;
    grade(sid(s), "sent", ok);
    nextSentence();
  }

  function nextSentence() {
    if (!sPool.length) return;
    sIndex++;
    if (sIndex < sPool.length) { showSentence(); return; }

    // Очередь исчерпана: собрать следующую либо показать итог.
    if (sReviewAll) { sPool = []; sIndex = 0; showSentence(); return; }
    sBypass = false;
    buildSentencePool();
  }

  function insertAtCursor(el, text) {
    if (!el) return;
    var start = el.selectionStart == null ? el.value.length : el.selectionStart;
    var end = el.selectionEnd == null ? el.value.length : el.selectionEnd;
    el.value = el.value.slice(0, start) + text + el.value.slice(end);
    var pos = start + text.length;
    el.selectionStart = el.selectionEnd = pos;
    el.focus();
  }

  function renderSpecialKeys(container, onPick) {
    if (!container) return;
    var keys = ["ċ", "ġ", "ħ", "ż", "Ġ", "Ħ", "Ż", "għ", "ie", "q", "'"];
    container.innerHTML = keys.map(function (k) {
      return '<button class="key" type="button">' + escapeHtml(k) + "</button>";
    }).join("");
    container.addEventListener("click", function (e) {
      var b = e.target.closest(".key");
      if (b) onPick(b.textContent);
    });
  }

  /* ---------- pairs: noun + verb ---------- */

  var PAIRS = window.PAIRS || [];
  var DEFAULT_PAIR_LIMIT = 10;
  var GENDERS = [
    { key: "m", label: "м. род" },
    { key: "f", label: "ж. род" },
    { key: "pl", label: "мн. ч." }
  ];

  var xPool = [], xIndex = 0, xState = "ask", xBypass = false;
  var xPicked = { gender: null, form: null, ru: null };

  function pid(p) { return "p:" + p.phrase; }

  function pairLimit() {
    return state.pairLimit === undefined ? DEFAULT_PAIR_LIMIT : state.pairLimit;
  }

  function introducedPairsToday() { return countIntroduced("p:"); }

  function pairRemaining() {
    var limit = pairLimit();
    if (!limit) return Infinity;
    return Math.max(0, limit - introducedPairsToday());
  }

  function initPairs() {
    $("pr-limit").value = String(pairLimit());
    $("pr-limit").addEventListener("change", function (e) {
      state.pairLimit = Number(e.target.value);
      saveState();
      xBypass = false;
      buildPairPool();
    });
    $("pr-shuffle").addEventListener("click", function () { shuffle(xPool); xIndex = 0; showPair(); });
    $("pr-check").addEventListener("click", checkPair);
    $("pr-reveal").addEventListener("click", revealPair);
    $("pr-next").addEventListener("click", nextPair);
    $("pr-bypass").addEventListener("click", function () { xBypass = true; buildPairPool(); });
    $("pr-speak").addEventListener("click", function () {
      var p = xPool[xIndex];
      if (p) speak(p.phrase);
    });
    $("pr-quiz").addEventListener("click", onPairOption);
    buildPairPool();
  }

  function buildPairPool() {
    xIndex = 0;
    var reviews = PAIRS.filter(function (p) {
      var r = state.items[pid(p)];
      return !!r && r.d <= dayNumber();
    }).sort(function (a, b) {
      return state.items[pid(a)].d - state.items[pid(b)].d;
    });

    var news = shuffle(PAIRS.filter(function (p) { return !state.items[pid(p)]; }));
    var allowed = xBypass ? news.length : pairRemaining();
    if (allowed !== Infinity) news = news.slice(0, allowed);

    xPool = reviews.concat(news);
    showPair();
  }

  function translationOptions(p) {
    var out = [p.ru];
    var rest = shuffle(PAIRS.filter(function (q) { return q.ru !== p.ru; }));
    for (var i = 0; i < rest.length && out.length < 3; i++) {
      if (out.indexOf(rest[i].ru) === -1) out.push(rest[i].ru);
    }
    return out;
  }

  function showPair() {
    var p = xPool[xIndex];
    var card = $("pr-card");

    if (!p) {
      card.hidden = true;
      $("pr-quiz").hidden = true;
      $("pr-actions").hidden = true;
      $("pr-speak-row").hidden = true;
      $("pr-done").hidden = false;
      $("pr-done-text").textContent = pairLimit()
        ? "Новых сочетаний сегодня: " + introducedPairsToday() + " из " + pairLimit() +
          ". Следующее повторение: " + nextDueDate("p:") + "."
        : "Следующее повторение: " + nextDueDate("p:") + ".";
      $("pr-counter").textContent = "";
      xBypass = false;
      return;
    }

    card.hidden = false;
    $("pr-done").hidden = true;
    $("pr-quiz").hidden = false;
    $("pr-actions").hidden = false;
    $("pr-speak-row").hidden = false;
    xState = "ask";
    xPicked = { gender: null, form: null, ru: null };

    $("pr-noun").textContent = p.subject;
    $("pr-verb").textContent = p.verbMt;

    $("pr-gender").innerHTML = GENDERS.map(function (g) {
      return '<button class="opt" data-kind="gender" data-val="' + g.key + '">' +
        g.label + "</button>";
    }).join("");

    $("pr-form").innerHTML = shuffle(p.forms.slice()).map(function (f) {
      return '<button class="opt" data-kind="form" data-val="' + escapeHtml(f) + '">' +
        escapeHtml(f) + "</button>";
    }).join("");

    $("pr-ru").innerHTML = shuffle(translationOptions(p)).map(function (r) {
      return '<button class="opt" data-kind="ru" data-val="' + escapeHtml(r) + '">' +
        escapeHtml(r) + "</button>";
    }).join("");

    $("pr-feedback").textContent = "";
    $("pr-feedback").className = "feedback";
    $("pr-answer").hidden = true;
    $("pr-answer").innerHTML = "";
    renderTranslit($("pr-translit"), "");
    $("pr-check").hidden = false;
    $("pr-reveal").hidden = false;
    $("pr-next").hidden = true;

    var parts = ["Сочетание " + (xIndex + 1) + " из " + xPool.length];
    if (pairLimit()) parts.push("новых сегодня: " + introducedPairsToday() + "/" + pairLimit());
    if (xBypass) parts.push("сверх лимита");
    $("pr-counter").textContent = parts.join(" · ");
  }

  function onPairOption(e) {
    var btn = e.target.closest(".opt");
    if (!btn || !btn.dataset.kind) return;
    if (xState === "done" || btn.closest("#pr-answer")) return;
    xPicked[btn.dataset.kind] = btn.dataset.val;
    Array.prototype.forEach.call(btn.parentNode.querySelectorAll(".opt"), function (o) {
      o.classList.toggle("picked", o === btn);
    });
  }

  function markRow(rowId, correct) {
    Array.prototype.forEach.call($(rowId).querySelectorAll(".opt"), function (o) {
      o.classList.remove("ok", "bad");
      if (o.dataset.val === correct) o.classList.add("ok");
      else if (o.classList.contains("picked")) o.classList.add("bad");
    });
  }

  function markPair(p) {
    markRow("pr-gender", p.gender);
    markRow("pr-form", p.form);
    markRow("pr-ru", p.ru);
  }

  function checkPair() {
    var p = xPool[xIndex];
    if (!p || xState === "done") return;
    if (xPicked.gender == null || xPicked.form == null || xPicked.ru == null) {
      $("pr-feedback").textContent = "Нужно ответить на все три пункта";
      $("pr-feedback").className = "feedback neutral";
      return;
    }
    var ok = xPicked.gender === p.gender && xPicked.form === p.form && xPicked.ru === p.ru;
    markPair(p);
    finishPair(p, ok);
  }

  function revealPair() {
    var p = xPool[xIndex];
    if (!p || xState === "done") return;
    markPair(p);
    finishPair(p, false);
  }

  function finishPair(p, ok) {
    xState = "done";
    grade(pid(p), "pair", ok);
    $("pr-check").hidden = true;
    $("pr-reveal").hidden = true;
    $("pr-next").hidden = false;

    var wrong = [];
    if (xPicked.gender !== p.gender) wrong.push("род");
    if (xPicked.form !== p.form) wrong.push("форма");
    if (xPicked.ru !== p.ru) wrong.push("перевод");
    $("pr-feedback").textContent = ok
      ? "Верно!"
      : (wrong.length === 3 ? "Разбор ниже" : "Неверно: " + wrong.join(", "));
    $("pr-feedback").className = "feedback " + (ok ? "good" : "bad");

    $("pr-answer").innerHTML =
      '<div class="pair-answer">' + escapeHtml(p.phrase) + "</div>" +
      '<div class="pair-answer-ru">' + escapeHtml(p.ru) + "</div>" +
      '<div class="pair-answer-ru">' + escapeHtml(p.subject) + " — " +
      escapeHtml(p.nounRu) + " · " + escapeHtml(p.verbMt) + " — " +
      escapeHtml(p.verbRu) + "</div>";
    $("pr-answer").hidden = false;
    renderTranslit($("pr-translit"), p.phrase);

    if (ok) {
      window.setTimeout(function () {
        if (xState === "done" && xPool[xIndex] === p) nextPair();
      }, 900);
    }
  }

  function nextPair() {
    xIndex++;
    if (xIndex < xPool.length) { showPair(); return; }
    xBypass = false;
    buildPairPool();
  }

  /* ---------- alphabet ---------- */

  var ALPHABET = [
    ["A a", "[а]", "mama' — мама"],
    ["B b", "[б]", "ballun — мяч"],
    ["Ċ ċ", "[ч]", "ċikkulata — шоколад"],
    ["D d", "[д]", "dar — дом"],
    ["E e", "[э]", "erbgħa — четыре"],
    ["F f", "[ф]", "fjura — цветок"],
    ["Ġ ġ", "[дж]", "ġobon — сыр"],
    ["G g", "[г]", "gżira — остров"],
    ["Għ għ", "часто немой, удлиняет гласную", "għajn — глаз"],
    ["H h", "немой", "hi — она"],
    ["Ħ ħ", "[хь], гортанный", "ħobż — хлеб"],
    ["I i", "[и]", "ilma — вода"],
    ["Ie ie", "[ие], один звук", "iebes — жёсткий"],
    ["J j", "[й]", "jum — день"],
    ["K k", "[к]", "kelb — собака"],
    ["L l", "[л]", "lejl — ночь"],
    ["M m", "[м]", "mara — женщина"],
    ["N n", "[н]", "nadif — чистый"],
    ["O o", "[о]", "ors — медведь"],
    ["P p", "[п]", "paċi — мир"],
    ["Q q", "[къ], гортанная смычка", "qalb — сердце"],
    ["R r", "[р]", "ras — голова"],
    ["S s", "[с]", "siġra — дерево"],
    ["T t", "[т]", "tieqa — окно"],
    ["U u", "[у]", "ukoll — тоже"],
    ["V v", "[в]", "vapur — корабль"],
    ["W w", "[у], краткая", "warda — роза"],
    ["X x", "[ш]", "xemx — солнце"],
    ["Ż ż", "[з]", "żmien — время"],
    ["Z z", "[ц]", "zalzett — колбаса"]
  ];

  function initAlphabet() {
    var grid = $("alpha-grid");
    grid.innerHTML = ALPHABET.map(function (row) {
      return '<button class="alpha-cell" type="button" data-say="' + escapeHtml(row[2].split(" — ")[0]) + '">' +
        '<span class="alpha-letter">' + escapeHtml(row[0]) + "</span>" +
        '<span class="alpha-sound">' + escapeHtml(row[1]) + "</span>" +
        '<span class="alpha-ex">' + escapeHtml(row[2]) + "</span>" +
        "</button>";
    }).join("");
    grid.addEventListener("click", function (e) {
      var b = e.target.closest(".alpha-cell");
      if (!b) return;
      speak(b.dataset.say);
    });
    renderSpecialKeys($("copy-kbd"), function (ch) { copyText(ch); });
  }

  function copyText(t) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(t).then(function () { toast("Скопировано: " + t); },
        function () { toast("Не удалось скопировать"); });
    } else {
      toast("Символ: " + t);
    }
  }

  /* ---------- progress ---------- */

  function renderProgress() {
    var boxLabels = ["Не начатые", "Коробка 1", "Коробка 2", "Коробка 3", "Коробка 4", "Коробка 5+"];
    var boxes = [0, 0, 0, 0, 0, 0];
    var dueReviews = 0;
    var untouched = 0;
    WORDS.forEach(function (w) {
      var r = state.items[wid(w)];
      boxes[r ? r.b : 0]++;
      if (!r) untouched++;
      else if (r.d <= dayNumber()) dueReviews++;
    });
    var learned = boxes[4] + boxes[5];
    var started = WORDS.length - untouched;
    var w = state.stats.word, s = state.stats.sent;
    var totalOk = w.ok + s.ok;
    var totalNo = w.no + s.no;
    var acc = (totalOk + totalNo) ? Math.round((totalOk / (totalOk + totalNo)) * 100) : 0;
    var limit = newLimit();
    var today = introducedToday();

    var cards = [
      ["Новых сегодня", today + (limit ? " из " + limit : " (без лимита)")],
      ["К повторению сейчас", String(dueReviews)],
      ["Слов начато", started + " из " + WORDS.length],
      ["Освоено (коробки 4–5)", String(learned)],
      ["Всего ответов", String(totalOk + totalNo)],
      ["Точность", acc + "%"],
      ["Сочетаний", String(PAIRS.length)],
      ["Новых сочетаний сегодня", introducedPairsToday() + (pairLimit() ? " из " + pairLimit() : "")]
    ];
    $("p-stats").innerHTML = cards.map(function (c) {
      return '<div class="stat"><div class="stat-value">' + escapeHtml(c[1]) +
        '</div><div class="stat-label">' + escapeHtml(c[0]) + "</div></div>";
    }).join("");

    var maxBox = Math.max.apply(null, boxes.concat([1]));
    $("p-boxes").innerHTML = boxLabels.map(function (label, i) {
      var pct = Math.round((boxes[i] / maxBox) * 100);
      return '<div class="box-row"><div class="box-label">' + escapeHtml(label) +
        '</div><div class="box-track"><div class="box-fill" style="width:' + pct + '%"></div></div>' +
        '<div class="box-count">' + boxes[i] + "</div></div>";
    }).join("");

    var days = [];
    for (var i = 6; i >= 0; i--) {
      var d = new Date();
      d.setDate(d.getDate() - i);
      var key = dateKey(d);
      days.push({ key: key, label: key.slice(5), count: state.days[key] || 0 });
    }
    var maxDay = Math.max.apply(null, days.map(function (x) { return x.count; }).concat([1]));
    $("p-days").innerHTML = days.map(function (x) {
      var pct = Math.round((x.count / maxDay) * 100);
      return '<div class="box-row"><div class="box-label">' + escapeHtml(x.label) +
        '</div><div class="box-track"><div class="box-fill day" style="width:' + pct + '%"></div></div>' +
        '<div class="box-count">' + x.count + "</div></div>";
    }).join("");
  }

  function initProgress() {
    $("p-reset").addEventListener("click", function () {
      if (!window.confirm("Сбросить весь прогресс?")) return;
      state = freshState();
      saveState();
      buildWordQueue();
      renderProgress();
      toast("Прогресс сброшен");
    });
  }

  /* ---------- keyboard shortcuts ---------- */

  function initKeys() {
    document.addEventListener("keydown", function (e) {
      var tag = (e.target.tagName || "").toLowerCase();
      var typing = tag === "input" || tag === "textarea" || tag === "select";
      if ($("view-words").hidden === false && !typing) {
        if (e.key === " " || e.key === "Enter") {
          e.preventDefault();
          if (wRevealed) answerWord(true); else revealWord();
        } else if (wRevealed && (e.key === "1" || e.key === "x")) {
          answerWord(false);
        } else if (wRevealed && (e.key === "2" || e.key === "z")) {
          answerWord(true);
        }
      }
    });
  }

  /* ---------- init ---------- */

  function init() {
    loadState();
    pickVoice();
    if ("speechSynthesis" in window) window.speechSynthesis.onvoiceschanged = pickVoice;
    // Секции инициализируются до initTabs: selectTab рендерит активную
    // вкладку, и очередь слов должна быть уже построена.
    initWords();
    initSentences();
    initPairs();
    initAlphabet();
    initProgress();
    initKeys();
    initTabs();
    $("s-chips").addEventListener("click", onChipClick);
    $("s-answer").addEventListener("click", onChipClick);
    $("s-input").addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); checkSentence(); }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
