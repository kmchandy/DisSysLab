# components/sinks/demo_file_writer.py

"""
Demo File Writer - Show what would be written to file

This demo version prints to console instead of writing files.
Perfect for learning without creating actual files!

Compare with file_writer.py to see the demo → real pattern.
"""

import json


class DemoFileWriter:
    """
    Demo file writer - prints instead of writing.

    Shows what would be written to file without actual file I/O.
    Perfect for learning the sink pattern.

    Args:
        filename: Filename to simulate writing to
        format: "json" | "jsonl" | "csv" | "text"

    Example:
        >>> from components.sinks.demo_file_writer import DemoFileWriter
        >>> writer = DemoFileWriter(filename="output.json", format="json")
        >>> writer.run({"id": 1, "name": "Alice"})
        >>> writer.run({"id": 2, "name": "Bob"})
        >>> writer.finalize()
    """

    def __init__(self, filename="output.json", format="json"):
        """
        Initialize demo file writer.

        Args:
            filename: Filename to simulate (not actually created)
            format: "json" | "jsonl" | "csv" | "text"
        """
        self.filename = filename
        self.format = format
        self.items = []

        print(f"[DemoFileWriter] Would write to: {filename}")
        print(f"[DemoFileWriter] Format: {format}")

    def run(self, item):
        """
        Process one item (collect for later display).

        Args:
            item: Dict or any object to write
        """
        self.items.append(item)
        # Show brief preview
        item_str = str(item)
        if len(item_str) > 60:
            item_str = item_str[:57] + "..."
        print(f"[DemoFileWriter] Item {len(self.items)}: {item_str}")

    def finalize(self):
        """
        Show what the file would look like.

        Called at the end of the stream.
        """
        print(f"\n[DemoFileWriter] File complete: {len(self.items)} items")
        print("=" * 70)
        print(f"Preview of {self.filename}:")
        print("=" * 70)

        if self.format == "json":
            self._show_json()
        elif self.format == "jsonl":
            self._show_jsonl()
        elif self.format == "csv":
            self._show_csv()
        elif self.format == "text":
            self._show_text()
        else:
            print(f"Unknown format: {self.format}")

        print("=" * 70)

    def _show_json(self):
        """Show JSON array format."""
        # Pretty-print first 3 items
        preview_items = self.items[:3]
        json_str = json.dumps(preview_items, indent=2, ensure_ascii=False)

        # If we have more items, show count
        if len(self.items) > 3:
            # Remove the closing bracket
            json_str = json_str.rstrip('\n]')
            print(json_str)
            print(f"  ... and {len(self.items) - 3} more items")
            print("]")
        else:
            print(json_str)

    def _show_jsonl(self):
        """Show JSON Lines format."""
        # One JSON object per line
        for i, item in enumerate(self.items[:3]):
            print(json.dumps(item, ensure_ascii=False))

        if len(self.items) > 3:
            print(f"... and {len(self.items) - 3} more lines")

    def _show_csv(self):
        """Show CSV format."""
        if not self.items:
            print("(empty)")
            return

        # Get column headers from first item
        if isinstance(self.items[0], dict):
            headers = list(self.items[0].keys())
            print(",".join(headers))

            # Show first 3 rows
            for item in self.items[:3]:
                values = [str(item.get(h, "")) for h in headers]
                print(",".join(values))

            if len(self.items) > 3:
                print(f"... and {len(self.items) - 3} more rows")
        else:
            # Not dicts, just show as-is
            for item in self.items[:3]:
                print(str(item))
            if len(self.items) > 3:
                print(f"... and {len(self.items) - 3} more rows")

    def _show_text(self):
        """Show plain text format."""
        for item in self.items[:5]:
            print(str(item))

        if len(self.items) > 5:
            print(f"... and {len(self.items) - 5} more lines")


# Test when run directly
if __name__ == "__main__":
    print("Demo File Writer - Test")
    print("=" * 70)

    # Test JSON format
    print("\nTest 1: JSON Format")
    print("-" * 70)
    writer = DemoFileWriter(filename="customers.json", format="json")
    writer.run({"id": 1, "name": "Alice", "age": 28})
    writer.run({"id": 2, "name": "Bob", "age": 34})
    writer.run({"id": 3, "name": "Carol", "age": 45})
    writer.run({"id": 4, "name": "David", "age": 31})
    writer.finalize()

    # Test JSONL format
    print("\n\nTest 2: JSONL Format")
    print("-" * 70)
    writer = DemoFileWriter(filename="events.jsonl", format="jsonl")
    writer.run({"type": "login", "user": "alice"})
    writer.run({"type": "purchase", "user": "bob"})
    writer.run({"type": "logout", "user": "alice"})
    writer.finalize()

    # Test CSV format
    print("\n\nTest 3: CSV Format")
    print("-" * 70)
    writer = DemoFileWriter(filename="data.csv", format="csv")
    writer.run({"name": "Alice", "age": 28, "city": "NYC"})
    writer.run({"name": "Bob", "age": 34, "city": "SF"})
    writer.run({"name": "Carol", "age": 45, "city": "Chicago"})
    writer.finalize()

    print("\n" + "=" * 70)
    print("✓ Demo File Writer works!")
