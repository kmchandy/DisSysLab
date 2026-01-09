# dsl/connectors/sources_simple.py

"""
Simple data sources for teaching purposes.

These are example source objects that have a .run() method.
Students can use these as-is or as templates for their own sources.
"""


class ListSource:
    """
    Emit items from a list, one at a time.

    Example:
        >>> posts = [
        ...     {"text": "Hello world"},
        ...     {"text": "Python is great"}
        ... ]
        >>> data = ListSource(posts)
        >>> source = Source(data=data)
    """

    def __init__(self, items):
        """
        Args:
            items: List of items to emit
        """
        self.items = items
        self.index = 0

    def run(self):
        """Returns next item or None when exhausted."""
        if self.index >= len(self.items):
            return None

        item = self.items[self.index]
        self.index += 1
        return item


class RangeSource:
    """
    Generate a sequence of numbers.

    Example:
        >>> # Generate numbers 0-9
        >>> data = RangeSource(10)
        >>> source = Source(data=data)
        >>> 
        >>> # Generate numbers 5-14
        >>> data = RangeSource(5, 15)
        >>> source = Source(data=data)
    """

    def __init__(self, start, stop=None):
        """
        Args:
            start: Starting number (or stop if stop is None)
            stop: Ending number (exclusive)
        """
        if stop is None:
            self.current = 0
            self.stop = start
        else:
            self.current = start
            self.stop = stop

    def run(self):
        """Returns next number or None when exhausted."""
        if self.current >= self.stop:
            return None

        value = {"value": self.current}
        self.current += 1
        return value


class CounterSource:
    """
    Count up to a maximum value.

    Example:
        >>> # Count from 1 to 5
        >>> data = CounterSource(max_count=5)
        >>> source = Source(data=data)
    """

    def __init__(self, max_count):
        """
        Args:
            max_count: Maximum count value
        """
        self.count = 0
        self.max_count = max_count

    def run(self):
        """Returns next count or None when done."""
        if self.count >= self.max_count:
            return None

        self.count += 1
        return {"count": self.count}


class FileLineSource:
    """
    Read lines from a file, one at a time.

    Example:
        >>> data = FileLineSource("posts.txt")
        >>> source = Source(data=data)
    """

    def __init__(self, filename):
        """
        Args:
            filename: Path to file to read
        """
        self.filename = filename
        self.file = None
        self.opened = False

    def run(self):
        """Returns next line or None when file ends."""
        # Open file on first call
        if not self.opened:
            self.file = open(self.filename, 'r')
            self.opened = True

        # Read next line
        line = self.file.readline()

        # If empty, we've reached end of file
        if not line:
            self.file.close()
            return None

        # Return line with whitespace stripped
        return {"text": line.strip()}


__all__ = ["ListSource", "RangeSource", "CounterSource", "FileLineSource"]
