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
              predicate=lambda s: "открыто фраз: 8 из 270" in s)
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
              predicate=lambda s: "открыто фраз: 8 из 270" in s)
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
              predicate=lambda s: "открыто фраз: 270 из 270" in s)

        # --- noun + verb mode ---
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.click('.tab[data-tab="pairs"]')
        check("pairs queue respects the daily limit", page.inner_text("#pr-counter"),
              predicate=lambda s: "Сочетание 1 из 10" in s and "0/10" in s)
        check("the pair is shown as noun + verb",
              page.inner_text("#pr-noun") + " + " + page.inner_text("#pr-verb"),
              predicate=lambda s: " + " in s and len(s) > 4)
        check("gender options", page.locator("#pr-gender .opt").count(), 3)
        check("verb form options", page.locator("#pr-form .opt").count(), 3)
        check("translation options", page.locator("#pr-ru .opt").count(), 3)
        page.click("#pr-check")
        check("an incomplete answer is rejected", page.inner_text("#pr-feedback"),
              predicate=lambda s: "все три" in s)

        # deliberately wrong answer on every row
        for row in ("#pr-gender", "#pr-form", "#pr-ru"):
            page.locator(row + " .opt").first.click()
        page.click("#pr-check")
        check("a wrong answer is reported", page.inner_text("#pr-feedback"),
              predicate=lambda s: s.startswith("Неверно") or s == "Разбор ниже")
        check("the correct options are highlighted",
              page.locator("#pr-gender .opt.ok").count(), 1)
        check("the full sentence is shown", page.inner_text("#pr-answer"),
              predicate=lambda s: len(s.split("\n")) >= 2)
        check("the sentence has a transcription", page.inner_text("#pr-translit"),
              predicate=lambda s: "[" in s)
        check("a next button appears after a wrong answer",
              page.locator("#pr-next").is_hidden(), False)
        page.click("#pr-next")
        check("the pair counter advances", page.inner_text("#pr-counter"),
              predicate=lambda s: "Сочетание 2 из 10" in s and "1/10" in s)

        # correct answer advances on its own
        page.evaluate("() => localStorage.clear()")
        page.reload()
        page.click('.tab[data-tab="pairs"]')
        correct = page.evaluate("""() => {
          const subject = document.getElementById('pr-noun').textContent;
          const verbMt = document.getElementById('pr-verb').textContent;
          const p = window.PAIRS.find(x => x.subject === subject && x.verbMt === verbMt);
          return p ? { gender: p.gender, form: p.form, ru: p.ru } : null;
        }""")
        check("the shown pair exists in the data", correct is not None, True)
        page.locator('#pr-gender .opt[data-val="%s"]' % correct["gender"]).click()
        page.locator('#pr-form .opt[data-val="%s"]' % correct["form"]).click()
        page.locator('#pr-ru .opt[data-val="%s"]' % correct["ru"]).click()
        page.click("#pr-check")
        check("a fully correct answer is accepted", page.inner_text("#pr-feedback"), "Верно!")
        page.wait_for_timeout(1300)
        check("a correct answer advances by itself", page.inner_text("#pr-counter"),
              predicate=lambda s: "Сочетание 2 из 10" in s)

        # old saved state without the "pair" bucket must not break anything
        page.evaluate("""() => localStorage.setItem('il-malti-v1',
          JSON.stringify({items:{},stats:{word:{ok:1,no:0},sent:{ok:0,no:0}},days:{}}))""")
        page.reload()
        page.click('.tab[data-tab="pairs"]')
        check("state saved by an older version still works", page.inner_text("#pr-counter"),
              predicate=lambda s: "Сочетание 1" in s)

        # --- alphabet ---
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
