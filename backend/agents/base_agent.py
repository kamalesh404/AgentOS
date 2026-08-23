"""Core ReAct-style agent loop shared by every AgentOS agent."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any

from memory.store import MemoryStore
from tools.registry import ToolRegistry


class AgentStatus(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    FINISHED = "finished"
    FAILED = "failed"


@dataclass
class Thought:
    step: int
    reasoning: str
    action: str
    action_input: Any = None


@dataclass
class StepTrace:
    step: int
    action: str
    action_input: Any
    observation: Any


DEFAULT_SYSTEM_PROMPT = """You are {name}, an autonomous {role} powered by {model}.

Solve the user's task by iterating through a think-act-observe loop.
On every turn respond EXACTLY in this format (no markdown fences):

THOUGHT: one or two sentences of reasoning about what to do next
ACTION: the tool to use next, or "finish" when the task is complete
INPUT: the JSON object passed to the tool, or your final answer as plain text when ACTION is finish

Rules:
- Prefer finishing over looping once you have enough information.
- Never invent tool names; pick only from the list below.
- INPUT must be valid JSON on a single line when calling a tool.

Available tools:
{tools}
"""


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


class BaseAgent:
    """An autonomous agent implementing the perceive-think-act-observe loop."""

    role = "AI agent"
    default_toolkit: list[str] | None = None

    def __init__(
        self,
        name: str,
        model: str = "gpt-4o-mini",
        tool_registry: ToolRegistry | None = None,
        memory_store: MemoryStore | None = None,
        max_iterations: int = 8,
    ) -> None:
        self.id = uuid.uuid4().hex
        self.name = name
        self.model = model
        self.tool_registry = tool_registry
        self.memory_store = memory_store
        self.max_iterations = max_iterations
        self.status = AgentStatus.IDLE
        self.history: list[StepTrace] = []

    @property
    def type(self) -> str:
        return self.__class__.__name__.removesuffix("Agent").lower() or "base"

    def describe(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "model": self.model,
            "status": self.status.value,
        }

    def available_tools(self) -> list[dict[str, Any]]:
        if self.tool_registry is None:
            return []
        tools = self.tool_registry.get_tools(enabled_only=True)
        if self.default_toolkit is not None:
            allowed = set(self.default_toolkit)
            tools = [tool for tool in tools if tool["name"] in allowed]
        return tools

    def _format_prompt(self, template: str) -> str:
        listing = "\n".join(f"- {t['name']}: {t['description']}" for t in self.available_tools()) or "(none)"
        return template.format(name=self.name, role=self.role, model=self.model, tools=listing)

    def system_prompt(self) -> str:
        return self._format_prompt(DEFAULT_SYSTEM_PROMPT)

    def _call_llm(self, messages: list[dict[str, str]]) -> str:
        from openai import OpenAI

        client = OpenAI()
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    def think(self, context: str) -> Thought:
        """Reason about the current context and choose the next action."""
        self.status = AgentStatus.THINKING
        step = len(self.history) + 1
        messages = [
            {"role": "system", "content": self.system_prompt()},
            {"role": "user", "content": context},
        ]
        try:
            raw = self._call_llm(messages)
            reasoning, action, action_input = self._parse_response(raw)
        except Exception as exc:
            return Thought(
                step=step,
                reasoning=f"planner unavailable: {exc}",
                action="finish",
                action_input=f"Unable to plan further ({exc}).",
            )
        return Thought(step=step, reasoning=reasoning, action=action, action_input=action_input)

    @staticmethod
    def _parse_response(raw: str) -> tuple[str, str, Any]:
        thought_match = re.search(r"THOUGHT:\s*(.+)", raw)
        action_match = re.search(r"ACTION:\s*(.+)", raw)
        input_match = re.search(r"INPUT:\s*(.+)", raw, re.DOTALL)
        reasoning = thought_match.group(1).strip() if thought_match else raw.strip()[:200]
        action = action_match.group(1).strip().strip('"') if action_match else "finish"
        raw_input = input_match.group(1).strip() if input_match else ""
        if action == "finish":
            return reasoning, action, raw_input
        try:
            return reasoning, action, json.loads(raw_input)
        except json.JSONDecodeError:
            return reasoning, action, raw_input

    def act(self, thought: Thought) -> Any:
        """Execute the chosen action through the tool registry."""
        self.status = AgentStatus.ACTING
        if thought.action == "finish":
            return thought.action_input
        if self.tool_registry is None:
            return {"error": "no tool registry attached"}
        return self.tool_registry.execute_tool(thought.action, thought.action_input)

    def observe(self, thought: Thought, observation: Any) -> None:
        """Record what happened so later iterations can condition on it."""
        self.status = AgentStatus.OBSERVING
        trace = StepTrace(step=thought.step, action=thought.action, action_input=thought.action_input, observation=observation)
        self.history.append(trace)
        failed = isinstance(observation, dict) and observation.get("ok") is False
        if failed or self.memory_store is None:
            return
        serialized = _truncate(json.dumps(observation, default=str), 400)
        self.memory_store.store(self.id, f"[{thought.action}] {serialized}", metadata={"step": thought.step})

    def run(self, task: str) -> dict[str, Any]:
        """Run the full think -> act -> observe loop until the agent finishes."""
        self.history = []
        context = task
        answer: Any = None

        for _ in range(self.max_iterations):
            thought = self.think(context)
            if thought.action == "finish":
                answer = thought.action_input
                self.status = AgentStatus.FINISHED
                if self.memory_store is not None:
                    self.memory_store.store(
                        self.id,
                        f"final answer: {_truncate(str(answer), 500)}",
                        metadata={"kind": "answer"},
                    )
                break
            observation = self.act(thought)
            self.observe(thought, observation)
            progress = "\n".join(
                f"- step {t.step} {t.action}: {_truncate(json.dumps(t.observation, default=str), 300)}"
                for t in self.history[-3:]
            )
            context = f"{task}\n\nProgress so far:\n{progress}\nContinue."
        else:
            self.status = AgentStatus.FINISHED
            tail = json.dumps([t.observation for t in self.history[-2:]], default=str)
            answer = f"Iteration limit reached. Last observations: {_truncate(tail, 400)}"

        return {
            "task": task,
            "answer": answer if isinstance(answer, str) else json.dumps(answer, indent=2, default=str),
            "status": self.status.value,
            "iterations": len(self.history),
            "steps": [
                {
                    "step": trace.step,
                    "action": trace.action,
                    "action_input": trace.action_input,
                    "observation": trace.observation,
                }
                for trace in self.history
            ],
        }
