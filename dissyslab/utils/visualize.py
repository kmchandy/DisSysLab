# dissyslab/utils/visualize.py

"""
Network visualization utilities for debugging and teaching.

Provides functions to visualize network structure and connections
using the rich library for colorized terminal output.

**Purpose:**
- Debug network structure and connections
- Understand automatic Broadcast/Merge insertion
- Teach distributed systems concepts visually
- Verify network topology before running

**Installation:**
    pip install rich

**Quick Start:**
    >>> from dsl import network
    >>> from dsl.utils.visualize import visualize
    >>> 
    >>> g = network([(source, transform), (transform, sink)])
    >>> visualize(g)

**Complete Example with Output:**

Student code:
    >>> from dsl import network
    >>> from dsl.blocks.source import Source
    >>> from dsl.blocks.transform import Transform
    >>> from dsl.blocks.sink import Sink
    >>> from dsl.utils.visualize import visualize
    >>> 
    >>> # Create data source classes
    >>> class ListSource:
    ...     def __init__(self, items):
    ...         self.items = items
    ...         self.index = 0
    ...     def run(self):
    ...         if self.index >= len(self.items):
    ...             return None
    ...         item = self.items[self.index]
    ...         self.index += 1
    ...         return {"value": item}
    >>> 
    >>> class Doubler:
    ...     def run(self, msg):
    ...         return {"value": msg["value"] * 2}
    >>> 
    >>> class ListCollector:
    ...     def __init__(self):
    ...         self.items = []
    ...     def run(self, msg):
    ...         self.items.append(msg)
    >>> 
    >>> # Create agents
    >>> data = ListSource([1, 2, 3])
    >>> source = Source(fn=data.run)
    >>> 
    >>> doubler = Doubler()
    >>> transform = Transform(fn=doubler.run)
    >>> 
    >>> collector = ListCollector()
    >>> sink = Sink(fn=collector.run)
    >>> 
    >>> # Build simple pipeline
    >>> g = network([
    ...     (source, transform),
    ...     (transform, sink)
    ... ])
    >>> 
    >>> # Visualize!
    >>> visualize(g)

Output (colorized in terminal):
    ━━━━━━━━━━━━━━━ Network Structure ━━━━━━━━━━━━━━━
    Network
    ├── Blocks (Logical)
    │   ├── Source@f47ac10b (Source)
    │   ├── Transform@8b9e3d2a (Transform)
    │   └── Sink@1a2b3c4d (Sink)
    └── Agents (Compiled)
        ├── Source@f47ac10b (Source)
        ├── Transform@8b9e3d2a (Transform)
        └── Sink@1a2b3c4d (Sink)
    
    ━━━━━━━━━ Connections (After Compilation) ━━━━━━━━━
    root⤏Source@f47ac10b ⤏ out -> root⤏Transform@8b9e3d2a ⤏ in
    root⤏Transform@8b9e3d2a ⤏ out -> root⤏Sink@1a2b3c4d ⤏ in
    
    ━━━━━━━━━━━━━ Network Summary ━━━━━━━━━━━━━
    Agent Types:
      • Sink: 1
      • Source: 1
      • Transform: 1
    
    Total Connections: 2

**Example with Fanout/Fanin (Automatic Broadcast/Merge):**

Student code:
    >>> # Multiple sources to one processor (fanin)
    >>> # One processor to multiple sinks (fanout)
    >>> twitter_data = TwitterSource()
    >>> twitter = Source(fn=twitter_data.run)
    >>> 
    >>> reddit_data = RedditSource()
    >>> reddit = Source(fn=reddit_data.run)
    >>> 
    >>> cleaner = TextCleaner()
    >>> clean = Transform(fn=cleaner.run)
    >>> 
    >>> sentiment_analyzer = SentimentAnalyzer()
    >>> sentiment = Transform(fn=sentiment_analyzer.run)
    >>> 
    >>> urgency_analyzer = UrgencyAnalyzer()
    >>> urgency = Transform(fn=urgency_analyzer.run)
    >>> 
    >>> logger = ConsoleLogger()
    >>> log = Sink(fn=logger.run)
    >>> 
    >>> # Build network with fanin and fanout
    >>> g = network([
    ...     (twitter, clean),    # Fanin at clean
    ...     (reddit, clean),
    ...     (clean, sentiment),  # Fanout from clean
    ...     (clean, urgency),
    ...     (sentiment, log),    # Fanin at log
    ...     (urgency, log)
    ... ])
    >>> 
    >>> visualize(g)

Output (showing auto-inserted Broadcast and Merge):
    ━━━━━━━━━━━━━━━ Network Structure ━━━━━━━━━━━━━━━
    Network
    ├── Blocks (Logical)
    │   ├── Source@abc (Source)
    │   ├── Source@def (Source)
    │   ├── Transform@ghi (Transform)
    │   ├── Transform@jkl (Transform)
    │   ├── Transform@mno (Transform)
    │   └── Sink@pqr (Sink)
    └── Agents (Compiled)
        ├── Source@abc (Source)
        ├── Source@def (Source)
        ├── merge_0 (MergeAsynch)        ← AUTO-INSERTED for fanin
        ├── Transform@ghi (Transform)
        ├── broadcast_0 (Broadcast)      ← AUTO-INSERTED for fanout
        ├── Transform@jkl (Transform)
        ├── Transform@mno (Transform)
        ├── merge_1 (MergeAsynch)        ← AUTO-INSERTED for fanin
        └── Sink@pqr (Sink)
    
    ━━━━━━━━━ Connections (After Compilation) ━━━━━━━━━
    root⤏Source@abc ⤏ out -> root⤏merge_0 ⤏ in_0
    root⤏Source@def ⤏ out -> root⤏merge_0 ⤏ in_1
    root⤏merge_0 ⤏ out -> root⤏Transform@ghi ⤏ in
    root⤏Transform@ghi ⤏ out -> root⤏broadcast_0 ⤏ in
    root⤏broadcast_0 ⤏ out_0 -> root⤏Transform@jkl ⤏ in
    root⤏broadcast_0 ⤏ out_1 -> root⤏Transform@mno ⤏ in
    root⤏Transform@jkl ⤏ out -> root⤏merge_1 ⤏ in_0
    root⤏Transform@mno ⤏ out -> root⤏merge_1 ⤏ in_1
    root⤏merge_1 ⤏ out -> root⤏Sink@pqr ⤏ in
    
    ━━━━━━━━━━━━━ Network Summary ━━━━━━━━━━━━━
    Agent Types:
      • Broadcast: 1
      • MergeAsynch: 2
      • Sink: 1
      • Source: 2
      • Transform: 3
    
    Total Connections: 9
    
    Detected Patterns:
      • Fanout (Broadcast): 1
      • Fanin (Merge): 2

**Visual Explanation:**

Before (what student wrote):
    twitter ─┐
             ├─→ clean ─┬─→ sentiment ─┐
    reddit ──┘          └─→ urgency ───┴─→ log

After (with auto-inserted nodes):
    twitter ─┐
             ├─→ merge_0 ─→ clean ─→ broadcast_0 ─┬─→ sentiment ─┐
    reddit ──┘                                     └─→ urgency ───┴─→ merge_1 ─→ log

The framework automatically handles the complexity!

**Advanced Usage:**

Show port names:
    >>> visualize(g, show_ports=True)

Just show structure:
    >>> from dsl.utils.visualize import print_network_hierarchy
    >>> print_network_hierarchy(g, show_ports=True)

Just show connections:
    >>> from dsl.utils.visualize import print_connections
    >>> print_connections(g)

Just show summary:
    >>> from dsl.utils.visualize import print_summary
    >>> print_summary(g)

Compile manually before visualizing:
    >>> g.compile()
    >>> visualize(g, compile_first=False)

**For Teaching:**

This tool is invaluable for:
1. Showing students what their network actually looks like
2. Explaining fanout/fanin patterns
3. Debugging connection issues
4. Understanding automatic agent insertion
5. Verifying network topology before running

**Note:** Requires the 'rich' library for colorized output.
If rich is not installed, install it with: pip install rich
"""

