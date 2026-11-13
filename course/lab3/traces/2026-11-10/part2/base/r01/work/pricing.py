"""Order pricing for the shop.

Orders of $100 or more get 10% off. Smaller orders pay full price.
"""


def discount(total: float) -> float:
    """The price to charge for an order of `total` dollars."""
    return total * 0.9 if total >= 100 else total
