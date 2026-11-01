import { appendFileSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "fs"
import { exec } from "child_process"
import { join } from "path"
import type { Plugin } from "@opencode-ai/plugin"

// ── Настройки ────────────────────────────────────────────────────────────────
// Сколько раз плагин сам подкидывает агенту «продолжай» (то есть максимум
// столько же дополнительных ответов сверх первого).
const MAX_ITERATIONS = 5
// Жёсткий предел по времени на весь цикл: сколько бы итераций ни осталось,
// после этого срока цикл останавливается.
const MAX_MINUTES = 60
// Предел на одну проверку внутри приёмки (smoke.py гоняет реальный браузер).
const CHECK_TIMEOUT_SECONDS = 600

const COMMANDS = ["ralph-loop", "loop"]
const CANCEL_COMMAND = "cancel-ralph"
const AGENT = "ralph"
const COMPLETION_TAG = /<promise>\s*DONE\s*<\/promise>/is
const TAG = "<promise>DONE</promise>"

// Единственный законный повод закончить цикл — эти три команды зелёные.
const CHECKS = [
  "python3 tools/check_specs.py",
  "python3 tools/make_forms.py --check",
  "python3 tests/smoke.py",
]

// ── Состояние и журнал: один файл на чат ─────────────────────────────────────
// Ключ — sessionID, поэтому два чата в одном проекте не мешают друг другу,
// а закрытие одного чата не трогает цикл в другом.

type RalphState = {
  active: boolean
  iteration: number
  maxIterations: number
  task: string
  createdAt: number
  deadline: number
}

const STATE_DIR = join(".opencode", "ralph")

function statePath(directory: string, sessionID: string): string {
  return join(directory, STATE_DIR, `${sessionID}.json`)
}

function readState(directory: string, sessionID: string): RalphState | null {
  try {
    const file = statePath(directory, sessionID)
    if (!existsSync(file)) return null
    return JSON.parse(readFileSync(file, "utf-8")) as RalphState
  } catch {
    // Прочитать не смогли — считаем, что цикла нет. Это безопасная сторона:
    // цикл просто не продолжается, наружу ничего не летит.
    return null
  }
}

function writeState(directory: string, sessionID: string, state: RalphState): boolean {
  try {
    mkdirSync(join(directory, STATE_DIR), { recursive: true })
    writeFileSync(statePath(directory, sessionID), JSON.stringify(state, null, 2))
    return true
  } catch {
    // Опасная сторона: без записанного счётчика лимит не сработает.
    // Поэтому вызывающий обязан считать false поводом немедленно остановиться.
    return false
  }
}

function clearState(directory: string, sessionID: string): void {
  try {
    rmSync(statePath(directory, sessionID), { force: true })
  } catch {
    // Файл не удалился. Не беда: на следующем простое счётчик снова упрётся
    // в лимит (или снова найдётся тег) до всякой инъекции — цикл не пойдёт.
  }
}

// Журнал решений цикла. Пишется «как получится»: если запись не удалась,
// на работу цикла это не влияет — в отличие от файла состояния.
function journal(directory: string, sessionID: string, level: "INFO" | "WARN" | "ERROR", message: string, extra?: any): void {
  try {
    mkdirSync(join(directory, STATE_DIR), { recursive: true })
    const tail = extra ? ` ${JSON.stringify(extra)}` : ""
    appendFileSync(join(directory, STATE_DIR, "history.log"), `${new Date().toISOString()} ${level} ${sessionID} ${message}${tail}\n`)
  } catch {}
}

// ── Вспомогательное ──────────────────────────────────────────────────────────

// Тост — не блокирующая побочная операция: без TUI (в `opencode run`) запрос
// может вовсе не ответить, и тогда `await` повесил бы обработку цикла.
function toast(client: any, directory: string, variant: string, message: string): void {
  try {
    Promise.resolve(client.tui.showToast({ query: { directory }, body: { message, variant } })).catch(() => {})
  } catch {}
}

async function fetchMessages(client: any, sessionID: string, directory: string): Promise<any[]> {
  try {
    const res = await client.session.messages({ path: { id: sessionID }, query: { directory } })
    return (res?.data ?? []) as any[]
  } catch {
    return []
  }
}

function assistantText(message: any): string {
  return (message?.parts ?? [])
    .filter((p: any) => p?.type === "text")
    .map((p: any) => p.text ?? "")
    .join("\n")
}

// Проверки запускаем через Node child_process: он асинхронный (не морозит
// сервер) и сам убивает процесс по таймауту. Bun-оболочка `$` из плагина в
// этой версии opencode просто не отвечает, поэтому от неё отказались.
function run(cmd: string, cwd: string): Promise<number> {
  return new Promise((resolve) => {
    exec(
      cmd,
      { cwd, timeout: CHECK_TIMEOUT_SECONDS * 1000, killSignal: "SIGKILL", maxBuffer: 64 * 1024 * 1024 },
      (err: any) => resolve(err ? (typeof err.code === "number" ? err.code : 1) : 0),
    )
  })
}

async function runChecks(directory: string): Promise<{ ok: boolean; failed: string[] }> {
  const failed: string[] = []
  for (const cmd of CHECKS) {
    try {
      if ((await run(cmd, directory)) !== 0) failed.push(cmd)
    } catch {
      failed.push(cmd)
    }
  }
  return { ok: failed.length === 0, failed }
}

function startPrompt(task: string): string {
  return [
    `Задача Ralph-loop: ${task}`,
    ``,
    `Работай по правилам агента ${AGENT}. Критерий готовности — зелёные проверки:`,
    ...CHECKS.map((c) => `- ${c}`),
    ``,
    `Когда задача выполнена и проверки зелёные, выведи ровно строку ${TAG}.`,
    `Раньше — не выводи: плагин всё равно прогонит проверки сам и не примет тег.`,
  ].join("\n")
}

function continuationPrompt(state: RalphState, note: string): string {
  return [
    `[RALPH LOOP — итерация ${state.iteration}/${state.maxIterations}]`,
    ``,
    `Продолжай задачу с того места, где остановился: ${state.task}`,
    note ? `\n${note}\n` : "",
    `Критерий готовности: ${CHECKS.join(" · ")}.`,
    `Когда всё зелёно и задача выполнена — выведи ровно ${TAG}.`,
  ].join("\n")
}

// ── Плагин ───────────────────────────────────────────────────────────────────

export const RalphPlugin: Plugin = async ({ client, directory }) => {
  return {
    // Команды регистрируем сами, чтобы всё жило в одном файле.
    // Если пользователь определил такие же в конфиге — его запись главнее.
    config: async (input: any) => {
      input.command = input.command ?? {}
      for (const name of COMMANDS) {
        if (input.command[name]) continue
        input.command[name] = {
          description: "Ralph-loop: до 5 итераций, тег DONE принимается только после зелёных проверок",
          agent: AGENT,
          template: `Задача Ralph-loop: $ARGUMENTS`,
        }
      }
      if (!input.command[CANCEL_COMMAND]) {
        input.command[CANCEL_COMMAND] = {
          description: "Остановить Ralph-loop в этом чате",
          agent: AGENT,
          template: "Ralph-loop остановлен. Ничего не делай, просто подтверди одной строкой.",
        }
      }
    },

    // Запуск и отмена цикла. Хук знает sessionID, поэтому состояние пишется
    // детерминированно, до первого хода агента, без bash-heredoc.
    "command.execute.before": async (input: any, output: any) => {
      const name = input?.command
      const sessionID: string | undefined = input?.sessionID
      if (!sessionID) return

      if (name === CANCEL_COMMAND) {
        clearState(directory, sessionID)
        journal(directory, sessionID, "INFO", "cancel")
        output.parts = [
          { type: "text", text: "Ralph-loop остановлен для этого чата. Ничего не делай, просто подтверди одной строкой." },
        ]
        return
      }

      if (!COMMANDS.includes(name)) return

      const task = String(input?.arguments ?? "").trim()
      const now = Date.now()
      const state: RalphState = {
        active: true,
        iteration: 0,
        maxIterations: MAX_ITERATIONS,
        task,
        createdAt: now,
        deadline: now + MAX_MINUTES * 60_000,
      }

      if (!writeState(directory, sessionID, state)) {
        journal(directory, sessionID, "ERROR", "start failed: state file not writable", { path: statePath(directory, sessionID) })
        toast(client, directory, "error", "Ralph: не удалось записать состояние — цикл НЕ запущен")
        output.parts = [
          {
            type: "text",
            text: `Ralph-loop НЕ запущен: не удалось записать файл состояния (${statePath(directory, sessionID)}). Не выполняй задачу автономно и сообщи об ошибке одной строкой.`,
          },
        ]
        return
      }

      journal(directory, sessionID, "INFO", "start", { maxIterations: MAX_ITERATIONS, maxMinutes: MAX_MINUTES, task })
      toast(client, directory, "info", `Ralph: цикл запущен, до ${MAX_ITERATIONS} итераций`)
      output.parts = [{ type: "text", text: startPrompt(task) }]
    },

    event: async ({ event }: any) => {
      const sessionID: string | undefined = event?.properties?.sessionID
      if (!sessionID) return

      if (event.type === "session.deleted") {
        clearState(directory, sessionID)
        return
      }
      if (event.type !== "session.idle") return

      const state = readState(directory, sessionID)
      if (!state?.active) return

      if (Date.now() > state.deadline) {
        clearState(directory, sessionID)
        journal(directory, sessionID, "WARN", "stop: deadline", { iteration: state.iteration, maxMinutes: MAX_MINUTES })
        toast(client, directory, "warning", `Ralph: прошло ${MAX_MINUTES} мин — цикл остановлен по времени`)
        return
      }

      // `session.idle` приходит дублями. Если последнее сообщение — наше
      // продолжение, значит агент ещё не ответил и второй раз продолжать нельзя:
      // иначе один ход агента съедает две итерации.
      const messages = await fetchMessages(client, sessionID, directory)
      const last = messages[messages.length - 1]
      if (!last || last?.info?.role !== "assistant") {
        journal(directory, sessionID, "INFO", "skip: awaiting assistant reply")
        return
      }

      // Заявление о готовности не принимаем на слово: гоняем проверки сами.
      let note = ""
      const text = assistantText(last)
      if (COMPLETION_TAG.test(text)) {
        journal(directory, sessionID, "INFO", "tag DONE claimed, verifying", { iteration: state.iteration })
        toast(client, directory, "info", "Ralph: модель говорит DONE — проверяю тестами…")
        journal(directory, sessionID, "INFO", "verifying: running checks")
        const checks = await runChecks(directory)
        journal(directory, sessionID, "INFO", "verifying: finished", { ok: checks.ok, failed: checks.failed })
        if (checks.ok) {
          clearState(directory, sessionID)
          journal(directory, sessionID, "INFO", "stop: done, checks green", { iteration: state.iteration })
          toast(client, directory, "success", "Ralph: цель достигнута, проверки зелёные — цикл закрыт")
          return
        }
        note = `В прошлый раз ты вывел ${TAG}, но проверки не прошли: ${checks.failed.join(", ")}. Тег не засчитан — доведи до зелёного.`
        journal(directory, sessionID, "WARN", "tag DONE rejected: checks failed", { failed: checks.failed })
        toast(client, directory, "warning", `Ralph: тег не принят, провалены: ${checks.failed.join(", ")}`)
      }

      if (state.iteration >= state.maxIterations) {
        clearState(directory, sessionID)
        journal(directory, sessionID, "WARN", "stop: iteration limit", { iteration: state.iteration })
        toast(client, directory, "warning", `Ralph: лимит ${state.maxIterations} итераций исчерпан — цикл остановлен`)
        return
      }

      // Сначала записываем счётчик, и только потом продолжаем. Если запись не
      // удалась — лимит перестаёт быть надёжным, поэтому останавливаемся.
      const next: RalphState = { ...state, iteration: state.iteration + 1 }
      if (!writeState(directory, sessionID, next)) {
        clearState(directory, sessionID)
        journal(directory, sessionID, "ERROR", "stop: state write failed", { iteration: next.iteration })
        toast(client, directory, "error", "Ralph: не удалось записать состояние — цикл остановлен")
        return
      }

      journal(directory, sessionID, "INFO", "continue", { iteration: next.iteration, maxIterations: next.maxIterations })
      try {
        await client.session.prompt({
          path: { id: sessionID },
          body: { parts: [{ type: "text", text: continuationPrompt(next, note) }] },
        })
      } catch {
        clearState(directory, sessionID)
        journal(directory, sessionID, "ERROR", "stop: session.prompt failed", { iteration: next.iteration })
        toast(client, directory, "error", "Ralph: не удалось продолжить сессию — цикл остановлен")
      }
    },
  }
}
