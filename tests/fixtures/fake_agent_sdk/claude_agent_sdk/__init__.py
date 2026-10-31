"""A stand-in for the Claude Agent SDK, for testing course/lab3's scripts
where the SDK is not installed. It keeps what the scripts pass in, so a
test can call the tools and hooks they define; it runs no model."""

from dataclasses import dataclass, field
from typing import Any


class SdkMcpTool:
    def __init__(self, name, description, schema, handler):
        self.name, self.description, self.schema, self.handler = name, description, schema, handler


def tool(name, description, input_schema, annotations=None):
    return lambda fn: SdkMcpTool(name, description, input_schema, fn)


def create_sdk_mcp_server(name, version="1.0.0", tools=None):
    return {"name": name, "tools": {t.name: t for t in tools or []}}


@dataclass
class HookMatcher:
    matcher: str | None = None
    hooks: list = field(default_factory=list)
    timeout: float | None = None


class ClaudeAgentOptions:
    def __init__(self, **kwargs: Any):
        self.__dict__.update(kwargs)
