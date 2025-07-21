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


# def print_connections_only(block: Union[Network, Block], name: str = "block_top", tree: Tree = None):
#     """
#     Visualizes connections in a compiled network using rich formatting.

#     Parameters:
#     - block: A compiled Network or Block instance.
#     - name: Name to display for the current block (default: "block_top").
#     - tree: Internal parameter used for recursion; leave as None when calling.
#     """
#     if not hasattr(block, "graph_connections"):
#         console.print(
#             f"[bold red]Error:[/bold red] The block '{name}' has not been compiled.")
#         return


#     # Create top-level tree if this is the initial call
#     is_root = tree is None
#     if is_root:
#         tree = Tree(
#             Text(f"Connections in [yellow]{name}[/yellow]", style="bold magenta"))

#     for (from_block_name, from_port, to_block_name, to_port,) in block.graph_connections:
#         from_block_short = _shorten_block_name(from_block_name)
#         to_block_short = _shorten_block_name(to_block_name)
#         edge_text = Text()
#         edge_text.append(from_block_short, style="cyan")
#         edge_text.append(from_port, style="white")
#         edge_text.append(" ─▶ ", style="red")
#         edge_text.append(to_block_short, style="cyan")
#         edge_text.append(to_port, style="white")
#         tree.add(edge_text)

#     # Recurse into sub-blocks if any
#     for subname, subblock in getattr(block, "_compiled_blocks", {}).items():
#         subtree = tree.add(
#             Text(f"Connections in [yellow]{subname}[/yellow]", style="brown"))
#         print_connections_only(subblock, subname, subtree)

#     # Print the entire tree if root
#     if is_root:
#         console.print(tree)


# def _shorten_block_name(block_name: str) -> str:
#     """
#     Shortens a full path like 'block_top.block_0.out' to 'block_0.out'
#     """
#     if not "." in block_name:
#         return block_name
#     else:
#         last_name = _shorten_block_name.split('.')[-1]
#         return last_name
