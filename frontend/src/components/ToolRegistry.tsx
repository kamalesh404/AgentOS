import type { ToolDefinition } from "../types";

interface ToolRegistryProps {
  tools: ToolDefinition[];
  onToggle: (name: string, enabled: boolean) => void;
}

export function ToolRegistry({ tools, onToggle }: ToolRegistryProps) {
  const enabledCount = tools.filter((tool) => tool.enabled).length;

  return (
    <section className="rounded-2xl border border-purple-500/20 bg-panel/70 p-5 backdrop-blur">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-purple-300/80">Tool Registry</h2>
        <span className="text-xs text-purple-300/50">
          {enabledCount}/{tools.length} enabled
        </span>
      </div>

      {tools.length === 0 ? (
        <p className="rounded-xl border border-dashed border-purple-500/25 px-4 py-6 text-center text-xs text-purple-300/50">
          Loading registry…
        </p>
      ) : (
        <ul className="space-y-2">
          {tools.map((tool) => (
            <li
              key={tool.name}
              className="flex items-center justify-between gap-3 rounded-lg border border-purple-500/15 bg-purple-500/5 px-3 py-2.5"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <code className="text-xs font-semibold text-fuchsia-300">{tool.name}</code>
                  {tool.builtin && (
                    <span className="rounded bg-sky-500/15 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-sky-300">
                      builtin
                    </span>
                  )}
                </div>
                <p className="truncate text-xs text-slate-400">{tool.description}</p>
              </div>
              <button
                role="switch"
                aria-checked={tool.enabled}
                aria-label={`Toggle ${tool.name}`}
                onClick={() => onToggle(tool.name, !tool.enabled)}
                className={`relative h-5 w-9 shrink-0 rounded-full transition ${
                  tool.enabled ? "bg-fuchsia-500" : "bg-slate-700"
                }`}
              >
                <span
                  className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${
                    tool.enabled ? "left-[18px]" : "left-0.5"
                  }`}
                />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
