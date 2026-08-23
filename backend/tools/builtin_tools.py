"""First-party tools shipped with AgentOS: search, files, code execution, and HTTP."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from tools.registry import ToolRegistry

WORKSPACE_DIR = Path(os.environ.get("AGENTOS_WORKSPACE", Path(tempfile.gettempdir()) / "agentos_workspace"))
USER_AGENT = "Mozilla/5.0 (compatible; AgentOS/1.0)"
MAX_BODY_CHARS = 4000


def _safe_path(path: str) -> Path:
    """Resolve a workspace-relative path and refuse anything escaping the sandbox."""
    root = WORKSPACE_DIR.resolve()
    candidate = (root / path.lstrip("/\\")).resolve()
    if not str(candidate).startswith(str(root)):
        raise ValueError("path escapes the AgentOS workspace sandbox")
    return candidate


def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the public web via DuckDuckGo's HTML endpoint."""
    response = httpx.get(
        "https://duckduckgo.com/html/",
        params={"q": query},
        headers={"User-Agent": USER_AGENT},
        timeout=10.0,
        follow_redirects=True,
    )
    response.raise_for_status()
    results: list[dict[str, str]] = []
    pattern = re.compile(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
    for href, title in pattern.findall(response.text)[:max_results]:
        parsed = urlparse(href.replace("&amp;", "&"))
        target = parse_qs(parsed.query).get("uddg", [href])[0]
        clean_title = re.sub(r"<[^>]+>", "", title).strip()
        results.append({"title": clean_title, "url": unquote(target)})
    return {"query": query, "results": results}


def read_file(path: str, max_bytes: int = 102_400) -> dict[str, Any]:
    """Read a text file from the agent workspace."""
    target = _safe_path(path)
    if not target.exists():
        raise FileNotFoundError(f"'{path}' does not exist in the workspace")
    content = target.read_text(encoding="utf-8", errors="replace")[:max_bytes]
    return {"path": str(target), "bytes_read": len(content), "content": content}


def write_file(path: str, content: str) -> dict[str, Any]:
    """Write (or overwrite) a text file inside the agent workspace."""
    target = _safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": str(target), "bytes_written": len(content.encode("utf-8"))}


def execute_code(code: str, timeout_seconds: float = 30.0) -> dict[str, Any]:
    """Run Python source in an isolated subprocess rooted at the workspace."""
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [sys.executable, "-I", "-u", "-c", code],
        cwd=str(WORKSPACE_DIR),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-MAX_BODY_CHARS:],
        "stderr": completed.stderr[-MAX_BODY_CHARS:],
    }


def http_request(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Perform an arbitrary HTTP request and return status plus a truncated body."""
    response = httpx.request(
        method,
        url,
        headers=headers,
        params=params,
        json=json_body,
        timeout=15.0,
        follow_redirects=True,
    )
    try:
        body: Any = response.json()
    except ValueError:
        body = response.text[:MAX_BODY_CHARS]
    return {"status": response.status_code, "url": str(response.url), "body": body}


def register_builtin_tools(registry: ToolRegistry) -> None:
    """Attach every built-in tool to the given registry."""
    registry.register(
        "web_search",
        "Search the public web and return ranked results with titles and URLs.",
        {
            "type": "object",
            "properties": {"query": {"type": "string"}, "max_results": {"type": "integer", "default": 5}},
            "required": ["query"],
        },
        web_search,
        builtin=True,
    )
    registry.register(
        "read_file",
        "Read a text file from the agent workspace.",
        {
            "type": "object",
            "properties": {"path": {"type": "string"}, "max_bytes": {"type": "integer", "default": 102400}},
            "required": ["path"],
        },
        read_file,
        builtin=True,
    )
    registry.register(
        "write_file",
        "Write (or overwrite) a text file in the agent workspace.",
        {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
        write_file,
        builtin=True,
    )
    registry.register(
        "execute_code",
        "Run Python source in a sandboxed subprocess inside the workspace and capture stdout/stderr.",
        {
            "type": "object",
            "properties": {"code": {"type": "string"}, "timeout_seconds": {"type": "number", "default": 30}},
            "required": ["code"],
        },
        execute_code,
        builtin=True,
    )
    registry.register(
        "http_request",
        "Perform an arbitrary HTTP request against any URL and return the response.",
        {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "method": {"type": "string", "default": "GET"},
                "headers": {"type": "object"},
                "params": {"type": "object"},
                "json_body": {"type": "object"},
            },
            "required": ["url"],
        },
        http_request,
        builtin=True,
    )
