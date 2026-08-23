import { useEffect, useRef, useState, type FormEvent } from "react";
import type { Agent, LogEntry, LogLevel } from "../types";

const LEVEL_STYLE: Record<LogLevel, string> = {
  info: "text-slate-400",
  action: "text-fuchsia-400",
  observation: "text-emerald-400",
  success: "text-violet-200",
  error: "text-red-400",
};

const PREFIX: Record<LogLevel, string> = {
  info: "\u00BB",
  action: "\u25B8",
  observation: "\u25C2",
  success: "\u2713",
  error: "\u2715",
};

interface TaskRunnerProps {
  agent: Agent | null;
  logs: LogEntry[];
  running: boolean;
  onRun: (task: string) => void;
}

export function TaskRunner({ agent, logs, running, onRun }: TaskRunnerProps) {
  const [task, setTask] = useState("");
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [logs]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = task.trim();
    if (!trimmed || !agent || running) return;
    onRun(trimmed);
    setTask("");
  };

  return (
    <section className="flex flex-col rounded-2xl border border-purple-500/20 bg-panel/70 p-5 backdrop-blur">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-purple-300/80">Task Runner</h2>
        <span className="text-xs text-purple-300/50">{agent ? `target: ${agent.name}` : "select an agent"}</span>
      </div>

      <form onSubmit={submit} className="flex gap-2">
        <input
          value={task}
          onChange={(event) => setTask(event.target.value)}
          placeholder={
            agent
              ? "Describe a task, e.g. 'scrape HN front page and summarize it'"
              : "Create and select an agent first"
          }
          disabled={!agent || running}
          className="min-w-0 flex-1 rounded-lg border border-purple-500/25 bg-black/30 px-3 py-2 text-sm text-white placeholder:text-purple-300/30 focus:border-fuchsia-400/60 focus:outline-none disabled:opacity-40"
        />
        <button
          type="submit"
          disabled={!agent || running || !task.trim()}
          className="shrink-0 rounded-lg bg-gradient-to-r from-purple-600 to-fuchsia-600 px-4 py-2 text-sm font-semibold text-white transition hover:from-purple-500 hover:to-fuchsia-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {running ? "Running…" : "Run"}
        </button>
      </form>

      <div
        ref={logRef}
        className="mt-4 h-72 overflow-y-auto rounded-xl border border-purple-500/15 bg-black/40 p-4 font-mono text-xs leading-relaxed"
      >
        {logs.length === 0 ? (
          <p className="text-purple-300/40">Execution log is empty. Dispatch a task to see live traces.</p>
        ) : (
          logs.map((entry, index) => (
            <p key={`${entry.timestamp}-${index}`} className={LEVEL_STYLE[entry.level]}>
              <span className="text-purple-300/40">[{new Date(entry.timestamp).toLocaleTimeString()}]</span>{" "}
              {PREFIX[entry.level]} {entry.message}
            </p>
          ))
        )}
      </div>
    </section>
  );
}
