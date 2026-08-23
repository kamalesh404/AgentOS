import { useCallback, useEffect, useMemo, useState } from "react";
import { AgentDashboard } from "./components/AgentDashboard";
import { TaskRunner } from "./components/TaskRunner";
import { MemoryViewer } from "./components/MemoryViewer";
import { ToolRegistry } from "./components/ToolRegistry";
import type {
  Agent,
  AgentType,
  LogEntry,
  LogLevel,
  MemoryEntry,
  RunResult,
  ToolDefinition,
} from "./types";

const API_BASE = import.meta.env.VITE_API_URL ?? "";
const MAX_LOGS = 200;

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Request failed (${response.status}): ${detail.slice(0, 200)}`);
  }
  return (await response.json()) as T;
}

function log(level: LogLevel, message: string): LogEntry {
  return { level, message, timestamp: new Date().toISOString() };
}

function StatChip({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 px-3 py-1.5 text-center">
      <div className="text-base font-bold leading-none text-fuchsia-300">{value}</div>
      <div className="mt-1 text-[10px] uppercase tracking-wider text-purple-300/60">{label}</div>
    </div>
  );
}

export default function App() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [creating, setCreating] = useState(false);
  const [loadingMemory, setLoadingMemory] = useState(false);

  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedId) ?? null,
    [agents, selectedId],
  );

  const appendLog = useCallback((level: LogLevel, message: string) => {
    setLogs((prev) => [...prev.slice(-(MAX_LOGS - 1)), log(level, message)]);
  }, []);

  const refreshAgents = useCallback(async () => {
    try {
      setAgents(await api<Agent[]>("/api/agents"));
    } catch (error) {
      console.error(error);
    }
  }, []);

  const refreshTools = useCallback(async () => {
    try {
      setTools(await api<ToolDefinition[]>("/api/tools"));
    } catch (error) {
      console.error(error);
    }
  }, []);

  const loadMemories = useCallback(async (agentId: string, query?: string) => {
    setLoadingMemory(true);
    try {
      const suffix = query ? `?q=${encodeURIComponent(query)}` : "";
      const data = await api<{ memories: MemoryEntry[] }>(`/api/memory/${agentId}${suffix}`);
      setMemories(data.memories);
    } catch (error) {
      appendLog("error", String(error));
    } finally {
      setLoadingMemory(false);
    }
  }, [appendLog]);

  useEffect(() => {
    void refreshAgents();
    void refreshTools();
    const timer = window.setInterval(refreshAgents, 5000);
    return () => window.clearInterval(timer);
  }, [refreshAgents, refreshTools]);

  useEffect(() => {
    if (selectedId) {
      void loadMemories(selectedId);
    } else {
      setMemories([]);
    }
  }, [selectedId, loadMemories]);

  const handleCreate = useCallback(
    async (type: AgentType) => {
      setCreating(true);
      try {
        const agent = await api<Agent>("/api/agents/create", {
          method: "POST",
          body: JSON.stringify({ type }),
        });
        appendLog("info", `Agent ${agent.name} (${agent.type}) spawned as ${agent.id}`);
        await refreshAgents();
        setSelectedId(agent.id);
      } catch (error) {
        appendLog("error", String(error));
      } finally {
        setCreating(false);
      }
    },
    [appendLog, refreshAgents],
  );

  const handleRun = useCallback(
    async (task: string) => {
      if (!selectedAgent) return;
      setRunning(true);
      setLogs([log("info", `Dispatching task to ${selectedAgent.name}: ${task}`)]);
      try {
        const result = await api<RunResult>(`/api/agents/${selectedAgent.id}/run`, {
          method: "POST",
          body: JSON.stringify({ task }),
        });
        for (const step of result.steps ?? []) {
          appendLog("action", `step ${step.step} · ${step.action}(${JSON.stringify(step.action_input ?? {})})`);
          appendLog("observation", String(step.observation).slice(0, 400));
        }
        appendLog("success", `${result.answer} (${result.duration_ms} ms)`);
        await refreshAgents();
        void loadMemories(selectedAgent.id);
      } catch (error) {
        appendLog("error", String(error));
      } finally {
        setRunning(false);
      }
    },
    [selectedAgent, appendLog, refreshAgents, loadMemories],
  );

  const handleToggleTool = useCallback(
    async (name: string, enabled: boolean) => {
      setTools((prev) => prev.map((tool) => (tool.name === name ? { ...tool, enabled } : tool)));
      try {
        await api(`/api/tools/${name}/toggle?enabled=${enabled}`, { method: "PATCH" });
        appendLog("info", `Tool ${name} ${enabled ? "enabled" : "disabled"}`);
      } catch (error) {
        setTools((prev) => prev.map((tool) => (tool.name === name ? { ...tool, enabled: !enabled } : tool)));
        appendLog("error", String(error));
      }
    },
    [appendLog],
  );

  const handleSearchMemory = useCallback(
    (query: string) => {
      if (!selectedId) return;
      void loadMemories(selectedId, query || undefined);
    },
    [selectedId, loadMemories],
  );

  const activeCount = agents.filter((agent) =>
    ["thinking", "acting", "observing"].includes(agent.status),
  ).length;

  return (
    <div className="min-h-screen px-4 pb-12 pt-6 sm:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-purple-500/20 bg-panel/70 px-6 py-5 shadow-lg shadow-purple-950/40 backdrop-blur">
          <div className="flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-purple-500 to-fuchsia-600 text-xl font-black text-white">
              A
            </span>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white">AgentOS</h1>
              <p className="text-sm text-purple-300/70">autonomous agents · browse · code · create</p>
            </div>
          </div>
          <div className="flex gap-3">
            <StatChip label="Agents" value={agents.length} />
            <StatChip label="Active" value={activeCount} />
            <StatChip label="Tools" value={tools.length} />
            <StatChip label="Memories" value={memories.length} />
          </div>
        </header>

        <main className="grid gap-6 lg:grid-cols-5">
          <section className="space-y-6 lg:col-span-3">
            <AgentDashboard
              agents={agents}
              selectedId={selectedId}
              onSelect={setSelectedId}
              onCreate={handleCreate}
              creating={creating}
            />
            <TaskRunner agent={selectedAgent} logs={logs} running={running} onRun={handleRun} />
          </section>
          <aside className="space-y-6 lg:col-span-2">
            <ToolRegistry tools={tools} onToggle={handleToggleTool} />
            <MemoryViewer
              memories={memories}
              loading={loadingMemory}
              disabled={!selectedAgent}
              agentName={selectedAgent?.name}
              onSearch={handleSearchMemory}
            />
          </aside>
        </main>

        <footer className="pt-2 text-center text-xs text-purple-300/40">
          AgentOS · autonomous agents that browse, code, and create
        </footer>
      </div>
    </div>
  );
}
