# components/sources/list_source.py

"""
ListSource: Simple source that returns next item from a list.

This is a basic source used for testing and examples.
"""

from typing import List, Any


class ListSource:

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
        output_msg = self.items[self.count] if self.count < len(
            self.items) else None
        self.count += 1
        return output_msg
