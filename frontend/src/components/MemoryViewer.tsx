import { useState, type FormEvent } from "react";
import type { MemoryEntry } from "../types";

interface MemoryViewerProps {
  memories: MemoryEntry[];
  loading: boolean;
  disabled?: boolean;
  agentName?: string;
  onSearch: (query: string) => void;
}

export function MemoryViewer({ memories, loading, disabled, agentName, onSearch }: MemoryViewerProps) {
  const [query, setQuery] = useState("");

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!disabled) onSearch(query.trim());
  };

  return (
    <section className="rounded-2xl border border-purple-500/20 bg-panel/70 p-5 backdrop-blur">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-purple-300/80">Memory Bank</h2>
        <span className="text-xs text-purple-300/50">{agentName ?? "no agent selected"}</span>
      </div>

      <form onSubmit={submit} className="mt-3 flex gap-2">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Semantic search across memories"
          disabled={disabled}
          className="min-w-0 flex-1 rounded-lg border border-purple-500/25 bg-black/30 px-3 py-2 text-sm text-white placeholder:text-purple-300/30 focus:border-fuchsia-400/60 focus:outline-none disabled:opacity-40"
        />
        <button
          type="submit"
          disabled={disabled || loading}
          className="shrink-0 rounded-lg border border-purple-400/30 bg-purple-500/10 px-3 py-2 text-xs font-medium text-purple-200 transition hover:bg-purple-500/25 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? "…" : "Search"}
        </button>
      </form>

      <div className="mt-4 max-h-64 space-y-2 overflow-y-auto pr-1">
        {memories.length === 0 ? (
          <p className="rounded-xl border border-dashed border-purple-500/25 px-4 py-6 text-center text-xs text-purple-300/50">
            {disabled ? "Select an agent to inspect its memory." : "No memories recorded yet."}
          </p>
        ) : (
          memories.map((memory) => (
            <article key={memory.id} className="rounded-lg border border-purple-500/15 bg-purple-500/5 p-3">
              <div className="mb-1 flex items-center justify-between gap-2 text-[10px] uppercase tracking-wider text-purple-300/50">
                <span>{new Date(memory.created_at).toLocaleString()}</span>
                {typeof memory.score === "number" && (
                  <span className="rounded bg-fuchsia-500/20 px-1.5 py-0.5 text-fuchsia-300">
                    {memory.score.toFixed(3)}
                  </span>
                )}
              </div>
              <p className="whitespace-pre-wrap break-words text-xs leading-relaxed text-slate-200">
                {memory.content}
              </p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
