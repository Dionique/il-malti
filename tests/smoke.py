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

        check("REQ-SHELL-01 title", page.title(), predicate=lambda t: "Malti" in t)

        # --- words ---
        # число тем считаем из данных, чтобы тест не устаревал при их добавлении
        topic_count = page.evaluate("() => new Set(window.WORDS.map(w => w.topic)).size")
        check("REQ-WORDS-01 words topic options", page.locator("#w-topic option").count(), topic_count + 1)
        check("REQ-WORDS-01 default new-words-per-day limit", page.input_value("#w-limit"), "10")
        check("REQ-WORDS-01 first queue is capped by the daily limit", page.inner_text("#w-counter"),
              predicate=lambda s: "В очереди: 10" in s and "новых сегодня: 0/10" in s)
        page.click("#w-show")
        back = page.inner_text("#w-back")
        check("REQ-WORDS-07 reveal shows translation", back, predicate=lambda s: len(s.strip()) > 0)
        check("REQ-WORDS-07 grade buttons appear", page.locator("#w-grade").is_hidden(), False)
        page.click("#w-yes")
        check("REQ-WORDS-01 queue shrinks and new counter grows", page.inner_text("#w-counter"),
              predicate=lambda s: "В очереди: 9" in s and "1/10" in s)
        stored = page.evaluate("() => localStorage.getItem('il-malti-v1')")
        check("REQ-SHELL-02 progress persisted", stored, predicate=lambda s: s and "items" in s)
        check("REQ-WORDS-04 record keeps intro day and due day", stored,
              predicate=lambda s: '"f":' in s and '"b":1' in s)

        # direction switch
        page.select_option("#w-dir", "ru-mt")
        page.click("#w-show")
        check("REQ-WORDS-05 reverse direction back text", page.inner_text("#w-back"),
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
        check("REQ-EX-01 a word with examples shows them before the answer", with_examples, True)
        check("REQ-EX-01 the example translation is still hidden", page.locator("#w-examples .ex-ru").count(), 0)
        check("REQ-EX-02 the target word is highlighted inside the example",
              page.locator("#w-examples .hl").first.inner_text(),
              predicate=lambda s: s and "." not in s and "?" not in s and " " not in s)
        page.click("#w-show")
        check("REQ-EX-03 revealing adds the example translation",
              page.locator("#w-examples .ex-ru").count(), predicate=lambda n: n >= 1)
        page.locator("#w-examples-toggle").uncheck()
        check("REQ-EX-04 the examples toggle hides them",
              page.locator("#w-examples .ex-mt").count(), 0)
        check("REQ-SHELL-03 examples toggle is persisted",
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
        check("REQ-TR-01 every word and sentence has a transcription", coverage, [])
        unlinked = page.evaluate(
            "() => Object.values(window.SENTENCE_LINKS).flatMap(v => v.unknown || []).length"
        )
        check("REQ-SENT-01 every sentence token maps to a vocabulary entry", unlinked, 0)
        check("REQ-SENT-01 sentences are linked to the vocabulary",
              page.evaluate("() => Object.keys(window.SENTENCE_LINKS).length"),
              predicate=lambda n: n > 0)
        check("REQ-TR-02 front transcription on mt-ru", page.inner_text("#w-translit-front"),
              predicate=lambda s: "[" in s and len(s) > 4)
        page.select_option("#w-dir", "ru-mt")
        check("REQ-TR-02 no transcription before reveal (ru-mt)",
              page.locator("#w-translit-front").is_hidden(), True)
        page.click("#w-show")
        check("REQ-TR-02 transcription after reveal (ru-mt)", page.inner_text("#w-translit-back"),
              predicate=lambda s: "[" in s)
        page.locator("#w-translit").uncheck()
        check("REQ-TR-03 toggle hides transcription", page.locator("#w-translit-back").is_hidden(), True)
        check("REQ-SHELL-03 toggle persisted", page.evaluate("() => localStorage.getItem('il-malti-translit')"), "0")
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
        check("REQ-SENT-02 фразы действительно закрыты не все", totals["open"],
              predicate=lambda n: 0 < n < totals["total"])
        check("REQ-SENT-02 few phrases open on a fresh start", page.inner_text("#s-counter"),
              predicate=lambda s: "открыто фраз: %d из %d" % (totals["open"], totals["total"]) in s)
        check("REQ-SENT-08 default new-phrases-per-day limit", page.input_value("#s-limit"), "5")
        check("REQ-SENT-04 familiarity is reported", page.inner_text("#s-counter"),
              predicate=lambda s: "знакомые слова:" in s)
        chips = page.locator("#s-chips .chip")
        check("REQ-SENT-04 build chips rendered", chips.count(), predicate=lambda n: n >= 1)
        check("REQ-SENT-04 new words are named in build mode", page.inner_text("#s-known"),
              predicate=lambda s: "Новые слова" in s)
        page.click("#s-reveal")
        check("REQ-SENT-04 reveal fills answer", page.inner_text("#s-feedback"),
              predicate=lambda s: s.startswith("Ответ:"))
        check("REQ-SENT-04 answer area filled", page.inner_text("#s-answer"),
              predicate=lambda s: len(s.strip()) > 0)
        check("REQ-TR-04 sentence transcription", page.inner_text("#s-translit"),
              predicate=lambda s: "[" in s)
        page.click("#s-next")

        # «Выбор перевода»: русская фраза дана, нужно узнать мальтийскую
        page.select_option("#s-mode", "choice")
        check("REQ-SENT-05 choice mode visible", page.locator("#s-choice").is_hidden(), False)
        check("REQ-SENT-05 new words hidden in choice mode", page.inner_text("#s-known"),
              predicate=lambda s: "нажми" in s)
        check("REQ-SENT-05 three translation options",
              page.locator("#s-choice-list .opt-sentence").count(), 3)
        check("REQ-SENT-05 the correct sentence is among the options", page.evaluate("""() => {
              const ru = document.getElementById('s-ru').textContent;
              const s = window.SENTENCES.find(x => x.ru === ru);
              if (!s) return null;
              return [...document.querySelectorAll('#s-choice-list .opt-sentence')]
                       .some(o => o.dataset.mt === s.mt);
            }"""), True)
        check("REQ-SENT-05 варианты не повторяются", page.evaluate("""() => {
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
        check("REQ-SENT-05 a wrong choice is reported", page.inner_text("#s-feedback"),
              predicate=lambda s: s.startswith("Не так"))
        check("REQ-SENT-05 the correct option is highlighted",
              page.locator("#s-choice-list .ok").count(), 1)
        check("REQ-SENT-05 the wrong option is marked", page.locator("#s-choice-list .bad").count(), 1)
        check("REQ-SENT-05 no check button needed in choice mode",
              page.locator("#s-check").is_hidden(), True)
        check("REQ-TR-04 the sentence transcription is shown", page.inner_text("#s-translit"),
              predicate=lambda s: "[" in s)
        check("REQ-SENT-09 после неверного выбора есть кнопка «Дальше»",
              page.locator("#s-forward").is_hidden(), False)

        # верный выбор уходит дальше сам
        page.click("#s-next")
        page.evaluate("""() => {
            const ru = document.getElementById('s-ru').textContent;
            const s = window.SENTENCES.find(x => x.ru === ru);
            [...document.querySelectorAll('#s-choice-list .opt-sentence')]
              .find(o => o.dataset.mt === s.mt).click();
          }""")
        check("REQ-SENT-05 a correct choice is accepted", page.inner_text("#s-feedback"), "Правильно!")
        page.wait_for_timeout(1300)
        check("REQ-SENT-05 a correct choice advances by itself",
              page.locator("#s-choice-list .ok").count(), 0)

        # карточка-переворот: ответ скрыт, пока не нажмёшь
        page.select_option("#s-mode", "card")
        secret = page.evaluate("""() => {
              const ru = document.getElementById('s-ru').textContent;
              const s = window.SENTENCES.find(x => x.ru === ru);
              return s ? s.mt : null;
            }""")
        check("REQ-SENT-06 в карточке ответ скрыт до переворота",
              page.inner_text("#s-mt") == secret, False)
        check("REQ-SENT-06 кнопки оценки скрыты до переворота",
              page.locator("#s-grade").is_hidden(), True)
        page.click("#s-flip")
        check("REQ-SENT-06 клик по карточке показывает ответ", page.inner_text("#s-mt"), secret)
        check("REQ-TR-04 транскрипция появляется вместе с ответом", page.inner_text("#s-translit"),
              predicate=lambda s: "[" in s)
        check("REQ-SENT-06 кнопки оценки появились", page.locator("#s-grade").is_hidden(), False)
        check("REQ-EX-03 новые слова раскрыты вместе с ответом", page.inner_text("#s-known"),
              predicate=lambda s: "Новые слова" in s)
        before = page.inner_text("#s-counter").split("·")[0]
        page.click("#s-yes")
        check("REQ-SENT-06 после оценки кнопки убраны", page.locator("#s-grade").is_hidden(), True)
        page.wait_for_timeout(1300)
        after = page.inner_text("#s-counter").split("·")[0]
        check("REQ-SENT-06 «Знаю» уводит к следующей фразе", after != before, True)
        check("REQ-SENT-06 на новой карточке ответ снова скрыт",
              page.inner_text("#s-mt") == secret, False)
        check("REQ-SENT-06 новая карточка снова без кнопок оценки",
              page.locator("#s-grade").is_hidden(), True)

        page.click("#s-flip")
        page.click("#s-no")
        page.wait_for_timeout(1500)
        after2 = page.inner_text("#s-counter").split("·")[0]
        check("REQ-SENT-06 «Не знаю» в карточке тоже уводит дальше", after2 != after, True)
        check("REQ-SENT-06 после «Не знаю» кнопки тоже убраны",
              page.locator("#s-grade").is_hidden(), True)

        # --- a topic whose phrases are all locked ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.click('.tab[data-tab="sentences"]')
        page.select_option("#s-topic", label="Семья")
        check("REQ-SENT-03 a topic with no open phrases says so",
              page.inner_text("#s-done-title"), "Фразы пока закрыты")
        check("REQ-SENT-03 the message names the words that would unlock phrases",
              page.inner_text("#s-done-text"),
              predicate=lambda s: "Выучи эти слова" in s and "фраза" in s)
        check("REQ-SENT-03 no actions are offered while locked",
              page.locator("#s-done-actions").is_hidden(), True)
        page.select_option("#s-topic", "all")

        # --- sentence SRS: a failed phrase comes back the same day ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.click('.tab[data-tab="sentences"]')
        page.select_option("#s-limit", "0")
        page.select_option("#s-mode", "card")
        check("REQ-SENT-08 all open phrases are queued", page.inner_text("#s-counter"),
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
        check("REQ-SENT-08 failed phrase returned", page.inner_text("#s-counter"),
              predicate=lambda s: s.startswith("Фраза 1 из 1"))
        check("REQ-SENT-08 it is the same phrase", page.inner_text("#s-mt"), failed)
        page.click("#s-reveal")
        page.click("#s-yes")
        page.wait_for_timeout(1300)      # ждём отложенный автопереход
        check("REQ-SENT-08 phrases done for today", page.locator("#s-done").is_visible(), True)
        check("REQ-SENT-08 done text reports new phrases", page.inner_text("#s-done-text"),
              predicate=lambda s: "Новых фраз сегодня: %d" % totals["open"] in s)

        # --- learning the vocabulary opens more phrases ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.click('.tab[data-tab="sentences"]')
        check("REQ-SENT-02 open-phrase count matches the data", page.inner_text("#s-counter"),
              predicate=lambda s: "открыто фраз: %d из %d" % (totals["open"], totals["total"]) in s)
        linked = page.evaluate(
            "() => [...new Set(Object.values(window.SENTENCE_LINKS).flatMap(v => v.words))]"
        )
        word_total = page.evaluate("() => window.WORDS.length")
        check("REQ-SENT-01 фразы используют лишь часть словаря", len(linked),
              predicate=lambda n: 0 < n < word_total)
        state = {
            "items": {("w:" + mt): {"b": 1, "d": 0, "f": 0} for mt in linked},
            "stats": {"word": {"ok": 0, "no": 0}, "sent": {"ok": 0, "no": 0}},
            "days": {},
        }
        page.evaluate("s => localStorage.setItem('il-malti-v1', s)", json.dumps(state))
        page.reload()
        page.click('.tab[data-tab="sentences"]')
        check("REQ-SENT-02 all phrases open once their vocabulary is known",
              page.inner_text("#s-counter"),
              predicate=lambda s: "открыто фраз: %d из %d" % (totals["total"], totals["total"]) in s)

        # --- формы: четыре режима на одном движке ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.click('.tab[data-tab="forms"]')
        check("REQ-FORMS-01 four morphology modes offered", page.locator("#fm-mode option").count(), 4)
        check("REQ-FORMS-05 queue respects the daily limit", page.inner_text("#fm-counter"),
              predicate=lambda s: "Упражнение 1 из 10" in s and "0/10" in s)

        rows_expected_map = {"pair": 3, "agree": 4, "plural": 2, "prep": 3}
        for mode, rows_expected in (("pair", 3), ("agree", 4), ("plural", 2), ("prep", 3)):
            page.select_option("#fm-mode", mode)
            # у множественного число вопросов зависит от слова (неисчисляемые -> без перевода)
            if mode == "plural":
                check("REQ-FORMS-02 plural: 2 or 3 question rows",
                      page.locator("#fm-quiz .quiz-row").count(),
                      predicate=lambda n: n in (2, 3))
            else:
                check("REQ-FORMS-02 %s: question rows" % mode,
                      page.locator("#fm-quiz .quiz-row").count(), rows_expected)
            check("REQ-FORMS-02 %s: prompt rendered" % mode, page.inner_text("#fm-prompt"),
                  predicate=lambda s: len(s.strip()) > 0)
            check("REQ-FORMS-02 %s: every row offers choices" % mode,
                  page.evaluate("""() => [...document.querySelectorAll('#fm-quiz .quiz-options')]
                      .every(b => b.querySelectorAll('.opt').length >= 2)"""), True)
            check("REQ-FORMS-02 %s: every row has a real correct answer" % mode,
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
                check("REQ-FORMS-03 plural: перевод показан тогда и только тогда, когда он есть",
                      has_ru_q == bool(needs), True)
            else:
                check("REQ-FORMS-03 %s: a translation question is present" % mode, has_ru_q, True)
            page.click("#fm-check")
            check("REQ-FORMS-04 %s: incomplete answer rejected" % mode, page.inner_text("#fm-feedback"),
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
            check("REQ-FORMS-04 %s: wrong answer is named" % mode, page.inner_text("#fm-feedback"),
                  predicate=lambda s: s.startswith("Неверно"))
            check("REQ-FORMS-04 %s: correct options are highlighted" % mode,
                  page.locator("#fm-quiz .opt.ok").count(), len(rows))
            check("REQ-FORMS-04 %s: the answer is shown" % mode, page.inner_text("#fm-answer"),
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
        check("REQ-FORMS-04 a fully correct answer is accepted", page.inner_text("#fm-feedback"), "Верно!")
        page.wait_for_timeout(1300)
        check("REQ-FORMS-04 a correct answer advances by itself", page.inner_text("#fm-counter"),
              predicate=lambda s: "Упражнение 2 из 10" in s)

        # старое сохранённое состояние без новых счётчиков не должно ломать вкладку
        page.evaluate("""() => localStorage.setItem('il-malti-v1',
          JSON.stringify({items:{},stats:{word:{ok:1,no:0},sent:{ok:0,no:0}},days:{}}))""")
        page.reload()
        page.click('.tab[data-tab="forms"]')
        check("REQ-SHELL-02 state from an older version still works", page.inner_text("#fm-counter"),
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
        check("REQ-SENT-04 нашли фразу из трёх и более разных слов",
              plan is not None, True)
        # строим верный порядок, но меняем местами первые два слова — ошибка гарантирована
        order = plan["idx"][:]
        order[0], order[1] = order[1], order[0]
        for i in order:
            page.locator("#s-chips .chip").nth(i).click()
        page.click("#s-check")
        check("REQ-SENT-07 a wrong sentence is reported", page.inner_text("#s-feedback"),
              predicate=lambda s: s.startswith("Не так"))
        check("REQ-SENT-07 the diff block appears", page.locator("#s-diff").is_hidden(), False)
        diff = page.inner_text("#s-diff")
        check("REQ-SENT-07 the diff shows both answers", diff,
              predicate=lambda s: "твой ответ" in s and "правильно" in s)
        check("REQ-SENT-07 the diff counts the mismatches", diff,
              predicate=lambda s: "Расхождений" in s)
        page.click("#s-next")
        check("REQ-SENT-07 the diff is cleared for the next sentence",
              page.locator("#s-diff").is_hidden(), True)
        page.select_option("#s-limit", "5")

        # --- «Заполнить пропуски»: форма в живом предложении ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.click('.tab[data-tab="sentences"]')
        check("REQ-BLANK-01 предложений четыре режима",
              page.locator("#s-mode option").count(), 4)
        page.select_option("#s-mode", "blanks")
        check("REQ-BLANK-01 режим пропусков виден", page.locator("#s-blanks").is_hidden(), False)
        check("REQ-BLANK-01 в подписи сказано определить лицо", page.inner_text("#s-prompt-label"),
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
        check("REQ-BLANK-01 упражнение найдено в данных", data is not None, True)
        check("REQ-BLANK-01 в предложении столько же пропусков",
              page.locator("#s-ru .blank-slot").count(), data["blanks"])
        check("REQ-BLANK-01 на каждый пропуск своя строка вариантов",
              page.locator("#s-blank-rows .quiz-options").count(), data["blanks"])
        check("REQ-BLANK-02 у каждого пропуска три варианта", page.evaluate("""() =>
              [...document.querySelectorAll('#s-blank-rows .quiz-options')]
                .every(r => r.querySelectorAll('.opt').length === 3)"""), True)
        check("REQ-BLANK-02 варианты внутри пропуска не повторяются", page.evaluate("""() =>
              [...document.querySelectorAll('#s-blank-rows .quiz-options')]
                .every(r => { const v = [...r.querySelectorAll('.opt')].map(o => o.dataset.value);
                              return new Set(v).size === v.length; })"""), True)
        check("REQ-BLANK-02 верный вариант есть среди предложенных", page.evaluate("""(answers) =>
              [...document.querySelectorAll('#s-blank-rows .quiz-options')]
                .every((r, i) => [...r.querySelectorAll('.opt')]
                  .some(o => o.dataset.value === answers[i]))""", data["answers"]), True)
        # подписи берём из данных, чтобы не зависеть от того, глагол это или существительное
        labels = page.evaluate("() => Object.values(window.BLANK_LABELS)")
        check("REQ-BLANK-03 подсказка о форме в вопросе НЕ показана",
              any(l in page.inner_text("#s-blank-rows") for l in labels), False)

        page.click("#s-check")
        check("REQ-BLANK-04 незаполненные пропуски не принимаются", page.inner_text("#s-feedback"),
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
        check("REQ-BLANK-04 неверный ответ посчитан по пропускам", page.inner_text("#s-feedback"),
              predicate=lambda s: s.startswith("Неверно: пропусков с ошибкой — 1 из"))
        check("REQ-BLANK-04 верные варианты подсвечены", page.locator("#s-blank-rows .opt.ok").count(),
              data["blanks"])
        check("REQ-BLANK-04 неверный вариант зачёркнут", page.locator("#s-blank-rows .opt.bad").count(), 1)
        check("REQ-BLANK-04 пропуски в предложении подсвечены",
              page.locator("#s-ru .blank-slot.ok").count() + page.locator("#s-ru .blank-slot.bad").count(),
              data["blanks"])
        answer_text = page.inner_text("#s-blank-answer")
        check("REQ-BLANK-05 разбор показывает полную фразу", answer_text, predicate=lambda s: data["full"] in s)
        check("REQ-BLANK-05 разбор показывает перевод", answer_text, predicate=lambda s: data["ru"] in s)
        check("REQ-BLANK-05 разбор называет форму", answer_text,
              predicate=lambda s: any(l in s for l in labels))
        check("REQ-BLANK-05 разбор объясняет каждую подстановку", answer_text,
              predicate=lambda s: s.count("→") >= data["blanks"])
        check("REQ-TR-04 разбор даёт транскрипцию", page.inner_text("#s-translit"),
              predicate=lambda s: "[" in s)
        check("REQ-SENT-09 после ответа есть кнопка «Дальше»",
              page.locator("#s-forward").is_hidden(), False)

        # верный ответ уходит сам
        before = page.inner_text("#s-counter").split("·")[0]
        page.click("#s-forward")
        check("REQ-SENT-09 «Дальше» уводит к следующей фразе",
              page.inner_text("#s-counter").split("·")[0] != before, True)
        check("REQ-SENT-09 на новой фразе «Дальше» снова скрыта",
              page.locator("#s-forward").is_hidden(), True)
        check("REQ-BLANK-06 подсказка в режиме пропусков подписана внятно",
              page.inner_text("#s-reveal"), "Показать ответ")
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
        check("REQ-SENT-04 все верные ответы принимаются", page.inner_text("#s-feedback"), "Верно!")
        page.wait_for_timeout(1300)
        check("REQ-BLANK-06 верный ответ уводит к следующей фразе",
              page.inner_text("#s-counter").split("·")[0] != before, True)
        check("REQ-BLANK-06 на новой фразе пропуски снова пустые",
              page.locator("#s-ru .blank-slot.ok").count() +
              page.locator("#s-ru .blank-slot.bad").count(), 0)

        # --- диалоги: фразы в контексте ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.click('.tab[data-tab="dialogues"]')
        check("REQ-DLG-01 диалоги загружены", page.locator("#dg-pick option").count(),
              predicate=lambda n: n >= 5)
        check("REQ-DLG-03 три режима диалогов", page.locator("#dg-mode option").count(), 3)
        check("REQ-DLG-01 у каждого диалога есть заголовок и реплики", page.evaluate("""() =>
              window.DIALOGUES.every(d => d.title && d.lines && d.lines.length >= 3)"""), True)
        check("REQ-DLG-01 у каждой реплики есть мальтийский и перевод", page.evaluate("""() =>
              window.DIALOGUES.every(d => d.lines.every(l =>
                l.mt && l.mt.trim() && l.ru && l.ru.trim()))"""), True)
        check("REQ-DLG-01 внутри диалога переводы не повторяются", page.evaluate("""() =>
              window.DIALOGUES.every(d => {
                const r = d.lines.map(l => l.ru);
                return new Set(r).size === r.length;
              })"""), True)
        check("REQ-DLG-01 идентификаторы диалогов уникальны", page.evaluate("""() => {
              const ids = window.DIALOGUES.map(d => d.id);
              return new Set(ids).size === ids.length;
            }"""), True)
        check("REQ-DLG-01 в каждом диалоге есть обе стороны", page.evaluate("""() =>
              window.DIALOGUES.every(d => {
                const who = new Set(d.lines.map(l => l.who));
                return who.size === 2;
              })"""), True)

        # чтение
        lines = page.locator("#dg-body .dlg-line").count()
        check("REQ-DLG-02 в режиме чтения видны все реплики", lines,
              predicate=lambda n: n >= 4)
        check("REQ-DLG-02 перевод виден", page.locator("#dg-body .dlg-ru").count(), lines)
        page.check("#dg-hide")
        check("REQ-DLG-02 перевод скрывается по переключателю", page.evaluate("""() =>
              [...document.querySelectorAll('#dg-body .dlg-ru')]
                .every(x => getComputedStyle(x).visibility === 'hidden')"""), True)
        page.uncheck("#dg-hide")

        # перевод по репликам
        page.select_option("#dg-mode", "drill")
        total = page.locator("#dg-pick option").count()
        check("REQ-DLG-03 в тренировке одна реплика", page.locator("#dg-body .card-main").count(), 1)
        check("REQ-DLG-03 перевод скрыт до нажатия", page.locator("#dg-ru").is_hidden(), True)
        check("REQ-DLG-03 кнопки оценки скрыты до нажатия", page.locator("#dg-grade").is_hidden(), True)
        page.click("#dg-reveal")
        check("REQ-DLG-03 перевод показывается", page.locator("#dg-ru").is_hidden(), False)
        check("REQ-TR-04 транскрипция показывается", page.inner_text("#dg-tr"),
              predicate=lambda s: "[" in s)
        check("REQ-SENT-06 кнопки оценки появились", page.locator("#dg-grade").is_hidden(), False)
        before = page.inner_text("#dg-counter")
        page.click("#dg-yes")
        check("REQ-DLG-03 оценка отмечена", page.inner_text("#dg-feedback"),
              predicate=lambda s: "знаю" in s)
        page.wait_for_timeout(1300)
        check("REQ-DLG-03 после оценки идём дальше", page.inner_text("#dg-counter") != before, True)

        # выбор ответа
        page.select_option("#dg-mode", "reply")
        check("REQ-DLG-04 показана предыдущая реплика", page.locator("#dg-body .dlg-prev").count(), 1)
        check("REQ-DLG-04 вариантов ответа три", page.locator("#dg-options .opt-sentence").count(), 3)
        check("REQ-DLG-04 есть верный вариант среди них", page.evaluate("""() => {
              const d = window.DIALOGUES[0];
              const pairs = [];
              d.lines.forEach((l, i) => { if (i > 0 && l.who !== d.lines[i-1].who) pairs.push(i); });
              const right = d.lines[pairs[0]].mt;
              return [...document.querySelectorAll('#dg-options .opt-sentence')]
                .some(o => o.textContent === right);
            }"""), True)
        page.locator("#dg-options .opt-sentence").first.click()
        check("REQ-DLG-04 выбор ответа проверяется", page.inner_text("#dg-feedback"),
              predicate=lambda s: len(s) > 0)
        check("REQ-DLG-04 подсвечен ровно один верный вариант",
              page.locator("#dg-options .ok").count(), 1)
        check("REQ-DLG-04 после ответа есть «Дальше»", page.locator("#dg-forward").is_hidden(), False)

        # прогресс учитывает диалоги
        page.click('.tab[data-tab="progress"]')
        sets = [x.replace("\n", " ") for x in page.evaluate(
            "() => [...document.querySelectorAll('#p-sets .set-row')].map(r => r.innerText)")]
        check("REQ-PROG-03 в прогрессе есть набор «Диалоги»",
              [x for x in sets if x.startswith("Диалоги")], predicate=lambda v: len(v) == 1)
        kinds = [x.replace("\n", " ") for x in page.evaluate(
            "() => [...document.querySelectorAll('#p-kinds .set-row')].map(r => r.innerText)")]
        check("REQ-PROG-04 ответы в диалогах учтены",
              [x for x in kinds if x.startswith("Диалоги") and "ответов: " in x],
              predicate=lambda v: len(v) == 1)

        # --- alphabet ---        # --- alphabet ---
        page.click('.tab[data-tab="alphabet"]')
        check("REQ-ALPHA-01 alphabet cells", page.locator("#alpha-grid .alpha-cell").count(), 30)
        check("REQ-ALPHA-02 alphabet copy keys", page.locator("#copy-kbd .key").count(), 11)
        check("REQ-TR-05 transcription legend rows", page.locator("#view-alphabet .legend li").count(), 6)

        # --- progress ---
        page.click('.tab[data-tab="progress"]')
        check("REQ-PROG-01 stat cards", page.locator("#p-stats .stat").count(), 6)
        check("REQ-PROG-02 box rows", page.locator("#p-boxes .box-row").count(), 7)
        check("REQ-PROG-03 progress rows per exercise set", page.locator("#p-sets .set-row").count(), 8)
        check("REQ-PROG-04 answer rows per mode", page.locator("#p-kinds .set-row").count(), 5)
        check("REQ-PROG-05 day rows", page.locator("#p-days .box-row").count(), 7)

        # --- reset ---
        page.on("dialog", lambda d: d.accept())
        page.click("#p-reset")
        page.wait_for_timeout(300)
        cleared = page.evaluate("() => localStorage.getItem('il-malti-v1')")
        check("REQ-SHELL-02 reset clears progress", cleared, predicate=lambda s: s and '"items":{}' in s)
        check("REQ-SHELL-02 stats reset", page.inner_text("#p-stats"), predicate=lambda s: "0%" in s)

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
        check("REQ-PROG-04 ответ из «Форм» попал в «Всего ответов»", stats,
              predicate=lambda s: "1\nВсего ответов" in s)
        check("REQ-PROG-04 точность считается по всем режимам", stats,
              predicate=lambda s: "100%\nТочность" in s)
        kinds = [x.replace("\n", " ") for x in page.evaluate(
            "() => [...document.querySelectorAll('#p-kinds .set-row')].map(r => r.innerText)")]
        check("REQ-PROG-04 ответ учтён в счётчике своего режима",
              [k for k in kinds if k.startswith("Согласование") and "ответов: 1" in k],
              predicate=lambda v: len(v) == 1)
        check("REQ-PROG-04 нулевые счётчики остались нулевыми",
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
        check("REQ-PROG-02 новых слов осталось на одно меньше", boxes.get("Не начатые"), total_words - 1)
        check("REQ-PROG-02 проваленное слово попало в коробку 0",
              boxes.get("Коробка 0 (проваленные)"), 1)
        check("REQ-PROG-02 строк в гистограмме — семь", len(boxes), 7)
        check("REQ-PROG-02 «Слов начато» учитывает провал", page.inner_text("#p-stats"),
              predicate=lambda s: "1 из %d\nСлов начато" % total_words in s)

        # (3) у каждого набора упражнений виден свой прогресс
        sets = [x.replace("\n", " ") for x in page.evaluate(
            "() => [...document.querySelectorAll('#p-sets .set-row')].map(r => r.innerText)")]
        check("REQ-PROG-03 прогресс показан по всем наборам", len(sets), 8)
        check("REQ-PROG-03 у наборов видны начатые и «далее»",
              all("начато:" in x and "далее:" in x and "к повторению:" in x for x in sets), True)

        # (4) слово со сроком возвращается и показывается РАНЬШЕ новых
        import json as _json
        due_state = {"items": {"w:" + failed_word: {"b": 2, "d": 0, "f": 0}},
                     "stats": {}, "days": {}}
        page.evaluate("s => localStorage.setItem('il-malti-v1', s)", _json.dumps(due_state))
        page.reload()
        page.click('.tab[data-tab="words"]')
        check("REQ-WORDS-02 слово со сроком стоит первым в очереди", page.inner_text("#w-front"), failed_word)
        check("REQ-WORDS-02 в очереди есть и новые слова", page.inner_text("#w-counter"),
              predicate=lambda s: int(s.split("В очереди: ")[1].split(" ")[0]) > 1)

        # (5) когда всё выучено и срок далёкий — очередь пуста, видно когда повторение
        all_ids = page.evaluate("() => window.WORDS.map(w => 'w:' + w.mt)")
        page.evaluate("s => localStorage.setItem('il-malti-v1', s)",
                      _json.dumps({"items": {uid: {"b": 5, "d": 99999, "f": 0} for uid in all_ids},
                                   "stats": {}, "days": {}}))
        page.reload()
        page.click('.tab[data-tab="words"]')
        check("REQ-WORDS-06 когда повторять нечего — блок «на сегодня всё»",
              page.locator("#w-done").is_visible(), True)
        check("REQ-WORDS-06 видно, когда следующее повторение", page.inner_text("#w-done-text"),
              predicate=lambda s: "Следующее повторение" in s and "через" in s)
        page.click('.tab[data-tab="progress"]')
        check("REQ-PROG-02 прогресс видит, что начаты все слова", page.inner_text("#p-stats"),
              predicate=lambda s: "%d из %d\nСлов начато" % (total_words, total_words) in s)
        check("REQ-PROG-02 далёкие слова не числятся к повторению", page.inner_text("#p-stats"),
              predicate=lambda s: "0\nСлов к повторению сейчас" in s)

        # вернуть чистое состояние для следующих блоков
        page.evaluate("() => localStorage.clear()")
        page.reload()

        # --- daily new-word limit and the "all done" state ---
        page.click('.tab[data-tab="words"]')
        check("REQ-WORDS-01 queue rebuilt after reset", page.inner_text("#w-counter"),
              predicate=lambda s: "В очереди: 10" in s and "0/10" in s)
        page.select_option("#w-limit", "5")
        check("REQ-WORDS-01 changing the limit rebuilds the queue", page.inner_text("#w-counter"),
              predicate=lambda s: "В очереди: 5" in s and "0/5" in s)

        for _ in range(5):
            page.click("#w-show")
            page.click("#w-yes")
        check("REQ-WORDS-06 done block appears when the day is finished",
              page.locator("#w-done").is_visible(), True)
        check("REQ-WORDS-06 card is hidden in the done state",
              page.locator("#w-card").is_visible(), False)
        done_text = page.inner_text("#w-done-text")
        check("REQ-WORDS-06 done text reports today's new words and next review", done_text,
              predicate=lambda s: "Новых сегодня: 5 из 5" in s and "Следующее повторение" in s)

        page.click("#w-bypass")
        check("REQ-WORDS-06 bypass shows the remaining new words", page.inner_text("#w-counter"),
              predicate=lambda s: "сверх лимита" in s and "В очереди: " in s)
        check("REQ-WORDS-06 card is back after bypass", page.locator("#w-card").is_visible(), True)
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
        check("REQ-WORDS-03 queue keeps only the failed word", page.inner_text("#w-counter"),
              predicate=lambda s: "В очереди: 1" in s and "новых сегодня: 5/5" in s)
        check("REQ-WORDS-03 the failed word returned", page.inner_text("#w-front"), failed_first)
        page.click("#w-show")
        page.click("#w-yes")
        check("REQ-WORDS-03 day finishes once the failed word is learned",
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
        check("REQ-PROG-04 sentence answers are recorded", sent_records, 3)
        page.click('.tab[data-tab="words"]')
        check("REQ-WORDS-08 sentences do not consume the new-word budget", page.inner_text("#w-counter"),
              predicate=lambda s: "В очереди: 10" in s and "новых сегодня: 0/10" in s)

        browser.close()

    if httpd:
        httpd.shutdown()

    check("REQ-SHELL-04 console errors", console_errors, [])

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
