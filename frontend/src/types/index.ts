export type AgentType = "base" | "code" | "browse";

export type AgentStatus =
  | "idle"
  | "thinking"
  | "acting"
  | "observing"
  | "finished"
  | "failed";

export interface Agent {
  id: string;
  name: string;
  type: AgentType;
  model: string;
  status: AgentStatus;
  tasks_completed: number;
  created_at: string;
}

export type LogLevel = "info" | "action" | "observation" | "success" | "error";

export interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: string;
}

export interface StepTrace {
  step: number;
  action: string;
  action_input: unknown;
  observation: unknown;
}

export interface RunResult {
  agent_id: string;
  task: string;
  answer: string;
  status: string;
  duration_ms: number;
  iterations: number;
  steps: StepTrace[];
}

export interface MemoryEntry {
  id: string;
  agent_id: string;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
  score?: number;
}

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
  builtin: boolean;
  enabled: boolean;
}
