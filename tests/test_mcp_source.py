# tests/test_mcp_source.py
#
# Integration test: MCPSource wired into a DisSysLab network.
# Requires: pip install mcp mcp-server-fetch
#
# Run with:
#   python3 tests/test_mcp_source.py

from dissyslab import network
from dissyslab.blocks import Source, Sink
from dissyslab.components.sources.mcp_source import MCPSource


def display(msg):
    print(f"[display] {msg.get('text', '')[:150]}")


if __name__ == "__main__":
    print("Testing MCPSource in a DisSysLab network...")
    print("=" * 60)

    source = MCPSource(
        server="fetch",
        tool="fetch",
        args={"url": "https://www.anthropic.com/news"},
        poll_interval=60,
        max_items=2,
    )

    src = Source(fn=source.run, name="mcp")
    sink = Sink(fn=display,      name="display")

    g = network([(src, sink)])
    g.run_network()

    print()
    print("✓ MCPSource network test complete.")
