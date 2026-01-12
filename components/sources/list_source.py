# components/sources/list_source.py

"""
ListSource: Simple source that yields items from a list.

This is a basic source used for testing and examples.
Perfect for when you need a simple data source without external dependencies.
"""

from typing import List, Any


class ListSource:
    """
    Simple source that yields items from a list.

    This is designed to work with the DSL's source_map decorator
    and provides an easy way to create test data streams.

    Example:
        >>> from components.sources import ListSource
        >>> source = ListSource(["hello", "world"])
        >>> for item in source.run():
        ...     print(item)
        hello
        world
    """

    def __init__(self, items: List[Any], name: str = "list_source"):
        """
        Initialize the list source.

        Args:
            items: List of items to yield
            name: Name for this source (for debugging)
        """
        self.items = items
        self.name = name
        self.count = 0

    def run(self):
        """
        Generator that yields each item from the list.

        Yields:
            Items from the list, one at a time
        """
        for item in self.items:
            self.count += 1
            yield item

    def get_stats(self):
        """Get statistics for this source."""
        return {
            "name": self.name,
            "total_items": len(self.items),
            "items_yielded": self.count
        }

    def print_stats(self):
        """Print statistics in a readable format."""
        stats = self.get_stats()
        print()
        print("=" * 60)
        print(f"List Source Statistics: {stats['name']}")
        print("=" * 60)
        print(f"Total items:    {stats['total_items']}")
        print(f"Items yielded:  {stats['items_yielded']}")
        print("=" * 60)
        print()
