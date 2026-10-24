"""Headless smoke test for the Il-Malti app.

Starts a local static server, drives the app with Playwright (Chromium, headless)
and asserts that all four screens work and no console errors appear.

Usage:
    python3 tests/smoke.py
    python3 tests/smoke.py --root dist    # check a built bundle

Requires: `playwright` python package with Chromium installed
    pip install playwright && playwright install chromium
"""

import functools
import http.server
import json
import os
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# --root DIR serves another directory (e.g. the built dist/ bundle)
if "--root" in sys.argv:
    ROOT = os.path.abspath(sys.argv[sys.argv.index("--root") + 1])
LIVE_URL = sys.argv[sys.argv.index("--url") + 1] if "--url" in sys.argv else None

failures = []


def check(label, actual, expected=None, predicate=None):
    if predicate is not None:
        ok = predicate(actual)
    else:
        ok = actual == expected
    mark = "ok  " if ok else "FAIL"
    print("[%s] %s: %r" % (mark, label, actual))
    if not ok:
        failures.append("%s -> %r (expected %r)" % (label, actual, expected))


def start_server():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)

    class Quiet(socketserver.TCPServer):
        allow_reuse_address = True

    httpd = Quiet(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


def main():
    httpd = None
    if LIVE_URL:
        url = LIVE_URL
    else:
        httpd, port = start_server()
        url = "http://127.0.0.1:%d/index.html" % port
    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 900, "height": 800})
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append("PAGEERROR: %s" % e))
        page.goto(url, wait_until="load")

        check("title", page.title(), predicate=lambda t: "Malti" in t)

        # --- words ---
        check("words topic options", page.locator("#w-topic option").count(), 18)
        check("default new-words-per-day limit", page.input_value("#w-limit"), "10")
        check("first queue is capped by the daily limit", page.inner_text("#w-counter"),
              predicate=lambda s: "В очереди: 10" in s and "новых сегодня: 0/10" in s)
        page.click("#w-show")
        back = page.inner_text("#w-back")
        check("reveal shows translation", back, predicate=lambda s: len(s.strip()) > 0)
        check("grade buttons appear", page.locator("#w-grade").is_hidden(), False)
        page.click("#w-yes")
        check("queue shrinks and new counter grows", page.inner_text("#w-counter"),
              predicate=lambda s: "В очереди: 9" in s and "1/10" in s)
        stored = page.evaluate("() => localStorage.getItem('il-malti-v1')")
        check("progress persisted", stored, predicate=lambda s: s and "items" in s)
        check("record keeps intro day and due day", stored,
              predicate=lambda s: '"f":' in s and '"b":1' in s)

        # direction switch
        page.select_option("#w-dir", "ru-mt")
        page.click("#w-show")
        check("reverse direction back text", page.inner_text("#w-back"),
              predicate=lambda s: len(s.strip()) > 0)
        page.select_option("#w-dir", "mt-ru")

        # --- example sentences on the word card ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.select_option("#w-limit", "0")
        page.select_option("#w-topic", label="Еда и напитки")
        with_examples = False
        for _ in range(30):
            if page.locator("#w-show").is_hidden():
                break
            if page.locator("#w-examples .ex-mt").count():
                with_examples = True
                break
            page.click("#w-show")
            page.click("#w-yes")
        check("a word with examples shows them before the answer", with_examples, True)
        check("the example translation is still hidden", page.locator("#w-examples .ex-ru").count(), 0)
        check("the target word is highlighted inside the example",
              page.locator("#w-examples .hl").first.inner_text(),
              predicate=lambda s: s and "." not in s and "?" not in s and " " not in s)
        page.click("#w-show")
        check("revealing adds the example translation",
              page.locator("#w-examples .ex-ru").count(), predicate=lambda n: n >= 1)
        page.locator("#w-examples-toggle").uncheck()
        check("the examples toggle hides them",
              page.locator("#w-examples .ex-mt").count(), 0)
        check("examples toggle is persisted",
              page.evaluate("() => localStorage.getItem('il-malti-examples')"), "0")
        page.locator("#w-examples-toggle").check()

        # --- transcription ---
        coverage = page.evaluate(
            """() => {
              const missing = [];
              window.WORDS.forEach(w => { if (!window.IPA_DATA[w.mt]) missing.push(w.mt); });
              window.SENTENCES.forEach(s => { if (!window.IPA_DATA[s.mt]) missing.push(s.mt); });
              return missing;
            }"""
        )
        check("every word and sentence has a transcription", coverage, [])
        unlinked = page.evaluate(
            "() => Object.values(window.SENTENCE_LINKS).flatMap(v => v.unknown || []).length"
        )
        check("every sentence token maps to a vocabulary entry", unlinked, 0)
        check("sentences are linked to the vocabulary",
              page.evaluate("() => Object.keys(window.SENTENCE_LINKS).length"),
              predicate=lambda n: n > 0)
        check("front transcription on mt-ru", page.inner_text("#w-translit-front"),
              predicate=lambda s: "[" in s and len(s) > 4)
        page.select_option("#w-dir", "ru-mt")
        check("no transcription before reveal (ru-mt)",
              page.locator("#w-translit-front").is_hidden(), True)
        page.click("#w-show")
        check("transcription after reveal (ru-mt)", page.inner_text("#w-translit-back"),
              predicate=lambda s: "[" in s)
        page.locator("#w-translit").uncheck()
        check("toggle hides transcription", page.locator("#w-translit-back").is_hidden(), True)
        check("toggle persisted", page.evaluate("() => localStorage.getItem('il-malti-translit')"), "0")
        page.locator("#w-translit").check()
        page.select_option("#w-dir", "mt-ru")

        # --- sentences: vocabulary gate ---
        page.click('.tab[data-tab="sentences"]')
        # пороги считаем из данных, чтобы тест не устаревал при их правке
        totals = page.evaluate("""() => ({
            total: window.SENTENCES.length,
            open: Object.values(window.SENTENCE_LINKS)
                    .filter(v => (v.words || []).length <= 1).length
          })""")
        check("фразы действительно закрыты не все", totals["open"],
              predicate=lambda n: 0 < n < totals["total"])
        check("few phrases open on a fresh start", page.inner_text("#s-counter"),
              predicate=lambda s: "открыто фраз: %d из %d" % (totals["open"], totals["total"]) in s)
        check("default new-phrases-per-day limit", page.input_value("#s-limit"), "5")
        check("familiarity is reported", page.inner_text("#s-counter"),
              predicate=lambda s: "знакомые слова:" in s)
        chips = page.locator("#s-chips .chip")
        check("build chips rendered", chips.count(), predicate=lambda n: n >= 1)
        check("new words are named in build mode", page.inner_text("#s-known"),
              predicate=lambda s: "Новые слова" in s)
        page.click("#s-reveal")
        check("reveal fills answer", page.inner_text("#s-feedback"),
              predicate=lambda s: s.startswith("Ответ:"))
        check("answer area filled", page.inner_text("#s-answer"),
              predicate=lambda s: len(s.strip()) > 0)
        check("sentence transcription", page.inner_text("#s-translit"),
              predicate=lambda s: "[" in s)
        page.click("#s-next")

        # «Выбор перевода»: русская фраза дана, нужно узнать мальтийскую
        page.select_option("#s-mode", "choice")
        check("choice mode visible", page.locator("#s-choice").is_hidden(), False)
        check("new words hidden in choice mode", page.inner_text("#s-known"),
              predicate=lambda s: "нажми" in s)
        check("three translation options",
              page.locator("#s-choice-list .opt-sentence").count(), 3)
        check("the correct sentence is among the options", page.evaluate("""() => {
              const ru = document.getElementById('s-ru').textContent;
              const s = window.SENTENCES.find(x => x.ru === ru);
              if (!s) return null;
              return [...document.querySelectorAll('#s-choice-list .opt-sentence')]
                       .some(o => o.dataset.mt === s.mt);
            }"""), True)
        check("варианты не повторяются", page.evaluate("""() => {
              const t = [...document.querySelectorAll('#s-choice-list .opt-sentence')]
                          .map(o => o.dataset.mt);
              return new Set(t).size === t.length;
            }"""), True)
        page.evaluate("""() => {
            const ru = document.getElementById('s-ru').textContent;
            const s = window.SENTENCES.find(x => x.ru === ru);
            [...document.querySelectorAll('#s-choice-list .opt-sentence')]
              .find(o => o.dataset.mt !== s.mt).click();
          }""")
        check("a wrong choice is reported", page.inner_text("#s-feedback"),
              predicate=lambda s: s.startswith("Не так"))
        check("the correct option is highlighted",
              page.locator("#s-choice-list .ok").count(), 1)
        check("the wrong option is marked", page.locator("#s-choice-list .bad").count(), 1)
        check("no check button needed in choice mode",
              page.locator("#s-check").is_hidden(), True)
        check("the sentence transcription is shown", page.inner_text("#s-translit"),
              predicate=lambda s: "[" in s)

        # верный выбор уходит дальше сам
        page.click("#s-next")
        page.evaluate("""() => {
            const ru = document.getElementById('s-ru').textContent;
            const s = window.SENTENCES.find(x => x.ru === ru);
            [...document.querySelectorAll('#s-choice-list .opt-sentence')]
              .find(o => o.dataset.mt === s.mt).click();
          }""")
        check("a correct choice is accepted", page.inner_text("#s-feedback"), "Правильно!")
        page.wait_for_timeout(1300)
        check("a correct choice advances by itself",
              page.locator("#s-choice-list .ok").count(), 0)

        # карточка-переворот: ответ скрыт, пока не нажмёшь
        page.select_option("#s-mode", "card")
        secret = page.evaluate("""() => {
              const ru = document.getElementById('s-ru').textContent;
              const s = window.SENTENCES.find(x => x.ru === ru);
              return s ? s.mt : null;
            }""")
        check("в карточке ответ скрыт до переворота",
              page.inner_text("#s-mt") == secret, False)
        check("кнопки оценки скрыты до переворота",
              page.locator("#s-grade").is_hidden(), True)
        page.click("#s-flip")
        check("клик по карточке показывает ответ", page.inner_text("#s-mt"), secret)
        check("транскрипция появляется вместе с ответом", page.inner_text("#s-translit"),
              predicate=lambda s: "[" in s)
        check("кнопки оценки появились", page.locator("#s-grade").is_hidden(), False)
        check("новые слова раскрыты вместе с ответом", page.inner_text("#s-known"),
              predicate=lambda s: "Новые слова" in s)
        before = page.inner_text("#s-counter").split("·")[0]
        page.click("#s-yes")
        check("после оценки кнопки убраны", page.locator("#s-grade").is_hidden(), True)
        page.wait_for_timeout(1300)
        after = page.inner_text("#s-counter").split("·")[0]
        check("«Знаю» уводит к следующей фразе", after != before, True)
        check("на новой карточке ответ снова скрыт",
              page.inner_text("#s-mt") == secret, False)
        check("новая карточка снова без кнопок оценки",
              page.locator("#s-grade").is_hidden(), True)

        page.click("#s-flip")
        page.click("#s-no")
        page.wait_for_timeout(1500)
        after2 = page.inner_text("#s-counter").split("·")[0]
        check("«Не знаю» в карточке тоже уводит дальше", after2 != after, True)
        check("после «Не знаю» кнопки тоже убраны",
              page.locator("#s-grade").is_hidden(), True)

        # --- a topic whose phrases are all locked ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.click('.tab[data-tab="sentences"]')
        page.select_option("#s-topic", label="Семья")
        check("a topic with no open phrases says so",
              page.inner_text("#s-done-title"), "Фразы пока закрыты")
        check("the message names the words that would unlock phrases",
              page.inner_text("#s-done-text"),
              predicate=lambda s: "Выучи эти слова" in s and "фраза" in s)
        check("no actions are offered while locked",
              page.locator("#s-done-actions").is_hidden(), True)
        page.select_option("#s-topic", "all")

        # --- sentence SRS: a failed phrase comes back the same day ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.click('.tab[data-tab="sentences"]')
        page.select_option("#s-limit", "0")
        page.select_option("#s-mode", "card")
        check("all open phrases are queued", page.inner_text("#s-counter"),
              predicate=lambda s: "Фраза 1 из %d" % totals["open"] in s)
        failed = page.inner_text("#s-mt")
        page.click("#s-reveal")
        page.click("#s-no")
        # после ответа «Показать ответ» скрывается — дальше идём кнопкой в панели
        page.click("#s-next")
        for _ in range(totals["open"] - 1):
            page.click("#s-reveal")
            page.click("#s-yes")
        page.wait_for_timeout(1300)      # ждём отложенный автопереход
        check("failed phrase returned", page.inner_text("#s-counter"),
              predicate=lambda s: s.startswith("Фраза 1 из 1"))
        check("it is the same phrase", page.inner_text("#s-mt"), failed)
        page.click("#s-reveal")
        page.click("#s-yes")
        page.wait_for_timeout(1300)      # ждём отложенный автопереход
        check("phrases done for today", page.locator("#s-done").is_visible(), True)
        check("done text reports new phrases", page.inner_text("#s-done-text"),
              predicate=lambda s: "Новых фраз сегодня: %d" % totals["open"] in s)

        # --- learning the vocabulary opens more phrases ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.click('.tab[data-tab="sentences"]')
        check("open-phrase count matches the data", page.inner_text("#s-counter"),
              predicate=lambda s: "открыто фраз: %d из %d" % (totals["open"], totals["total"]) in s)
        linked = page.evaluate(
            "() => [...new Set(Object.values(window.SENTENCE_LINKS).flatMap(v => v.words))]"
        )
        word_total = page.evaluate("() => window.WORDS.length")
        check("фразы используют лишь часть словаря", len(linked),
              predicate=lambda n: 0 < n < word_total)
        state = {
            "items": {("w:" + mt): {"b": 1, "d": 0, "f": 0} for mt in linked},
            "stats": {"word": {"ok": 0, "no": 0}, "sent": {"ok": 0, "no": 0}},
            "days": {},
        }
        page.evaluate("s => localStorage.setItem('il-malti-v1', s)", json.dumps(state))
        page.reload()
        page.click('.tab[data-tab="sentences"]')
        check("all phrases open once their vocabulary is known",
              page.inner_text("#s-counter"),
              predicate=lambda s: "открыто фраз: %d из %d" % (totals["total"], totals["total"]) in s)

        # --- формы: четыре режима на одном движке ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.click('.tab[data-tab="forms"]')
        check("four morphology modes offered", page.locator("#fm-mode option").count(), 4)
        check("queue respects the daily limit", page.inner_text("#fm-counter"),
              predicate=lambda s: "Упражнение 1 из 10" in s and "0/10" in s)

        rows_expected_map = {"pair": 3, "agree": 4, "plural": 2, "prep": 3}
        for mode, rows_expected in (("pair", 3), ("agree", 4), ("plural", 2), ("prep", 3)):
            page.select_option("#fm-mode", mode)
            # у множественного число вопросов зависит от слова (неисчисляемые -> без перевода)
            if mode == "plural":
                check("plural: 2 or 3 question rows",
                      page.locator("#fm-quiz .quiz-row").count(),
                      predicate=lambda n: n in (2, 3))
            else:
                check("%s: question rows" % mode,
                      page.locator("#fm-quiz .quiz-row").count(), rows_expected)
            check("%s: prompt rendered" % mode, page.inner_text("#fm-prompt"),
                  predicate=lambda s: len(s.strip()) > 0)
            check("%s: every row offers choices" % mode,
                  page.evaluate("""() => [...document.querySelectorAll('#fm-quiz .quiz-options')]
                      .every(b => b.querySelectorAll('.opt').length >= 2)"""), True)
            check("%s: every row has a real correct answer" % mode,
                  page.evaluate("""() => {
                    const rows = JSON.parse(document.getElementById('fm-correct').value);
                    return rows.length > 0 && rows.every(r =>
                      [...document.querySelectorAll('#fm-quiz .quiz-options[data-key="' + r.key + '"] .opt')]
                        .some(o => o.dataset.value === r.correct));
                  }"""), True)
            has_ru_q = page.evaluate("""() => {
                const cyr = /[а-яё]/i;
                return [...document.querySelectorAll('#fm-quiz .opt')].some(o => cyr.test(o.textContent));
              }""")
            if mode == "plural":
                # у неисчисляемых (birra, patata, ewro) русского мн. ч. нет — строки тоже нет
                needs = page.evaluate("""() => {
                    const noun = document.querySelector('#fm-prompt .pair-part').textContent;
                    const it = window.FORMS.plural.find(x => x.noun === noun);
                    return it ? !!it.ruPl : null;
                  }""")
                check("plural: перевод показан тогда и только тогда, когда он есть",
                      has_ru_q == bool(needs), True)
            else:
                check("%s: a translation question is present" % mode, has_ru_q, True)
            page.click("#fm-check")
            check("%s: incomplete answer rejected" % mode, page.inner_text("#fm-feedback"),
                  predicate=lambda s: "все пункты" in s)

        # неверный ответ по каждому пункту -> режим должен назвать, что не так
        for mode in ("pair", "agree", "plural", "prep"):
            page.select_option("#fm-mode", mode)
            rows = page.evaluate("() => JSON.parse(document.getElementById('fm-correct').value)")
            for r in rows:
                page.evaluate("""r => {
                  const box = document.querySelector("#fm-quiz .quiz-options[data-key='" + r.key + "']");
                  const el = [...box.querySelectorAll('.opt')].find(o => o.dataset.value !== r.correct);
                  if (el) el.click();
                }""", r)
            page.click("#fm-check")
            check("%s: wrong answer is named" % mode, page.inner_text("#fm-feedback"),
                  predicate=lambda s: s.startswith("Неверно"))
            check("%s: correct options are highlighted" % mode,
                  page.locator("#fm-quiz .opt.ok").count(), len(rows))
            check("%s: the answer is shown" % mode, page.inner_text("#fm-answer"),
                  predicate=lambda s: len(s.strip()) > 0)

        # верный ответ уходит сам
        page.select_option("#fm-mode", "agree")
        rows = page.evaluate("() => JSON.parse(document.getElementById('fm-correct').value)")
        for r in rows:
            page.evaluate("""r => {
              const box = document.querySelector("#fm-quiz .quiz-options[data-key='" + r.key + "']");
              [...box.querySelectorAll('.opt')].find(o => o.dataset.value === r.correct).click();
            }""", r)
        page.click("#fm-check")
        check("a fully correct answer is accepted", page.inner_text("#fm-feedback"), "Верно!")
        page.wait_for_timeout(1300)
        check("a correct answer advances by itself", page.inner_text("#fm-counter"),
              predicate=lambda s: "Упражнение 2 из 10" in s)

        # старое сохранённое состояние без новых счётчиков не должно ломать вкладку
        page.evaluate("""() => localStorage.setItem('il-malti-v1',
          JSON.stringify({items:{},stats:{word:{ok:1,no:0},sent:{ok:0,no:0}},days:{}}))""")
        page.reload()
        page.click('.tab[data-tab="forms"]')
        check("state from an older version still works", page.inner_text("#fm-counter"),
              predicate=lambda s: "Упражнение 1" in s)

        # --- разбор ошибок: собираем фразу в неверном порядке ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.click('.tab[data-tab="sentences"]')
        # открыть все фразы, иначе в пуле одни односложные приветствия
        linked_all = page.evaluate(
            "() => [...new Set(Object.values(window.SENTENCE_LINKS).flatMap(v => v.words))]")
        page.evaluate("s => localStorage.setItem('il-malti-v1', s)", json.dumps({
            "items": {("w:" + mt): {"b": 1, "d": 0, "f": 0} for mt in linked_all},
            "stats": {}, "days": {}}))
        page.reload()
        page.click('.tab[data-tab="sentences"]')
        page.select_option("#s-mode", "build")
        page.select_option("#s-limit", "0")
        # ищем фразу из >=3 слов без повторов и сразу считаем индексы чипов
        plan = None
        for _ in range(60):
            plan = page.evaluate("""() => {
              const ru = document.getElementById('s-ru').textContent;
              const s = window.SENTENCES.find(x => x.ru === ru);
              if (!s) return null;
              const strip = t => t.replace(/^[«"'(]+/, '').replace(/[.,!?;:]+$/, '');
              const toks = s.mt.split(' ').map(strip);
              if (toks.length < 3 || new Set(toks).size !== toks.length) return null;
              const chips = [...document.querySelectorAll('#s-chips .chip')].map(c => c.textContent);
              const used = chips.map(() => false);
              const idx = toks.map(t => {
                const i = chips.findIndex((c, j) => !used[j] && c === t);
                if (i >= 0) used[i] = true;
                return i;
              });
              if (idx.some(i => i < 0)) return null;
              return { toks: toks, idx: idx };
            }""")
            if plan:
                break
            page.click("#s-next")
        check("нашли фразу из трёх и более разных слов",
              plan is not None, True)
        # строим верный порядок, но меняем местами первые два слова — ошибка гарантирована
        order = plan["idx"][:]
        order[0], order[1] = order[1], order[0]
        for i in order:
            page.locator("#s-chips .chip").nth(i).click()
        page.click("#s-check")
        check("a wrong sentence is reported", page.inner_text("#s-feedback"),
              predicate=lambda s: s.startswith("Не так"))
        check("the diff block appears", page.locator("#s-diff").is_hidden(), False)
        diff = page.inner_text("#s-diff")
        check("the diff shows both answers", diff,
              predicate=lambda s: "твой ответ" in s and "правильно" in s)
        check("the diff counts the mismatches", diff,
              predicate=lambda s: "Расхождений" in s)
        page.click("#s-next")
        check("the diff is cleared for the next sentence",
              page.locator("#s-diff").is_hidden(), True)
        page.select_option("#s-limit", "5")

        # --- «Заполнить пропуски»: форма в живом предложении ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.click('.tab[data-tab="sentences"]')
        check("предложений четыре режима",
              page.locator("#s-mode option").count(), 4)
        page.select_option("#s-mode", "blanks")
        check("режим пропусков виден", page.locator("#s-blanks").is_hidden(), False)
        check("в подписи сказано определить лицо", page.inner_text("#s-prompt-label"),
              predicate=lambda s: "лицо" in s)

        data = page.evaluate("""() => {
              const sent = document.getElementById('s-ru').textContent;
              const it = window.BLANKS.find(x => x.sent.replace(/\\{(\\d+)\\}/g, '_____') === sent);
              if (!it) return null;
              return {
                blanks: it.blanks.length,
                answers: it.blanks.map(b => window.BLANK_FORMS[b.hint][b.key]),
                ru: it.ru,
                full: it.full
              };
            }""")
        check("упражнение найдено в данных", data is not None, True)
        check("в предложении столько же пропусков",
              page.locator("#s-ru .blank-slot").count(), data["blanks"])
        check("на каждый пропуск своя строка вариантов",
              page.locator("#s-blank-rows .quiz-options").count(), data["blanks"])
        check("у каждого пропуска три варианта", page.evaluate("""() =>
              [...document.querySelectorAll('#s-blank-rows .quiz-options')]
                .every(r => r.querySelectorAll('.opt').length === 3)"""), True)
        check("варианты внутри пропуска не повторяются", page.evaluate("""() =>
              [...document.querySelectorAll('#s-blank-rows .quiz-options')]
                .every(r => { const v = [...r.querySelectorAll('.opt')].map(o => o.dataset.value);
                              return new Set(v).size === v.length; })"""), True)
        check("верный вариант есть среди предложенных", page.evaluate("""(answers) =>
              [...document.querySelectorAll('#s-blank-rows .quiz-options')]
                .every((r, i) => [...r.querySelectorAll('.opt')]
                  .some(o => o.dataset.value === answers[i]))""", data["answers"]), True)
        # подписи берём из данных, чтобы не зависеть от того, глагол это или существительное
        labels = page.evaluate("() => Object.values(window.BLANK_LABELS)")
        check("подсказка о форме в вопросе НЕ показана",
              any(l in page.inner_text("#s-blank-rows") for l in labels), False)

        page.click("#s-check")
        check("незаполненные пропуски не принимаются", page.inner_text("#s-feedback"),
              predicate=lambda s: "Заполни все пропуски" in s)

        # один пропуск неверный
        page.evaluate("""(answers) => {
            const rows = [...document.querySelectorAll('#s-blank-rows .quiz-options')];
            rows.forEach((r, i) => {
              const pick = i === 0
                ? [...r.querySelectorAll('.opt')].find(o => o.dataset.value !== answers[i])
                : [...r.querySelectorAll('.opt')].find(o => o.dataset.value === answers[i]);
              pick.click();
            });
          }""", data["answers"])
        page.click("#s-check")
        check("неверный ответ посчитан по пропускам", page.inner_text("#s-feedback"),
              predicate=lambda s: s.startswith("Неверно: пропусков с ошибкой — 1 из"))
        check("верные варианты подсвечены", page.locator("#s-blank-rows .opt.ok").count(),
              data["blanks"])
        check("неверный вариант зачёркнут", page.locator("#s-blank-rows .opt.bad").count(), 1)
        check("пропуски в предложении подсвечены",
              page.locator("#s-ru .blank-slot.ok").count() + page.locator("#s-ru .blank-slot.bad").count(),
              data["blanks"])
        answer_text = page.inner_text("#s-blank-answer")
        check("разбор показывает полную фразу", answer_text, predicate=lambda s: data["full"] in s)
        check("разбор показывает перевод", answer_text, predicate=lambda s: data["ru"] in s)
        check("разбор называет форму", answer_text,
              predicate=lambda s: any(l in s for l in labels))
        check("разбор объясняет каждую подстановку", answer_text,
              predicate=lambda s: s.count("→") >= data["blanks"])
        check("разбор даёт транскрипцию", page.inner_text("#s-translit"),
              predicate=lambda s: "[" in s)

        # верный ответ уходит сам
        before = page.inner_text("#s-counter").split("·")[0]
        page.click("#s-next")
        data2 = page.evaluate("""() => {
              const sent = document.getElementById('s-ru').textContent;
              const it = window.BLANKS.find(x => x.sent.replace(/\\{(\\d+)\\}/g, '_____') === sent);
              return it ? it.blanks.map(b => window.BLANK_FORMS[b.hint][b.key]) : null;
            }""")
        page.evaluate("""(answers) => {
            [...document.querySelectorAll('#s-blank-rows .quiz-options')].forEach((r, i) => {
              [...r.querySelectorAll('.opt')].find(o => o.dataset.value === answers[i]).click();
            });
          }""", data2)
        page.click("#s-check")
        check("все верные ответы принимаются", page.inner_text("#s-feedback"), "Верно!")
        page.wait_for_timeout(1300)
        check("верный ответ уводит к следующей фразе",
              page.inner_text("#s-counter").split("·")[0] != before, True)
        check("на новой фразе пропуски снова пустые",
              page.locator("#s-ru .blank-slot.ok").count() +
              page.locator("#s-ru .blank-slot.bad").count(), 0)

        # --- alphabet ---        # --- alphabet ---
        page.click('.tab[data-tab="alphabet"]')
        check("alphabet cells", page.locator("#alpha-grid .alpha-cell").count(), 30)
        check("alphabet copy keys", page.locator("#copy-kbd .key").count(), 11)
        check("transcription legend rows", page.locator("#view-alphabet .legend li").count(), 6)

        # --- progress ---
        page.click('.tab[data-tab="progress"]')
        check("stat cards", page.locator("#p-stats .stat").count(), 6)
        check("box rows", page.locator("#p-boxes .box-row").count(), 7)
        check("progress rows per exercise set", page.locator("#p-sets .set-row").count(), 6)
        check("answer rows per mode", page.locator("#p-kinds .set-row").count(), 4)
        check("day rows", page.locator("#p-days .box-row").count(), 7)

        # --- reset ---
        page.on("dialog", lambda d: d.accept())
        page.click("#p-reset")
        page.wait_for_timeout(300)
        cleared = page.evaluate("() => localStorage.getItem('il-malti-v1')")
        check("reset clears progress", cleared, predicate=lambda s: s and '"items":{}' in s)
        check("stats reset", page.inner_text("#p-stats"), predicate=lambda s: "0%" in s)

        # --- статистика: ответы учитываются во всех режимах ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        total_words = page.evaluate("() => window.WORDS.length")

        # (1) ответ в «Формах» должен попасть в общий счёт и в точность
        page.click('.tab[data-tab="forms"]')
        page.select_option("#fm-mode", "agree")
        rows = page.evaluate("() => JSON.parse(document.getElementById('fm-correct').value)")
        for r in rows:
            page.evaluate("""r => {
              const box = document.querySelector("#fm-quiz .quiz-options[data-key='" + r.key + "']");
              [...box.querySelectorAll('.opt')].find(o => o.dataset.value === r.correct).click();
            }""", r)
        page.click("#fm-check")
        page.wait_for_timeout(1200)
        page.click('.tab[data-tab="progress"]')
        stats = page.inner_text("#p-stats")
        check("ответ из «Форм» попал в «Всего ответов»", stats,
              predicate=lambda s: "1\nВсего ответов" in s)
        check("точность считается по всем режимам", stats,
              predicate=lambda s: "100%\nТочность" in s)
        kinds = [x.replace("\n", " ") for x in page.evaluate(
            "() => [...document.querySelectorAll('#p-kinds .set-row')].map(r => r.innerText)")]
        check("ответ учтён в счётчике своего режима",
              [k for k in kinds if k.startswith("Согласование") and "ответов: 1" in k],
              predicate=lambda v: len(v) == 1)
        check("нулевые счётчики остались нулевыми",
              [k for k in kinds if "Слова" in k and "ответов: 0" in k],
              predicate=lambda v: len(v) == 1)

        # (2) проваленное слово — это «начатое», а не «не начатое»
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.click('.tab[data-tab="words"]')
        failed_word = page.inner_text("#w-front")
        page.click("#w-show")
        page.click("#w-no")
        page.click('.tab[data-tab="progress"]')
        boxes = page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('#p-boxes .box-row')]
          .map(r => [r.querySelector('.box-label').textContent, Number(r.querySelector('.box-count').textContent)]))""")
        check("новых слов осталось на одно меньше", boxes.get("Не начатые"), total_words - 1)
        check("проваленное слово попало в коробку 0",
              boxes.get("Коробка 0 (проваленные)"), 1)
        check("строк в гистограмме — семь", len(boxes), 7)
        check("«Слов начато» учитывает провал", page.inner_text("#p-stats"),
              predicate=lambda s: "1 из %d\nСлов начато" % total_words in s)

        # (3) у каждого набора упражнений виден свой прогресс
        sets = [x.replace("\n", " ") for x in page.evaluate(
            "() => [...document.querySelectorAll('#p-sets .set-row')].map(r => r.innerText)")]
        check("прогресс показан по всем наборам", len(sets), 6)
        check("у наборов видны начатые и «далее»",
              all("начато:" in x and "далее:" in x and "к повторению:" in x for x in sets), True)

        # (4) слово со сроком возвращается и показывается РАНЬШЕ новых
        import json as _json
        due_state = {"items": {"w:" + failed_word: {"b": 2, "d": 0, "f": 0}},
                     "stats": {}, "days": {}}
        page.evaluate("s => localStorage.setItem('il-malti-v1', s)", _json.dumps(due_state))
        page.reload()
        page.click('.tab[data-tab="words"]')
        check("слово со сроком стоит первым в очереди", page.inner_text("#w-front"), failed_word)
        check("в очереди есть и новые слова", page.inner_text("#w-counter"),
              predicate=lambda s: int(s.split("В очереди: ")[1].split(" ")[0]) > 1)

        # (5) когда всё выучено и срок далёкий — очередь пуста, видно когда повторение
        all_ids = page.evaluate("() => window.WORDS.map(w => 'w:' + w.mt)")
        page.evaluate("s => localStorage.setItem('il-malti-v1', s)",
                      _json.dumps({"items": {uid: {"b": 5, "d": 99999, "f": 0} for uid in all_ids},
                                   "stats": {}, "days": {}}))
        page.reload()
        page.click('.tab[data-tab="words"]')
        check("когда повторять нечего — блок «на сегодня всё»",
              page.locator("#w-done").is_visible(), True)
        check("видно, когда следующее повторение", page.inner_text("#w-done-text"),
              predicate=lambda s: "Следующее повторение" in s and "через" in s)
        page.click('.tab[data-tab="progress"]')
        check("прогресс видит, что начаты все слова", page.inner_text("#p-stats"),
              predicate=lambda s: "%d из %d\nСлов начато" % (total_words, total_words) in s)
        check("далёкие слова не числятся к повторению", page.inner_text("#p-stats"),
              predicate=lambda s: "0\nСлов к повторению сейчас" in s)

        # вернуть чистое состояние для следующих блоков
        page.evaluate("() => localStorage.clear()")
        page.reload()

        # --- daily new-word limit and the "all done" state ---
        page.click('.tab[data-tab="words"]')
        check("queue rebuilt after reset", page.inner_text("#w-counter"),
              predicate=lambda s: "В очереди: 10" in s and "0/10" in s)
        page.select_option("#w-limit", "5")
        check("changing the limit rebuilds the queue", page.inner_text("#w-counter"),
              predicate=lambda s: "В очереди: 5" in s and "0/5" in s)

        for _ in range(5):
            page.click("#w-show")
            page.click("#w-yes")
        check("done block appears when the day is finished",
              page.locator("#w-done").is_visible(), True)
        check("card is hidden in the done state",
              page.locator("#w-card").is_visible(), False)
        done_text = page.inner_text("#w-done-text")
        check("done text reports today's new words and next review", done_text,
              predicate=lambda s: "Новых сегодня: 5 из 5" in s and "Следующее повторение" in s)

        page.click("#w-bypass")
        check("bypass shows the remaining new words", page.inner_text("#w-counter"),
              predicate=lambda s: "сверх лимита" in s and "В очереди: " in s)
        check("card is back after bypass", page.locator("#w-card").is_visible(), True)
        page.select_option("#w-limit", "10")

        # --- wrong answer comes back the same day ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.locator("#w-limit").select_option("5")
        for _ in range(4):
            page.click("#w-show")
            page.click("#w-yes")
        page.click("#w-show")
        page.click("#w-no")
        failed_first = page.inner_text("#w-front")
        check("queue keeps only the failed word", page.inner_text("#w-counter"),
              predicate=lambda s: "В очереди: 1" in s and "новых сегодня: 5/5" in s)
        check("the failed word returned", page.inner_text("#w-front"), failed_first)
        page.click("#w-show")
        page.click("#w-yes")
        check("day finishes once the failed word is learned",
              page.locator("#w-done").is_visible(), True)

        # --- sentence practice must not eat the new-word budget ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.click('.tab[data-tab="sentences"]')
        page.select_option("#s-mode", "card")
        for _ in range(3):
            page.click("#s-reveal")
            page.click("#s-yes")
        sent_records = page.evaluate(
            "() => Object.keys(JSON.parse(localStorage.getItem('il-malti-v1')).items)"
            ".filter(k => k.indexOf('s:') === 0).length"
        )
        check("sentence answers are recorded", sent_records, 3)
        page.click('.tab[data-tab="words"]')
        check("sentences do not consume the new-word budget", page.inner_text("#w-counter"),
              predicate=lambda s: "В очереди: 10" in s and "новых сегодня: 0/10" in s)

        browser.close()

    if httpd:
        httpd.shutdown()

    check("console errors", console_errors, [])

    print()
    if failures:
        print("FAILED (%d):" % len(failures))
        for f in failures:
            print("  -", f)
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
