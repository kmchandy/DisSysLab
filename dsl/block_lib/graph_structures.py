from dsl.core import Network


from dsl.core import Network


def pipeline(block_dict: dict) -> Network:
    """
    Build a linear pipeline from an ordered dict of named blocks.

    Parameters:
    - block_dict: Ordered dictionary {name: block} in execution order.

    Returns:
    - A Network with blocks and inferred connections.

    Example:
    >>> pipeline({
            "source": generate(...),
            "uppercase": transform(...),
            "sink": record(...)
        })
    """
    names = list(block_dict.keys())
    net = Network("pipeline", blocks=block_dict, connections=[])
    for i in range(len(names) - 1):
        net.connections.append((names[i], "out", names[i + 1], "in"))
    return net
