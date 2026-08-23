import type { Agent, AgentStatus, AgentType } from "../types";

const STATUS_STYLES: Record<AgentStatus, { dot: string; text: string }> = {
  idle: { dot: "bg-slate-400", text: "text-slate-300" },
  thinking: { dot: "bg-amber-400 animate-pulse", text: "text-amber-300" },
  acting: { dot: "bg-fuchsia-400 animate-pulse", text: "text-fuchsia-300" },
  observing: { dot: "bg-sky-400 animate-pulse", text: "text-sky-300" },
  finished: { dot: "bg-emerald-400", text: "text-emerald-300" },
  failed: { dot: "bg-red-500", text: "text-red-300" },
};

const TYPE_META: Record<AgentType, { glyph: string; label: string }> = {
  base: { glyph: "◆", label: "Generalist" },
  code: { glyph: "{ }", label: "Coder" },
  browse: { glyph: "~", label: "Browser" },
};

interface AgentDashboardProps {
  agents: Agent[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onCreate: (type: AgentType) => void;
  creating: boolean;
}

export function AgentDashboard({ agents, selectedId, onSelect, onCreate, creating }: AgentDashboardProps) {
  return (
    <section className="rounded-2xl border border-purple-500/20 bg-panel/70 p-5 backdrop-blur">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-purple-300/80">Agent Fleet</h2>
        <div className="flex flex-wrap gap-2">
          {(Object.keys(TYPE_META) as AgentType[]).map((type) => (
            <button
              key={type}
              onClick={() => onCreate(type)}
              disabled={creating}
              className="rounded-lg border border-purple-400/30 bg-purple-500/10 px-3 py-1.5 text-xs font-medium text-purple-200 transition hover:border-purple-300/50 hover:bg-purple-500/25 disabled:cursor-not-allowed disabled:opacity-40"
            >
              + {TYPE_META[type].label}
            </button>
          ))}
        </div>
      </div>

      {agents.length === 0 ? (
        <div className="grid place-items-center rounded-xl border border-dashed border-purple-500/25 px-6 py-10 text-center">
          <p className="text-sm text-purple-300/60">No agents yet. Spawn one above to get started.</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {agents.map((agent) => {
            const status = STATUS_STYLES[agent.status];
            const isSelected = agent.id === selectedId;
            return (
              <button
                key={agent.id}
                onClick={() => onSelect(agent.id)}
                className={`w-full rounded-xl border p-4 text-left ring-1 transition ${
                  isSelected
                    ? "border-fuchsia-400/60 bg-fuchsia-500/10 ring-fuchsia-400/40"
                    : "border-purple-500/15 bg-purple-500/5 ring-transparent hover:border-purple-400/40 hover:bg-purple-500/10"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm font-bold text-fuchsia-300">{TYPE_META[agent.type].glyph}</span>
                  <span className={`flex items-center gap-1.5 text-[11px] uppercase tracking-wider ${status.text}`}>
                    <span className={`h-1.5 w-1.5 rounded-full ${status.dot}`} />
                    {agent.status}
                  </span>
                </div>
                <h3 className="mt-2 truncate text-sm font-semibold text-white">{agent.name}</h3>
                <p className="mt-0.5 truncate text-xs text-slate-400">
                  {TYPE_META[agent.type].label} · {agent.model}
                </p>
                <p className="mt-2 text-[10px] uppercase tracking-wider text-purple-300/50">
                  {agent.tasks_completed} task{agent.tasks_completed === 1 ? "" : "s"} completed
                </p>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
