# components/sinks/file_writer.py

"""
File Writer - Write data to files on disk

This is the REAL version that creates actual files.
Same interface as demo_file_writer.py - easy to swap!

Compare with demo_file_writer.py to see the demo → real pattern.
"""

import json
import csv
import os


class FileWriter:
    """
    Write data to files on disk.

    Same interface as DemoFileWriter - just change the import!

    Args:
        filepath: Path where file will be written
        format: "json" | "jsonl" | "csv" | "text"
        mode: "w" (overwrite) | "a" (append) - default: "w"

    Formats:
        json: Pretty-printed JSON array [{...}, {...}]
        jsonl: JSON Lines, one object per line (streaming)
        csv: CSV with headers from first item's keys
        text: Plain text, one item per line

    Example:
        >>> from components.sinks.file_writer import FileWriter
        >>> writer = FileWriter("output.json", format="json")
        >>> # Use in network, file gets written automatically
    """

    def __init__(self, filepath, format="json", mode="w"):
        """
        Initialize file writer.

        Args:
            filepath: Path where file will be written
            format: "json" | "jsonl" | "csv" | "text"
            mode: "w" (overwrite) | "a" (append)
        """
        self.filepath = filepath
        self.format = format
        self.mode = mode
        self.items = []
        self.file_handle = None
        self.csv_writer = None

        # Validate format
        if format not in ["json", "jsonl", "csv", "text"]:
            raise ValueError(
                f"Unsupported format: {format}\n"
                f"Supported formats: json, jsonl, csv, text"
            )

        # Create directory if it doesn't exist
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            print(f"[FileWriter] Created directory: {directory}")

        # Open file immediately for streaming formats
        if format in ["jsonl", "text"]:
            try:
                self.file_handle = open(filepath, mode, encoding="utf-8")
            except IOError as e:
                raise IOError(
                    f"Cannot open {filepath} for writing\n"
                    f"Error: {e}\n"
                    f"Check:\n"
                    f"  1. File isn't open in another program\n"
                    f"  2. You have write permissions\n"
                    f"  3. Directory exists"
                )

        # CSV needs special handling
        if format == "csv":
            try:
                self.file_handle = open(
                    filepath, mode, newline='', encoding="utf-8")
            except IOError as e:
                raise IOError(
                    f"Cannot open {filepath} for writing\n"
                    f"Error: {e}"
                )

        print(f"[FileWriter] Writing to: {filepath} ({format})")

    def run(self, item):
        """
        Write one item to file.

        Args:
            item: Dict or any object to write
        """
        if self.format == "json":
            # Collect all items, write in finalize
            self.items.append(item)

        elif self.format == "jsonl":
            # Write immediately (one JSON object per line)
            self.file_handle.write(json.dumps(item, ensure_ascii=False) + "\n")
            self.items.append(item)  # Track count

        elif self.format == "csv":
            # First item: create CSV writer with headers
            if self.csv_writer is None:
                if isinstance(item, dict):
                    fieldnames = list(item.keys())
                    self.csv_writer = csv.DictWriter(
                        self.file_handle,
                        fieldnames=fieldnames
                    )
                    self.csv_writer.writeheader()
                else:
                    raise ValueError(
                        f"CSV format requires dict items, got {type(item).__name__}\n"
                        f"Item: {item}"
                    )

            # Write row
            self.csv_writer.writerow(item)
            self.items.append(item)  # Track count

        elif self.format == "text":
            # Write as string
            self.file_handle.write(str(item) + "\n")
            self.items.append(item)  # Track count

    def finalize(self):
        """
        Flush and close file.

        Called at the end of the stream.
        """
        if self.format == "json":
            # Write all items as JSON array
            try:
                with open(self.filepath, self.mode, encoding="utf-8") as f:
                    json.dump(self.items, f, indent=2, ensure_ascii=False)
                print(
                    f"[FileWriter] Wrote {len(self.items)} items to {self.filepath}")
            except IOError as e:
                raise IOError(
                    f"Error writing to {self.filepath}\n"
                    f"Error: {e}"
                )
        else:
            # Already written (streaming), just close
            if self.file_handle:
                self.file_handle.close()

            print(
                f"[FileWriter] Wrote {len(self.items)} items to {self.filepath}")

        # Show file size
        if os.path.exists(self.filepath):
            size = os.path.getsize(self.filepath)
            if size < 1024:
                size_str = f"{size} bytes"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            print(f"[FileWriter] File size: {size_str}")


# Test when run directly
if __name__ == "__main__":
    import os

    print("File Writer - Test")
    print("=" * 70)

    # Test JSON format
    print("\nTest 1: JSON Format")
    print("-" * 70)
    writer = FileWriter("test_output.json", format="json")
    writer.run({"id": 1, "name": "Alice", "age": 28})
    writer.run({"id": 2, "name": "Bob", "age": 34})
    writer.run({"id": 3, "name": "Carol", "age": 45})
    writer.finalize()

    # Verify
    with open("test_output.json") as f:
        data = json.load(f)
        print(f"✓ Wrote {len(data)} items")
        print(f"  First item: {data[0]}")

    # Test JSONL format
    print("\nTest 2: JSONL Format")
    print("-" * 70)
    writer = FileWriter("test_output.jsonl", format="jsonl")
    writer.run({"type": "login", "user": "alice"})
    writer.run({"type": "purchase", "user": "bob"})
    writer.finalize()

    # Verify
    with open("test_output.jsonl") as f:
        lines = f.readlines()
        print(f"✓ Wrote {len(lines)} lines")
        print(f"  First line: {lines[0].strip()}")

    # Test CSV format
    print("\nTest 3: CSV Format")
    print("-" * 70)
    writer = FileWriter("test_output.csv", format="csv")
    writer.run({"name": "Alice", "age": 28, "city": "NYC"})
    writer.run({"name": "Bob", "age": 34, "city": "SF"})
    writer.finalize()

    # Verify
    with open("test_output.csv") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        print(f"✓ Wrote {len(rows)} rows")
        print(f"  First row: {rows[0]}")

    # Cleanup
    os.remove("test_output.json")
    os.remove("test_output.jsonl")
    os.remove("test_output.csv")

    print("\n" + "=" * 70)
    print("✓ File Writer works!")
