"""AgentOS control plane: spawn agents, dispatch tasks, inspect memory and tools."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.base_agent import AgentStatus, BaseAgent
from agents.browse_agent import BrowseAgent
from agents.code_agent import CodeAgent
from memory.store import MemoryStore
from tools.builtin_tools import register_builtin_tools
from tools.registry import ToolRegistry

app = FastAPI(
    title="AgentOS",
    description="Autonomous AI agent framework - agents that browse, code, and create.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

AGENT_TYPES: dict[str, type[BaseAgent]] = {
    "base": BaseAgent,
    "code": CodeAgent,
    "browse": BrowseAgent,
}

BUSY_STATUSES = {AgentStatus.THINKING, AgentStatus.ACTING, AgentStatus.OBSERVING}


class AgentRecord:
    __slots__ = ("agent", "created_at", "tasks_completed")

    def __init__(self, agent: BaseAgent) -> None:
        self.agent = agent
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.tasks_completed = 0


class CreateAgentRequest(BaseModel):
    type: Literal["base", "code", "browse"] = "base"
    name: str | None = Field(default=None, max_length=64)
    model: str = "gpt-4o-mini"


class RunTaskRequest(BaseModel):
    task: str = Field(min_length=1, max_length=8000)


class RegisterToolRequest(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{1,48}$")
    description: str = Field(min_length=3, max_length=500)
    url: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "POST"


class AgentOut(BaseModel):
    id: str
    name: str
    type: str
    model: str
    status: str
    tasks_completed: int
    created_at: str


_agents: dict[str, AgentRecord] = {}
tool_registry = ToolRegistry()
register_builtin_tools(tool_registry)
memory_store = MemoryStore()


def _record_or_404(agent_id: str) -> AgentRecord:
    record = _agents.get(agent_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"agent '{agent_id}' not found")
    return record


def _to_out(record: AgentRecord) -> AgentOut:
    info = record.agent.describe()
    return AgentOut(**info, tasks_completed=record.tasks_completed, created_at=record.created_at)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/agents/create", response_model=AgentOut, status_code=201)
def create_agent(request: CreateAgentRequest) -> AgentOut:
    agent_cls = AGENT_TYPES[request.type]
    name = request.name or f"{request.type}-{uuid.uuid4().hex[:6]}"
    agent = agent_cls(
        name=name,
        model=request.model,
        tool_registry=tool_registry,
        memory_store=memory_store,
    )
    record = AgentRecord(agent)
    _agents[agent.id] = record
    return _to_out(record)


@app.post("/api/agents/{agent_id}/run")
def run_agent(agent_id: str, request: RunTaskRequest) -> dict[str, Any]:
    record = _record_or_404(agent_id)
    if record.agent.status in BUSY_STATUSES:
        raise HTTPException(status_code=409, detail="agent is already running a task")
    started = time.perf_counter()
    try:
        result = record.agent.run(request.task)
    except Exception as exc:
        record.agent.status = AgentStatus.FAILED
        raise HTTPException(status_code=500, detail=f"agent crashed: {exc}") from exc
    record.tasks_completed += 1
    result["agent_id"] = agent_id
    result["duration_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return result


@app.get("/api/agents/{agent_id}/status", response_model=AgentOut)
def agent_status(agent_id: str) -> AgentOut:
    return _to_out(_record_or_404(agent_id))


@app.get("/api/agents", response_model=list[AgentOut])
def list_agents() -> list[AgentOut]:
    return [_to_out(record) for record in _agents.values()]


@app.get("/api/tools")
def list_tools() -> list[dict[str, Any]]:
    return tool_registry.get_tools()


@app.post("/api/tools/register", status_code=201)
def register_tool(request: RegisterToolRequest) -> dict[str, Any]:
    def handler(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        response = httpx.request(request.method, request.url, json=payload or {}, timeout=15.0)
        return {"status_code": response.status_code, "body": response.text[:2000]}

    tool_registry.register(request.name, request.description, {"type": "object"}, handler, builtin=False)
    return {"registered": request.name, "tools": tool_registry.get_tools()}


@app.patch("/api/tools/{name}/toggle")
def toggle_tool(name: str, enabled: bool = Query(...)) -> dict[str, Any]:
    return tool_registry.set_enabled(name, enabled)


@app.get("/api/memory/{agent_id}")
def get_memory(agent_id: str, q: str | None = None, limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    _record_or_404(agent_id)
    if q:
        memories = memory_store.search(agent_id, q, top_k=limit)
    else:
        memories = memory_store.recall(agent_id, limit=limit)
    return {"agent_id": agent_id, "count": len(memories), "memories": memories}
