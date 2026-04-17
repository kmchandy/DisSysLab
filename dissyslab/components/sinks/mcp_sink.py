# components/sinks/mcp_sink.py
"""
MCP Sink — Send DisSysLab messages to any MCP server tool.

Supports both local stdio MCP servers (run as subprocesses) and
remote HTTP MCP servers (connected via URL).

Static args (from office.md) are merged with the message fields —
message fields take precedence, so agents can override defaults.

Requires: pip install mcp

Example office.md (local stdio server):
    Sinks: mcp_sink(server="filesystem",
                     tool="write_file",
                     args={"path": "output.txt"})

Example office.md (remote HTTP server):
    Sinks: mcp_sink(server="https://my-server.com/mcp",
                     tool="send_alert",
                     args={"channel": "#news"},
                     auth_env_var="SLACK_TOKEN")

Example Python:
    from dissyslab.components.sinks.mcp_sink import MCPSink
    from dissyslab.blocks import Sink

    sink = MCPSink(
        server="filesystem",
        tool="write_file",
        args={"path": "briefings.txt"},
    )
    node = Sink(fn=sink.run, name="file_output")
"""

import asyncio
import os


class MCPSink:
    """
    Send each DisSysLab message to an MCP server tool.

    For each incoming message, merges the message fields with any
    static args provided at construction time, then calls the MCP tool.
    Message fields take precedence over static args, so agents can
    override defaults (e.g. set a dynamic file path or subject line).

    Args:
        server:       Server name (see STDIO_SERVERS) or full HTTP URL
        tool:         Tool name to call for each message
        args:         Static args merged with each message (optional)
        auth_env_var: Name of environment variable holding the auth token
                      (only used for remote HTTP servers)
    """

    # Local stdio MCP servers — launched as subprocesses
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
        auth_env_var=None,
    ):
        self.server = server
        self.tool = tool
        self.static_args = args or {}
        self.auth_token = os.environ.get(
            auth_env_var) if auth_env_var else None
        self.calls_made = 0

        # Determine transport type
        self._is_http = server.startswith(
            "http://") or server.startswith("https://")

    # ── Async MCP calls ───────────────────────────────────────────────────────

    async def _async_call_stdio(self, merged_args):
        """Call a local stdio MCP server running as a subprocess."""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            raise ImportError(
                "MCPSink requires the 'mcp' library.\n"
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
                    result = await session.call_tool(self.tool, merged_args)
                    return result
        except Exception as e:
            print(f"[MCPSink:{self.server}] Error calling '{self.tool}': {e}")
            return None

    async def _async_call_http(self, merged_args):
        """Call a remote HTTP MCP server."""
        try:
            from mcp.client.streamable_http import streamablehttp_client
            from mcp import ClientSession
        except ImportError:
            raise ImportError(
                "MCPSink requires the 'mcp' library.\n"
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
                    result = await session.call_tool(self.tool, merged_args)
                    return result
        except Exception as e:
            print(f"[MCPSink:{self.server}] Error calling '{self.tool}': {e}")
            return None

    # ── DisSysLab sink function ───────────────────────────────────────────────

    def run(self, msg):
        """
        Called by DisSysLab for each incoming message.

        Merges static args with message fields (message wins on conflict)
        and calls the MCP tool. Runs synchronously — bridges to async
        internally using asyncio.run().

        Args:
            msg: Dict message from upstream DisSysLab node
        """
        # Message fields override static args
        merged = {**self.static_args, **msg}

        self.calls_made += 1
        transport = "HTTP" if self._is_http else "stdio"
        print(
            f"[MCPSink] Call #{self.calls_made} — "
            f"server={self.server} ({transport})  tool={self.tool}"
        )

        if self._is_http:
            asyncio.run(self._async_call_http(merged))
        else:
            asyncio.run(self._async_call_stdio(merged))


# ── Test when run directly ────────────────────────────────────────────────────

if __name__ == "__main__":
    print("MCPSink — Test")
    print("=" * 60)
    print("To test MCPSink with the filesystem server:")
    print()
    print("  pip install mcp-server-filesystem")
    print()
    print("  sink = MCPSink(")
    print("      server='filesystem',")
    print("      tool='write_file',")
    print("      args={'path': 'test_output.txt'},")
    print("  )")
    print("  sink.run({'text': 'Hello from DisSysLab!'})")
    print()
    print("For remote HTTP servers:")
    print()
    print("  sink = MCPSink(")
    print("      server='https://my-server.com/mcp',")
    print("      tool='send_alert',")
    print("      args={'channel': '#news'},")
    print("      auth_env_var='MY_TOKEN',")
    print("  )")
    print("  sink.run({'text': 'Breaking news!'})")
