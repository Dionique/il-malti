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
        check("words topic options", page.locator("#w-topic option").count(), 17)
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
        check("few phrases open on a fresh start", page.inner_text("#s-counter"),
              predicate=lambda s: "открыто фраз: 8 из 269" in s)
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

        # type mode hides the new words, special keys insert characters
        page.select_option("#s-mode", "type")
        check("type mode visible", page.locator("#s-type").is_hidden(), False)
        check("new words hidden in type mode", page.inner_text("#s-known"),
              predicate=lambda s: "нажми" in s)
        check("special keys count", page.locator("#s-kbd .key").count(), 11)
        page.locator("#s-kbd .key").first.click()
        check("key inserted into input", page.input_value("#s-input"), predicate=lambda v: v == "\u010b")

        # card mode reveals the new words together with the answer
        page.select_option("#s-mode", "card")
        check("card shows maltese", page.inner_text("#s-mt"), predicate=lambda s: len(s.strip()) > 0)
        page.click("#s-reveal")
        check("card grade visible", page.locator("#s-grade").is_hidden(), False)
        check("new words revealed with the answer", page.inner_text("#s-known"),
              predicate=lambda s: "Новые слова" in s)
        page.click("#s-yes")

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
              predicate=lambda s: "Фраза 1 из 8" in s)
        failed = page.inner_text("#s-mt")
        page.click("#s-reveal")
        page.click("#s-no")
        for _ in range(7):
            page.click("#s-reveal")
            page.click("#s-yes")
        check("failed phrase returned", page.inner_text("#s-counter"),
              predicate=lambda s: "из 1" in s)
        check("it is the same phrase", page.inner_text("#s-mt"), failed)
        page.click("#s-reveal")
        page.click("#s-yes")
        check("phrases done for today", page.locator("#s-done").is_visible(), True)
        check("done text reports new phrases", page.inner_text("#s-done-text"),
              predicate=lambda s: "Новых фраз сегодня: 8" in s)

        # --- learning the vocabulary opens more phrases ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.click('.tab[data-tab="sentences"]')
        check("8 phrases open with no vocabulary", page.inner_text("#s-counter"),
              predicate=lambda s: "открыто фраз: 8 из 269" in s)
        linked = page.evaluate(
            "() => [...new Set(Object.values(window.SENTENCE_LINKS).flatMap(v => v.words))]"
        )
        check("phrases use a subset of the vocabulary", len(linked),
              predicate=lambda n: 100 < n < 304)
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
              predicate=lambda s: "открыто фраз: 269 из 269" in s)

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
            check("%s: a translation question is present" % mode,
                  page.evaluate("""() => {
                    const cyr = /[а-яё]/i;
                    return [...document.querySelectorAll('#fm-quiz .quiz-options')].some(b =>
                      [...b.querySelectorAll('.opt')].some(o => cyr.test(o.textContent)));
                  }"""), True)
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

        # --- разбор ошибок в предложениях ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.click('.tab[data-tab="sentences"]')
        page.select_option("#s-mode", "type")
        page.locator("#s-input").fill("Ħażin ħafna kliem")
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

        # --- alphabet ---        # --- alphabet ---
        page.click('.tab[data-tab="alphabet"]')
        check("alphabet cells", page.locator("#alpha-grid .alpha-cell").count(), 30)
        check("alphabet copy keys", page.locator("#copy-kbd .key").count(), 11)
        check("transcription legend rows", page.locator("#view-alphabet .legend li").count(), 6)

        # --- progress ---
        page.click('.tab[data-tab="progress"]')
        check("stat cards", page.locator("#p-stats .stat").count(), 8)
        check("box rows", page.locator("#p-boxes .box-row").count(), 6)
        check("day rows", page.locator("#p-days .box-row").count(), 7)

        # --- reset ---
        page.on("dialog", lambda d: d.accept())
        page.click("#p-reset")
        page.wait_for_timeout(300)
        cleared = page.evaluate("() => localStorage.getItem('il-malti-v1')")
        check("reset clears progress", cleared, predicate=lambda s: s and '"items":{}' in s)
        check("stats reset", page.inner_text("#p-stats"), predicate=lambda s: "0%" in s)

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