from rich.console import Console
from rich.tree import Tree
from rich.text import Text
from typing import Optional

from dissyslab.core import Network, Agent

console = Console()


def print_network_hierarchy(network: Network, show_ports: bool = False):
    """
    Prints a visual tree of the network/agent hierarchy.

    Shows the logical structure of blocks in the network, including
    any auto-inserted Broadcast/Merge agents after compilation.

    Args:
        network: The Network to visualize
        show_ports: If True, show input/output ports for each agent

    Example:
        >>> g = network([(source, transform), (transform, sink)])
        >>> print_network_hierarchy(g)
        Network
        ├── Source@abc123
        ├── Transform@def456
        └── Sink@ghi789
    """
    console.rule("[bold blue]Network Structure[/bold blue]")

    network_name = network.name or "Network"
    tree = Tree(Text(network_name, style="bold blue"))

    # Show logical blocks (before compilation)
    if hasattr(network, "blocks") and network.blocks:
        blocks_tree = tree.add(Text("Blocks (Logical)", style="cyan"))
        for block_name, block_obj in network.blocks.items():
            _add_block_node(blocks_tree, block_name, block_obj, show_ports)

    # Show compiled agents (after compilation)
    if hasattr(network, "agents") and network.agents:
        agents_tree = tree.add(Text("Agents (Compiled)", style="yellow"))
        for agent_path, agent_obj in network.agents.items():
            _add_agent_node(agents_tree, agent_path, agent_obj, show_ports)

    console.print(tree)


