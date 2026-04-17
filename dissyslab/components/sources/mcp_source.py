# components/sources/mcp_source.py
"""
MCP Source — Poll any MCP server tool as a DisSysLab source.

Supports both local stdio MCP servers (run as subprocesses) and
remote HTTP MCP servers (connected via URL).

Most MCP servers run locally via stdio. Remote HTTP servers are
less common but supported.

Requires: pip install mcp mcp-server-fetch

Example office.md (local stdio server):
    Sources: mcp_source(server="fetch",
                         tool="fetch",
                         args={"url": "https://reddit.com/r/python.rss"},
                         poll_interval=300)

Example office.md (remote HTTP server):
    Sources: mcp_source(server="https://my-server.com/mcp",
                         tool="search",
                         args={"query": "AI news"},
                         poll_interval=300)

Example Python:
    from dissyslab.components.sources.mcp_source import MCPSource
    from dissyslab.blocks import Source

    source = MCPSource(
        server="fetch",
        tool="fetch",
        args={"url": "https://news.ycombinator.com/rss"},
        poll_interval=300,
    )
    node = Source(fn=source.run, name="hackernews")
"""

import asyncio
import json
import os
import time


class MCPSource:
    """
    Poll any MCP server tool and yield results as DisSysLab messages.

    For local stdio servers (most MCP servers), pass the server name
    from STDIO_SERVERS. For remote HTTP servers, pass the full URL.

    Each call to the tool may return one item or many. If the result
    is a JSON list, each element is yielded as a separate message.
    If it is a JSON dict, it is yielded as a single message.
    If it is plain text, it is wrapped in {"text": ..., "source": ...}.

    Args:
        server:        Server name (see STDIO_SERVERS) or full HTTP URL
        tool:          Tool name to call on the server
        args:          Dict of arguments to pass to the tool (optional)
        poll_interval: Seconds to wait between polls (default: 300)
        max_items:     Stop after this many items total (None = run forever)
        auth_env_var:  Name of environment variable holding the auth token
                       (only used for remote HTTP servers)
    """

    # Local stdio MCP servers — launched as subprocesses
    # Install each with: pip install <package> or use uvx
    STDIO_SERVERS = {
        "fetch":        ["python", "-m", "mcp_server_fetch"],
        "brave_search": ["python", "-m", "mcp_server_brave_search"],
        "github":       ["uvx", "mcp-server-github"],
        "filesystem":   ["python", "-m", "mcp_server_filesystem"],
        "sqlite":       ["python", "-m", "mcp_server_sqlite"],
    }

    def __init__(
        self,
        server,
        tool,
        args=None,
        poll_interval=300,
        max_items=None,
        auth_env_var=None,
    ):
        self.server = server
        self.tool = tool
        self.args = args or {}
        self.poll_interval = poll_interval
        self.max_items = max_items
        self.auth_token = os.environ.get(
            auth_env_var) if auth_env_var else None
        self.items_yielded = 0

        # Determine transport type
        self._is_http = server.startswith(
            "http://") or server.startswith("https://")

    # ── Async MCP calls ───────────────────────────────────────────────────────

    async def _async_call_stdio(self):
        """Call a local stdio MCP server running as a subprocess."""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            raise ImportError(
                "MCPSource requires the 'mcp' library.\n"
                "Install it with: pip install mcp"
            )

        cmd = self.STDIO_SERVERS.get(self.server)
        if not cmd:
            raise ValueError(
                f"Unknown stdio MCP server: '{self.server}'.\n"
                f"Known servers: {list(self.STDIO_SERVERS.keys())}\n"
                f"Or pass a full HTTP URL for a remote server."
            )

        import subprocess as _subprocess

        server_params = StdioServerParameters(
            command=cmd[0],
            args=cmd[1:],
            env=None,
            stderr=_subprocess.DEVNULL,
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(self.tool, self.args)
                    return result.content
        except Exception as e:
            print(
                f"[MCPSource:{self.server}] Error calling '{self.tool}': {e}")
            return []

    async def _async_call_http(self):
        """Call a remote HTTP MCP server."""
        try:
            from mcp.client.streamable_http import streamablehttp_client
            from mcp import ClientSession
        except ImportError:
            raise ImportError(
                "MCPSource requires the 'mcp' library.\n"
                "Install it with: pip install mcp"
            )

        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        try:
            async with streamablehttp_client(
                self.server, headers=headers
            ) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(self.tool, self.args)
                    return result.content
        except Exception as e:
            print(
                f"[MCPSource:{self.server}] Error calling '{self.tool}': {e}")
            return []

    def _call_tool(self):
        """Bridge: call async MCP tool from synchronous DisSysLab thread."""
        if self._is_http:
            return asyncio.run(self._async_call_http())
        else:
            return asyncio.run(self._async_call_stdio())

    # ── Result parsing ────────────────────────────────────────────────────────

    def _parse_results(self, content):
        """
        Convert MCP content blocks into a list of dicts.
        Each dict becomes one message in the DisSysLab network.
        """
        items = []
        for block in content:
            if not hasattr(block, "text"):
                continue
            text = block.text.strip()
            if not text:
                continue
            try:
                data = json.loads(text)
                if isinstance(data, list):
                    items.extend(data)
                elif isinstance(data, dict):
                    items.append(data)
                else:
                    items.append({"text": str(data), "source": self.server})
            except json.JSONDecodeError:
                items.append({
                    "text":   text,
                    "source": self.server,
                    "tool":   self.tool,
                })
        return items

    # ── DisSysLab generator ───────────────────────────────────────────────────

    def run(self):
        """
        Generator that polls the MCP tool and yields result items.

        Runs forever (or until max_items is reached), sleeping
        poll_interval seconds between each call.

        DisSysLab's Source block wraps this generator automatically.
        """
        transport = "HTTP" if self._is_http else "stdio"
        print(
            f"[MCPSource] server={self.server} ({transport})  tool={self.tool}")
        print(f"[MCPSource] Polling every {self.poll_interval}s")
        if self.args:
            print(f"[MCPSource] args={self.args}")

        while True:
            print(f"[MCPSource] Calling {self.tool}...")
            content = self._call_tool()
            items = self._parse_results(content)
            print(f"[MCPSource] Received {len(items)} item(s)")

            for item in items:
                yield item
                self.items_yielded += 1
                if self.max_items and self.items_yielded >= self.max_items:
                    print(
                        f"[MCPSource] Reached max_items={self.max_items}. Stopping."
                    )
                    return

            if self.max_items and self.items_yielded >= self.max_items:
                return

            print(f"[MCPSource] Sleeping {self.poll_interval}s...")
            time.sleep(self.poll_interval)


# ── Test when run directly ────────────────────────────────────────────────────

if __name__ == "__main__":
    print("MCPSource — Test (stdio fetch server)")
    print("=" * 60)
    print("Requires: pip install mcp-server-fetch")
    print("Fetching a web page as markdown via local MCP fetch server...")
    print("-" * 60)

    source = MCPSource(
        server="fetch",
        tool="fetch",
        args={"url": "https://www.anthropic.com/news"},
        poll_interval=60,
        max_items=1,
    )

    count = 0
    for item in source.run():
        count += 1
        text = item.get("text", str(item))
        print(f"\n{count}. {text[:500]}")

    print(f"\n{'=' * 60}")
    print(f"✓ MCPSource yielded {count} items.")
    print()
    print("Note: For RSS feeds, use rss_normalizer directly —")
    print("it produces cleaner structured messages.")
    print("MCPSource is best for web pages, search, GitHub, email, etc.")
