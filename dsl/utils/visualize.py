# visualize.py

from rich.console import Console
from rich.tree import Tree
from rich.text import Text
from typing import Union
from dsl.core import Network, Block, RunnableBlock

console = Console()


def print_block_hierarchy(block: Block):
    """
    Prints a visual tree of the block hierarchy using rich.

    Parameters:
    - block: The top-level block (e.g., Network) with .name and .blocks.
    """
    console.rule("[bold blue]Block Hierarchy[/bold blue]")  # 🆕 Heading
    tree = Tree(
        Text(f"{block.name}", style="blue"))
    _add_block_children(block, tree)
    console.print(tree)


def _add_block_children(block: Block, tree: Tree):
    """
    Recursively adds children of a block to the rich tree.
    """
    if not hasattr(block, "blocks"):
        return

    for child_name, child_block in block.blocks.items():
        if isinstance(child_block, RunnableBlock):
            label = Text(child_block.name or child_name, style="green")
        else:
            label = Text(child_block.name or child_name, style="red")

        subtree = tree.add(label)

        # Recursive call
        _add_block_children(child_block, subtree)


def print_graph_connections_only(block: Block):
    """
    Prints a colorized list of graph-level connections using rich.

    Each connection is shown as:
    [block_path ⤏ ...] port_name -> [block_path ⤏ ...] port_name

    Colors:
    - Block names: red
    - Port names: blue
    - Arrow: white
    """
    console.rule("[bold green]Port Connections[/bold green]")  # 🆕 Heading

    if not hasattr(block, "graph_connections"):
        console.print(
            "[bold red]Error:[/bold red] block has no attribute 'graph_connections'")
        return

    for from_block, from_port, to_block, to_port in block.graph_connections:
        # Format left-hand side
        from_text = Text()
        from_text.append(_format_block_path(from_block), style="red")
        from_text.append(" ")
        from_text.append(from_port, style="blue")

        # Arrow
        arrow_text = Text(" -> ", style="white")

        # Format right-hand side
        to_text = Text()
        to_text.append(_format_block_path(to_block), style="red")
        to_text.append(" ")
        to_text.append(to_port, style="blue")

        # Combine and print
        connection_text = from_text + arrow_text + to_text
        console.print(connection_text)


def _format_block_path(path: str) -> str:
    """
    Replaces dots in a full block path with ⤏ for better visual separation.
    Example: block_top.block_0.A0 -> block_top⤏block_0⤏A0
    """
    return path.replace(".", "⤏")


def draw(block: Block):
    print_block_hierarchy(block)
    print("\n")
    print_graph_connections_only(block)
    print("\n \n \n")