def _add_block_node(tree: Tree, name: str, block, show_ports: bool):
    """Add a block node to the tree."""
    if isinstance(block, Agent):
        # It's an agent
        class_name = block.__class__.__name__
        label = Text(f"{name} ", style="green")
        label.append(f"({class_name})", style="dim green")

        if show_ports:
            label.append(f" in=[{', '.join(block.inports)}] out=[{', '.join(block.outports)}]",
                         style="dim")

        node = tree.add(label)
    else:
        # It's a nested network
        label = Text(f"{name} ", style="cyan")
        label.append("(Network)", style="dim cyan")
        node = tree.add(label)

        # Recursively add children
        if hasattr(block, "blocks"):
            for child_name, child_block in block.blocks.items():
                _add_block_node(node, child_name, child_block, show_ports)


def _add_agent_node(tree: Tree, path: str, agent: Agent, show_ports: bool):
    """Add an agent node to the tree (for compiled agents)."""
    class_name = agent.__class__.__name__

    # Use just the last part of the path for display
    display_name = path.split(".")[-1]

    label = Text(f"{display_name} ", style="green")
    label.append(f"({class_name})", style="dim green")

    if show_ports:
        label.append(f" in=[{', '.join(agent.inports)}] out=[{', '.join(agent.outports)}]",
                     style="dim")

    tree.add(label)


