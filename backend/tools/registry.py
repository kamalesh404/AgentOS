"""Central registry of capabilities available to AgentOS agents."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

Handler = Callable[..., Any]


class ToolError(RuntimeError):
    """Raised when a tool cannot be resolved or executed."""


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Handler
    builtin: bool = False
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "builtin": self.builtin,
            "enabled": self.enabled,
        }


class ToolRegistry:
    """Tracks every tool an agent may call and executes them safely."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Handler,
        builtin: bool = False,
    ) -> Tool:
        """Register (or replace) a tool under the given name."""
        if not name or not name.replace("_", "").isalnum():
            raise ValueError(f"invalid tool name: {name!r}")
        tool = Tool(name=name, description=description, parameters=parameters, handler=handler, builtin=builtin)
        self._tools[name] = tool
        return tool

    def register_http_tool(self, name: str, description: str, url: str, method: str = "POST") -> Tool:
        """Register a tool whose handler proxies the call to an HTTP endpoint."""
        import httpx

        def handler(**payload: Any) -> dict[str, Any]:
            response = httpx.request(method, url, json=payload, timeout=15.0)
            return {"status_code": response.status_code, "body": response.text[:2000]}

        return self.register(name, description, {"type": "object"}, handler, builtin=False)

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry if present."""
        self._tools.pop(name, None)

    def get_tool(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise ToolError(f"unknown tool '{name}'") from None

    def get_tools(self, names: list[str] | None = None, enabled_only: bool = False) -> list[dict[str, Any]]:
        """Return serializable tool descriptors, optionally filtered and sorted."""
        tools = list(self._tools.values())
        if names is not None:
            wanted = set(names)
            tools = [tool for tool in tools if tool.name in wanted]
        if enabled_only:
            tools = [tool for tool in tools if tool.enabled]
        return sorted((tool.to_dict() for tool in tools), key=lambda t: t["name"])

    def set_enabled(self, name: str, enabled: bool) -> dict[str, Any]:
        """Enable or disable a tool and return its updated descriptor."""
        tool = self.get_tool(name)
        tool.enabled = enabled
        return tool.to_dict()

    def execute_tool(self, name: str, payload: Any = None) -> dict[str, Any]:
        """Execute a registered tool, wrapping success and failure in a uniform envelope."""
        try:
            tool = self.get_tool(name)
        except ToolError as exc:
            return {"ok": False, "tool": name, "error": str(exc)}
        if not tool.enabled:
            return {"ok": False, "tool": name, "error": f"tool '{name}' is disabled"}
        arguments = payload if isinstance(payload, dict) else {}
        started = time.perf_counter()
        try:
            result = tool.handler(**arguments)
        except Exception as exc:
            return {"ok": False, "tool": name, "error": f"{type(exc).__name__}: {exc}"}
        return {
            "ok": True,
            "tool": name,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            "result": result,
        }
