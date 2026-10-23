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
    prep: "Предлоги",
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

  // Единственный источник правды для счётчиков ответов.
  // Раньше список дублировался в трёх местах и разъезжался.
  var STAT_KINDS = ["word", "sent", "pair", "form"];

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
    var stats = {};
    STAT_KINDS.forEach(function (k) { stats[k] = { ok: 0, no: 0 }; });
    return { items: {}, stats: stats, days: {} };
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
        STAT_KINDS.forEach(function (k) {
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
    if (name === "forms") fmShow();
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
  var sTokens = [], sAnswer = [], sRevealed = false, sDone = false;
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
    $("s-choice-list").addEventListener("click", onChoiceClick);
    $("s-next").addEventListener("click", nextSentence);
    $("s-check").addEventListener("click", checkSentence);
    $("s-reveal").addEventListener("click", revealSentence);
    $("s-again").addEventListener("click", showSentence);
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
    sRevealed = false;
    sDone = false;

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
    $("s-diff").hidden = true;
    $("s-diff").innerHTML = "";
    $("s-feedback").textContent = "";
    $("s-feedback").className = "feedback";
    $("s-reveal").hidden = false;
    $("s-grade").hidden = true;
    renderTranslit($("s-translit"), "");

    var isBuild = sMode === "build";
    var isChoice = sMode === "choice";
    var isCard = sMode === "card";

    $("s-build").hidden = !isBuild;
    $("s-choice").hidden = !isChoice;
    $("s-cardbox").hidden = !isCard;
    $("s-check").hidden = !isBuild;
    $("s-reveal").textContent = isBuild ? "Подсказка (показать ответ)" : "Показать ответ";

    if (isBuild) {
      sTokens = tokenize(s.mt);
      sAnswer = [];
      renderBuild();
    } else if (isChoice) {
      renderChoice(s);
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

  // Режим «Выбор перевода»: русская фраза дана, надо узнать мальтийскую.
  // Дистракторы берём из той же темы и близкой длины, чтобы не угадывать.
  function choiceOptions(s) {
    var mine = s.mt.split(" ").length;
    var rest = SENTENCES.filter(function (x) { return x.mt !== s.mt; });
    rest.sort(function (a, b) {
      var ta = a.topic === s.topic ? 0 : 1;
      var tb = b.topic === s.topic ? 0 : 1;
      if (ta !== tb) return ta - tb;
      return Math.abs(a.mt.split(" ").length - mine) -
             Math.abs(b.mt.split(" ").length - mine);
    });
    return shuffle([s].concat(rest.slice(0, 2)));
  }

  function renderChoice(s) {
    $("s-choice-list").innerHTML = choiceOptions(s).map(function (o) {
      return '<button class="opt-sentence" data-mt="' + escapeHtml(o.mt) + '">' +
        escapeHtml(o.mt) + "</button>";
    }).join("");
  }

  function onChoiceClick(e) {
    var btn = e.target.closest(".opt-sentence");
    if (!btn || sMode !== "choice" || sDone) return;
    var s = sPool[sIndex];
    if (!s) return;
    var picked = btn.dataset.mt;
    var ok = picked === s.mt;
    Array.prototype.forEach.call($("s-choice-list").querySelectorAll(".opt-sentence"), function (o) {
      o.classList.remove("picked", "ok", "bad");
      if (o.dataset.mt === s.mt) o.classList.add("ok");
      else if (o.dataset.mt === picked) o.classList.add("bad");
    });
    finishSentence(s, ok);
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

  // Общее завершение: показать разбор, засчитать ответ, при верном — уйти дальше.
  function finishSentence(s, ok) {
    sDone = true;
    feedback(ok, s);
    renderTranslit($("s-translit"), s.mt);
    $("s-known").innerHTML = renderNewWords(unfamiliarOf(s), true);
    $("s-reveal").hidden = true;
    $("s-check").hidden = true;
    grade(sid(s), "sent", ok);
    if (ok) {
      window.setTimeout(function () { if (sPool[sIndex] === s) nextSentence(); }, 900);
    }
  }

  function checkSentence() {
    var s = sPool[sIndex];
    if (!s || sDone) return;
    var user = sAnswer.map(function (i) { return sTokens[i].clean; }).join(" ");
    var ok = norm(user) === norm(s.mt);
    if (!ok) renderDiff(user, s);
    finishSentence(s, ok);
  }

  function revealSentence() {
    var s = sPool[sIndex];
    if (!s || sRevealed || sDone) return;
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
    } else if (sMode === "choice") {
      Array.prototype.forEach.call($("s-choice-list").querySelectorAll(".opt-sentence"), function (o) {
        o.classList.remove("bad");
        o.classList.toggle("ok", o.dataset.mt === s.mt);
      });
    } else {
      $("s-mt").textContent = s.mt;
    }
    feedback(true, s, true);
    renderTranslit($("s-translit"), s.mt);
    $("s-known").innerHTML = renderNewWords(unfamiliarOf(s), true);
    if (sMode === "card") $("s-grade").hidden = false;
  }

  // Сравниваем ответ по словам: показываем, что именно разошлось.
  function renderDiff(user, s) {
    var u = tokenize(String(user || ""));
    var c = tokenize(s.mt);
    var n = Math.max(u.length, c.length);
    var rows = [];
    var bad = 0;
    for (var i = 0; i < n; i++) {
      var ut = u[i] ? u[i].clean : null;
      var ct = c[i] ? c[i].clean : null;
      var same = ut !== null && ct !== null && norm(ut) === norm(ct);
      if (!same) bad++;
      rows.push({
        mine: u[i] ? u[i].raw : "…",
        right: c[i] ? c[i].raw : "…",
        same: same
      });
    }
    var box = $("s-diff");
    if (!bad) { box.hidden = true; box.innerHTML = ""; return; }
    function line(tag, field) {
      return '<div class="diff-row"><span class="diff-tag">' + tag + "</span>" +
        rows.map(function (r) {
          return '<span class="' + (r.same ? "dt-ok" : "dt-bad") + '">' +
            escapeHtml(r[field]) + "</span>";
        }).join(" ") + "</div>";
    }
    box.innerHTML = line("твой ответ", "mine") + line("правильно", "right") +
      '<div class="diff-note">Расхождений: ' + bad + "</div>";
    box.hidden = false;
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
    if (!s || sDone) return;
    // finishSentence сам уходит дальше при верном ответе;
    // при неверном ждём, пока пользователь нажмёт «Другое предложение».
    finishSentence(s, ok);
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

  /* ---------- формы: 4 режима (сочетание / согласование / мн.ч. / предлоги) ---------- */

  var PAIRS = window.PAIRS || [];
  var FORMS = window.FORMS || { agreement: [], plural: [], prep: [] };
  var DEFAULT_FM_LIMIT = 10;

  var GENDER_CHOICES = [
    { value: "m", label: "м. род" },
    { value: "f", label: "ж. род" },
    { value: "pl", label: "мн. ч." }
  ];
  var GENDER_LABEL = { m: "м. род", f: "ж. род", pl: "мн. ч." };

  var FM_MODES = {
    pair: {
      label: "Существительное + глагол",
      prefix: "p:",
      kind: "pair",
      source: function () { return PAIRS; },
      key: function (it) { return it.phrase; }
    },
    agree: {
      label: "Согласование: сущ + прил + глаг",
      prefix: "fa:",
      kind: "form",
      source: function () { return FORMS.agreement || []; },
      key: function (it) { return it.phrase; }
    },
    plural: {
      label: "Множественное число",
      prefix: "fp:",
      kind: "form",
      source: function () { return FORMS.plural || []; },
      key: function (it) { return it.noun; }
    },
    prep: {
      label: "Предлоги и слитные формы",
      prefix: "fr:",
      kind: "form",
      source: function () { return FORMS.prep || []; },
      key: function (it) { return it.prep + "|" + it.subject; }
    }
  };

  var fmList = [], fmPool = [], fmIndex = 0, fmPicked = {}, fmState = "ask", fmBypass = false;
  var fmReviewAll = false;

  function fmMode() { return $("fm-mode").value; }

  function fmCurrentList() { return FM_MODES[fmMode()].list || []; }

  function fmUid(mode, it) { return FM_MODES[mode].prefix + FM_MODES[mode].key(it); }

  function fmLimit() {
    return state.fmLimit === undefined ? DEFAULT_FM_LIMIT : state.fmLimit;
  }

  function fmIntroduced(mode) { return countIntroduced(FM_MODES[mode].prefix); }

  function fmRemaining(mode) {
    var limit = fmLimit();
    if (!limit) return Infinity;
    return Math.max(0, limit - fmIntroduced(mode));
  }

  function fmInit() {
    // уникальный id каждому пункту, чтобы SRS не путался
    Object.keys(FM_MODES).forEach(function (k) {
      var m = FM_MODES[k];
      m.list = m.source().map(function (it) {
        return { data: it, uid: m.prefix + m.key(it) };
      });
    });
    Object.keys(FM_MODES).forEach(function (k) {
      var o = document.createElement("option");
      o.value = k;
      o.textContent = FM_MODES[k].label;
      $("fm-mode").appendChild(o);
    });
    $("fm-limit").value = String(fmLimit());
    $("fm-mode").addEventListener("change", function () {
      fmBypass = false;
      fmBuild();
    });
    $("fm-limit").addEventListener("change", function (e) {
      state.fmLimit = Number(e.target.value);
      saveState();
      fmBypass = false;
      fmBuild();
    });
    $("fm-shuffle").addEventListener("click", function () { shuffle(fmPool); fmIndex = 0; fmShow(); });
    $("fm-check").addEventListener("click", fmCheck);
    $("fm-reveal").addEventListener("click", fmReveal);
    $("fm-next").addEventListener("click", fmNext);
    $("fm-bypass").addEventListener("click", function () { fmBypass = true; fmBuild(); });
    $("fm-review-all").addEventListener("click", function () { fmReviewAll = true; fmBuild(); });
    $("fm-quiz").addEventListener("click", fmPick);
    fmBuild();
  }

  function fmBuild() {
    var mode = fmMode();
    var all = fmCurrentList();
    fmIndex = 0;

    if (fmReviewAll) {
      fmPool = shuffle(all.slice());
      fmShow();
      return;
    }

    var reviews = all.filter(function (x) {
      var r = state.items[x.uid];
      return !!r && r.d <= dayNumber();
    }).sort(function (a, b) {
      return state.items[a.uid].d - state.items[b.uid].d;
    });

    var news = shuffle(all.filter(function (x) { return !state.items[x.uid]; }));
    var allowed = fmBypass ? news.length : fmRemaining(mode);
    if (allowed !== Infinity) news = news.slice(0, allowed);

    fmPool = reviews.concat(news);
    fmShow();
  }

  function fmPrompt(mode, it) {
    function part(text) { return '<span class="pair-part">' + escapeHtml(text) + "</span>"; }
    if (mode === "pair" || mode === "agree") {
      var parts = [part(it.subject), part(it.adj), part(it.verbMt || it.verb)];
      if (mode === "pair") parts = [part(it.subject), part(it.verbMt)];
      return parts.join('<span class="pair-plus">+</span>');
    }
    if (mode === "plural") {
      return part(it.noun) + '<span class="pair-plus">→ мн. ч.</span>';
    }
    return part(it.prep) + '<span class="pair-plus">+</span>' + part(it.subject);
  }

  function fmRows(mode, it) {
    var rows = [];
    function vals(arr) {
      return arr.map(function (v) { return { value: v, label: v }; });
    }
    function distractors(correct, source, n, field) {
      var out = [];
      shuffle(source.slice()).forEach(function (x) {
        var v = x[field || "ru"] || x.meaning;
        if (v && v !== correct && out.indexOf(v) === -1 && out.length < n) out.push(v);
      });
      return out;
    }

    if (mode === "pair") {
      rows.push({ key: "gender", label: "1. Род существительного", options: GENDER_CHOICES, correct: it.gender });
      rows.push({ key: "form", label: "2. Форма глагола (настоящее время)", options: vals(it.forms), correct: it.form });
      rows.push({ key: "ru", label: "3. Перевод сочетания",
                  options: vals([it.ru].concat(distractors(it.ru, FM_MODES.pair.list.map(function (x) { return x.data; }), 2))),
                  correct: it.ru });
    } else if (mode === "agree") {
      var others = FM_MODES.agree.list.map(function (x) { return x.data; });
      rows.push({ key: "gender", label: "1. Род существительного", options: GENDER_CHOICES, correct: it.gender });
      rows.push({ key: "adjForm", label: "2. Форма прилагательного", options: vals(it.adjOptions), correct: it.adjForm });
      rows.push({ key: "verbForm", label: "3. Форма глагола (" + escapeHtml(it.verb) + ")", options: vals(it.verbOptions), correct: it.verbForm });
      rows.push({ key: "ru", label: "4. Перевод фразы",
                  options: vals([it.ru].concat(distractors(it.ru, others, 2))), correct: it.ru });
    } else if (mode === "plural") {
      var nouns = FM_MODES.plural.list.map(function (x) { return x.data; });
      rows.push({ key: "plural", label: "1. Множественное число", options: vals(it.pluralOptions), correct: it.plural });
      rows.push({ key: "definite", label: "2. Множественное число с артиклем", options: vals(it.definiteOptions), correct: it.definite });
      if (it.ruPl) {
        rows.push({ key: "ruPl", label: "3. Перевод (множественное число)",
                    options: vals(shuffle([it.ruPl].concat(distractors(it.ruPl, nouns, 2, "ruPl")))),
                    correct: it.ruPl });
      }
    } else {
      var preps = FM_MODES.prep.list.map(function (x) { return x.data; });
      var meanings = [];
      preps.forEach(function (p) { if (meanings.indexOf(p.meaning) === -1) meanings.push(p.meaning); });
      var mopts = [it.meaning].concat(shuffle(meanings.filter(function (m) { return m !== it.meaning; })).slice(0, 2));
      rows.push({ key: "fused", label: "1. Слитная форма", options: vals(it.options), correct: it.fused });
      rows.push({ key: "meaning", label: "2. Значение предлога", options: vals(shuffle(mopts)), correct: it.meaning });
      rows.push({ key: "nounRu", label: "3. Перевод существительного",
                  options: vals(shuffle([it.nounRu].concat(distractors(it.nounRu, preps, 2, "nounRu")))),
                  correct: it.nounRu });
    }
    return rows;
  }

  function fmShow() {
    var wrapper = fmPool[fmIndex];
    var mode = fmMode();
    var card = $("fm-card");

    if (!wrapper) {
      card.hidden = true;
      $("fm-quiz").hidden = true;
      $("fm-actions").hidden = true;
      $("fm-done").hidden = false;
      var limit = fmLimit();
      var total = fmCurrentList().length;
      var done = fmIntroduced(mode);
      $("fm-done-text").textContent = limit
        ? "В этом режиме новых сегодня: " + done + " из " + limit +
          ". Всего упражнений: " + total + ". Следующее повторение: " + nextDueDate(FM_MODES[mode].prefix) + "."
        : "Всего упражнений: " + total + ". Следующее повторение: " + nextDueDate(FM_MODES[mode].prefix) + ".";
      $("fm-counter").textContent = "";
      fmBypass = false;
      return;
    }

    var it = wrapper.data;
    card.hidden = false;
    $("fm-done").hidden = true;
    $("fm-quiz").hidden = false;
    $("fm-actions").hidden = false;
    fmState = "ask";
    fmPicked = {};

    $("fm-prompt").innerHTML = fmPrompt(mode, it);

    var rows = fmRows(mode, it);
    $("fm-quiz").innerHTML = rows.map(function (row) {
      return '<div class="quiz-row"><div class="quiz-label">' + row.label + "</div>" +
        '<div class="quiz-options" data-key="' + row.key + '">' +
        row.options.map(function (o) {
          return '<button class="opt" data-value="' + escapeHtml(o.value) + '">' +
            escapeHtml(o.label) + "</button>";
        }).join("") + "</div></div>";
    }).join("");
    $("fm-correct").value = JSON.stringify(rows.map(function (r) {
      return { key: r.key, correct: r.correct };
    }));

    $("fm-feedback").textContent = "";
    $("fm-feedback").className = "feedback";
    $("fm-answer").hidden = true;
    $("fm-answer").innerHTML = "";
    renderTranslit($("fm-translit"), "");
    $("fm-check").hidden = false;
    $("fm-reveal").hidden = false;
    $("fm-next").hidden = true;

    var parts = ["Упражнение " + (fmIndex + 1) + " из " + fmPool.length];
    if (fmLimit()) parts.push("новых сегодня: " + fmIntroduced(mode) + "/" + fmLimit());
    if (fmBypass) parts.push("сверх лимита");
    $("fm-counter").textContent = parts.join(" · ");
  }

  function fmPick(e) {
    var btn = e.target.closest(".opt");
    if (!btn || fmState === "done") return;
    var row = btn.parentNode;
    fmPicked[row.dataset.key] = btn.dataset.value;
    Array.prototype.forEach.call(row.querySelectorAll(".opt"), function (o) {
      o.classList.toggle("picked", o === btn);
    });
  }

  function fmCorrectRows() {
    try { return JSON.parse($("fm-correct").value); } catch (e) { return []; }
  }

  function fmMark() {
    var rows = fmCorrectRows();
    Array.prototype.forEach.call($("fm-quiz").querySelectorAll(".quiz-options"), function (box) {
      var key = box.dataset.key;
      var row = rows.filter(function (r) { return r.key === key; })[0];
      if (!row) return;
      Array.prototype.forEach.call(box.querySelectorAll(".opt"), function (o) {
        o.classList.remove("ok", "bad");
        if (o.dataset.value === row.correct) o.classList.add("ok");
        else if (o.classList.contains("picked")) o.classList.add("bad");
      });
    });
  }

  function fmCheck() {
    if (fmState === "done") return;
    var rows = fmCorrectRows();
    var missing = rows.filter(function (r) { return fmPicked[r.key] == null; });
    if (missing.length) {
      $("fm-feedback").textContent = "Ответь на все пункты (" + rows.length + ")";
      $("fm-feedback").className = "feedback neutral";
      return;
    }
    var wrong = rows.filter(function (r) { return fmPicked[r.key] !== r.correct; });
    fmMark();
    fmFinish(wrong);
  }

  function fmReveal() {
    if (fmState === "done") return;
    fmMark();
    fmFinish(null, true);
  }

  function fmFinish(wrong, revealed) {
    var wrapper = fmPool[fmIndex];
    var mode = fmMode();
    var it = wrapper.data;
    fmState = "done";
    var ok = !revealed && wrong.length === 0;
    grade(wrapper.uid, FM_MODES[mode].kind, ok);

    $("fm-check").hidden = true;
    $("fm-reveal").hidden = true;
    $("fm-next").hidden = false;

    var labels = { gender: "род", adjForm: "форма прилагательного", verbForm: "форма глагола",
                   form: "форма глагола", ru: "перевод", plural: "мн. число",
                   definite: "артикль", ruPl: "перевод", fused: "слитная форма",
                   meaning: "значение", nounRu: "перевод" };
    $("fm-feedback").textContent = ok ? "Верно!"
      : (revealed ? "Разбор" : "Неверно: " + wrong.map(function (r) { return labels[r.key] || r.key; }).join(", "));
    $("fm-feedback").className = "feedback " + (ok ? "good" : "bad");

    $("fm-answer").innerHTML = fmAnswer(mode, it);
    $("fm-answer").hidden = false;
    renderTranslit($("fm-translit"), mode === "agree" || mode === "pair" ? it.phrase : "");

    if (ok) {
      window.setTimeout(function () {
        if (fmState === "done" && fmPool[fmIndex] === wrapper) fmNext();
      }, 900);
    }
  }

  function fmAnswer(mode, it) {
    if (mode === "pair") {
      return '<div class="pair-answer">' + escapeHtml(it.phrase) + "</div>" +
        '<div class="pair-answer-ru">' + escapeHtml(it.ru) + "</div>" +
        '<div class="pair-answer-ru">' + escapeHtml(it.subject) + " — " + escapeHtml(it.nounRu) +
        " · " + escapeHtml(it.verbMt) + " — " + escapeHtml(it.verbRu) + "</div>";
    }
    if (mode === "agree") {
      return '<div class="pair-answer">' + escapeHtml(it.phrase) + "</div>" +
        '<div class="pair-answer-ru">' + escapeHtml(it.ru) + "</div>" +
        '<div class="pair-answer-ru">' + escapeHtml(it.subject) + " — " + GENDER_LABEL[it.gender] +
        " · прилаг. " + escapeHtml(it.adjForm) + " · глаг. " + escapeHtml(it.verbForm) + "</div>";
    }
    if (mode === "plural") {
      return '<div class="pair-answer">' + escapeHtml(it.noun) + " → " + escapeHtml(it.definite) + "</div>" +
        '<div class="pair-answer-ru">' + escapeHtml(it.nounRu) +
        (it.ruPl ? " → " + escapeHtml(it.ruPl) : "") + " (" + GENDER_LABEL[it.gender] +
        ") · мн. ч. " + escapeHtml(it.plural) + "</div>";
    }
    return '<div class="pair-answer">' + escapeHtml(it.prep) + " + " + escapeHtml(it.subject) +
      " → " + escapeHtml(it.fused) + "</div>" +
      '<div class="pair-answer-ru">' + escapeHtml(it.nounRu) + " · " + escapeHtml(it.meaning) + "</div>";
  }

  function fmNext() {
    fmIndex++;
    if (fmIndex < fmPool.length) { fmShow(); return; }
    if (fmReviewAll) { fmPool = []; fmIndex = 0; fmShow(); fmReviewAll = false; return; }
    fmBypass = false;
    fmBuild();
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
      return '<button class="alpha-cell" type="button">' +
        '<span class="alpha-letter">' + escapeHtml(row[0]) + "</span>" +
        '<span class="alpha-sound">' + escapeHtml(row[1]) + "</span>" +
        '<span class="alpha-ex">' + escapeHtml(row[2]) + "</span>" +
        "</button>";
    }).join("");
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

  var KIND_LABEL = { word: "Слова", sent: "Предложения", pair: "Существительное + глагол",
                     form: "Согласование, множественное, предлоги" };

  // Сводка по любой коллекции: сколько начато, освоено и ждёт повторения.
  function srsSummary(prefix, uids) {
    var started = 0, learned = 0, due = 0, untouched = 0;
    uids.forEach(function (uid) {
      var r = state.items[uid];
      if (!r) { untouched++; return; }
      started++;
      if (r.b >= 4) learned++;
      if (r.d <= dayNumber()) due++;
    });
    return { total: uids.length, started: started, learned: learned, due: due,
             untouched: untouched, next: nextDueDate(prefix) };
  }

  function allSummaries() {
    var out = [];
    out.push({ name: "Слова", s: srsSummary("w:", WORDS.map(wid)) });
    out.push({ name: "Предложения", s: srsSummary("s:", SENTENCES.map(sid)) });
    Object.keys(FM_MODES).forEach(function (k) {
      var m = FM_MODES[k];
      out.push({ name: m.label, s: srsSummary(m.prefix, m.list.map(function (x) { return x.uid; })) });
    });
    return out;
  }

  function renderProgress() {
    var notStarted = 0, forgotten = 0, dueReviews = 0;
    var boxes = [0, 0, 0, 0, 0, 0];          // коробки 0..5 среди начатых слов
    WORDS.forEach(function (w) {
      var r = state.items[wid(w)];
      if (!r) { notStarted++; return; }
      boxes[r.b]++;
      if (r.b === 0) forgotten++;
      if (r.d <= dayNumber()) dueReviews++;
    });
    var learned = boxes[4] + boxes[5];
    var started = WORDS.length - notStarted;

    // Ответы и точность по ВСЕМ режимам, а не только по словам.
    var ok = 0, no = 0;
    STAT_KINDS.forEach(function (k) {
      ok += state.stats[k].ok;
      no += state.stats[k].no;
    });
    var acc = (ok + no) ? Math.round((ok / (ok + no)) * 100) : 0;

    var limit = newLimit();
    var cards = [
      ["Новых слов сегодня", introducedToday() + (limit ? " из " + limit : " (без лимита)")],
      ["Слов к повторению сейчас", String(dueReviews)],
      ["Слов начато", started + " из " + WORDS.length],
      ["Освоено (коробки 4–5)", String(learned)],
      ["Всего ответов", String(ok + no)],
      ["Точность", acc + "%"]
    ];
    $("p-stats").innerHTML = cards.map(function (c) {
      return '<div class="stat"><div class="stat-value">' + escapeHtml(c[1]) +
        '</div><div class="stat-label">' + escapeHtml(c[0]) + "</div></div>";
    }).join("");

    // Гистограмма: не начатые, «забытые» (коробка 0) и коробки 1–5.
    var rows = [
      ["Не начатые", notStarted],
      ["Коробка 0 (проваленные)", forgotten],
      ["Коробка 1", boxes[1]],
      ["Коробка 2", boxes[2]],
      ["Коробка 3", boxes[3]],
      ["Коробка 4", boxes[4]],
      ["Коробка 5+", boxes[5]]
    ];
    var maxRow = Math.max.apply(null, rows.map(function (r) { return r[1]; }).concat([1]));
    $("p-boxes").innerHTML = rows.map(function (r) {
      var pct = Math.round((r[1] / maxRow) * 100);
      return '<div class="box-row"><div class="box-label">' + escapeHtml(r[0]) +
        '</div><div class="box-track"><div class="box-fill" style="width:' + pct + '%"></div></div>' +
        '<div class="box-count">' + r[1] + "</div></div>";
    }).join("");

    // Прогресс по каждому набору упражнений: раньше был виден только по словам.
    $("p-sets").innerHTML = allSummaries().map(function (row) {
      var s = row.s;
      return '<div class="set-row"><div class="set-name">' + escapeHtml(row.name) + "</div>" +
        '<div class="set-num">начато: <b>' + s.started + "</b> из " + s.total + "</div>" +
        '<div class="set-num">освоено: <b>' + s.learned + "</b></div>" +
        '<div class="set-num">к повторению: <b>' + s.due + "</b></div>" +
        '<div class="set-num set-next">далее: ' + escapeHtml(s.next) + "</div></div>";
    }).join("");

    // Сколько ответов дано по каждому режиму.
    $("p-kinds").innerHTML = STAT_KINDS.map(function (k) {
      var st = state.stats[k];
      var total = st.ok + st.no;
      var a = total ? Math.round((st.ok / total) * 100) : 0;
      return '<div class="set-row"><div class="set-name">' + escapeHtml(KIND_LABEL[k]) + "</div>" +
        '<div class="set-num">ответов: <b>' + total + "</b></div>" +
        '<div class="set-num">верно: <b>' + st.ok + "</b></div>" +
        '<div class="set-num">ошибок: <b>' + st.no + "</b></div>" +
        '<div class="set-num set-next">точность: ' + a + "%</div></div>";
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
    // Секции инициализируются до initTabs: selectTab рендерит активную
    // вкладку, и очередь слов должна быть уже построена.
    initWords();
    initSentences();
    fmInit();
    initAlphabet();
    initProgress();
    initKeys();
    initTabs();
    $("s-chips").addEventListener("click", onChipClick);
    $("s-answer").addEventListener("click", onChipClick);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