def print_connections(network: Network, compile_first: bool = False):
    """
    Prints colorized connections after compilation.

    Shows all port-to-port connections in the compiled network,
    including connections to auto-inserted Broadcast/Merge agents.

    Args:
        network: The Network to visualize
        compile_first: If True, compile the network before showing connections

    Format: 
        [block_path ⤏ port] -> [block_path ⤏ port]

    Example:
        >>> g = network([(source, transform), (transform, sink)])
        >>> print_connections(g, compile_first=True)
        root⤏Source@abc ⤏ out -> root⤏Transform@def ⤏ in
        root⤏Transform@def ⤏ out -> root⤏Sink@ghi ⤏ in
    """
    console.rule("[bold green]Connections (After Compilation)[/bold green]")

    # Check if network is compiled
    if not hasattr(network, "graph_connections") or network.graph_connections is None:
        if compile_first:
            console.print("[yellow]Compiling network...[/yellow]")
            network.compile()
            print()
        else:
            console.print(
                "[yellow]Network not compiled yet. "
                "Call network.compile() first or use compile_first=True.[/yellow]"
            )
            return

    if not network.graph_connections:
        console.print("[yellow]No connections found.[/yellow]")
        return

    # Print each connection
    for from_block, from_port, to_block, to_port in network.graph_connections:
        # Format left side
        from_text = Text()
        from_text.append(_format_block_path(from_block), style="red")
        from_text.append(" ⤏ ", style="dim white")
        from_text.append(from_port, style="blue")

        # Arrow
        arrow_text = Text(" -> ", style="bold white")

        # Format right side
        to_text = Text()
        to_text.append(_format_block_path(to_block), style="red")
        to_text.append(" ⤏ ", style="dim white")
        to_text.append(to_port, style="blue")

        # Print combined
        console.print(from_text + arrow_text + to_text)


def _format_block_path(path: str) -> str:
    """
    Replace dots in block path with ⤏ for visual clarity.

    Example: 
        "root.block_0.agent" -> "root⤏block_0⤏agent"
    """
    return path.replace(".", "⤏")


def print_summary(network: Network):
    """
    Print a summary of the network: agents, connections, and detected patterns.

    Args:
        network: The Network to summarize
    """
    console.rule("[bold magenta]Network Summary[/bold magenta]")

    # Count agents by type
    if hasattr(network, "agents") and network.agents:
        from collections import Counter
        agent_types = Counter(
            agent.__class__.__name__ for agent in network.agents.values())

        console.print("[bold]Agent Types:[/bold]")
        for agent_type, count in sorted(agent_types.items()):
            console.print(f"  • {agent_type}: {count}")
        console.print()

    # Connection count
    if hasattr(network, "graph_connections") and network.graph_connections:
        console.print(
            f"[bold]Total Connections:[/bold] {len(network.graph_connections)}")
        console.print()

    # Detect patterns
    if hasattr(network, "agents") and network.agents:
        broadcast_count = sum(1 for a in network.agents.values()
                              if a.__class__.__name__ == "Broadcast")
        merge_count = sum(1 for a in network.agents.values()
                          if a.__class__.__name__ == "MergeAsynch")

        if broadcast_count > 0 or merge_count > 0:
            console.print("[bold]Detected Patterns:[/bold]")
            if broadcast_count > 0:
                console.print(f"  • Fanout (Broadcast): {broadcast_count}")
            if merge_count > 0:
                console.print(f"  • Fanin (Merge): {merge_count}")


def visualize(network: Network,
              compile_first: bool = True,
              show_ports: bool = False,
              show_summary: bool = True):
    """
    Complete visualization: structure, connections, and summary.

    Main entry point for network visualization. Shows everything you need
    to understand and debug a network.

    Args:
        network: The Network to visualize
        compile_first: If True, compile before showing connections
        show_ports: If True, show port names for each agent
        show_summary: If True, show summary statistics

    Example:
        >>> from dsl import network
        >>> from dsl.utils.visualize import visualize
        >>> 
        >>> g = network([
        ...     (twitter, clean),
        ...     (reddit, clean),
        ...     (clean, sentiment),
        ...     (clean, urgency),
        ...     (sentiment, logger),
        ...     (urgency, logger)
        ... ])
        >>> 
        >>> visualize(g)
    """
    # Compile if requested
    if compile_first and not hasattr(network, "graph_connections"):
        console.print("[yellow]Compiling network...[/yellow]")
        network.compile()
        print()

    # Show structure
    print_network_hierarchy(network, show_ports=show_ports)
    print()

    # Show connections
    print_connections(network, compile_first=False)
    print()

    # Show summary
    if show_summary:
        print_summary(network)
        print()


# Convenience alias
draw = visualize


__all__ = [
    "visualize",
    "draw",
    "print_network_hierarchy",
    "print_connections",
    "print_summary"
]
