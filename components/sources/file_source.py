# components/sources/file_source.py

"""
File Source - Read CSV/JSON files from filesystem

This is the REAL version that reads actual files.
Same interface as demo_file.py - easy to swap!

Compare with demo_file.py to see the demo → real pattern.
"""

import json
import csv
import os


class FileSource:
    """
    Read CSV or JSON files from filesystem.

    Same interface as DemoFileSource - just change the import!

    Args:
        filepath: Path to file
        format: "csv" | "json" | "jsonl" (auto-detected if not specified)
        encoding: File encoding (default: "utf-8")

    Returns:
        Dict for each row/item (same as demo version)

    Example:
        >>> from components.sources.file_source import FileSource
        >>> source = FileSource("data/customers.csv", format="csv")
        >>> for customer in source.run():
        ...     print(customer["name"])
    """

    def __init__(self, filepath, format=None, encoding="utf-8"):
        """
        Initialize file source.

        Args:
            filepath: Path to file
            format: "csv" | "json" | "jsonl" (auto-detected from extension if None)
            encoding: File encoding (default: "utf-8")
        """
        self.filepath = filepath
        self.encoding = encoding

        # Check file exists
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"File not found: {filepath}\n"
                f"Current directory: {os.getcwd()}\n"
                f"Check:\n"
                f"  1. File path is correct\n"
                f"  2. You're in the right directory\n"
                f"  3. File name spelling is correct"
            )

        # Auto-detect format from extension if not specified
        if format is None:
            ext = os.path.splitext(filepath)[1].lower()
            if ext == ".csv":
                format = "csv"
            elif ext == ".json":
                format = "json"
            elif ext == ".jsonl":
                format = "jsonl"
            else:
                raise ValueError(
                    f"Cannot auto-detect format from extension: {ext}\n"
                    f"Please specify format='csv', 'json', or 'jsonl'"
                )

        # Validate format
        if format not in ["csv", "json", "jsonl"]:
            raise ValueError(
                f"Unsupported format: {format}\n"
                f"Supported formats: csv, json, jsonl"
            )

        self.format = format

        print(f"[FileSource] Reading {filepath} as {format}")

    def run(self):
        """
        Yield items from file.

        - CSV: Yields each row as dict (using headers)
        - JSON: Yields each item from array
        - JSONL: Yields each line as separate JSON object

        Returns None when complete.
        """
        try:
            if self.format == "csv":
                yield from self._read_csv()
            elif self.format == "json":
                yield from self._read_json()
            elif self.format == "jsonl":
                yield from self._read_jsonl()
        except UnicodeDecodeError as e:
            raise ValueError(
                f"Encoding error reading {self.filepath}\n"
                f"Current encoding: {self.encoding}\n"
                f"Try: FileSource('{self.filepath}', encoding='latin-1')\n"
                f"Error: {e}"
            )

        return None

    def _read_csv(self):
        """Read CSV file, yield rows as dicts."""
        with open(self.filepath, 'r', encoding=self.encoding, newline='') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Skip empty rows
                if not any(row.values()):
                    continue

                # Try to convert numeric strings to numbers
                converted_row = {}
                for key, value in row.items():
                    converted_row[key] = self._try_convert_number(value)

                yield converted_row

    def _read_json(self):
        """Read JSON file (expects array), yield each item."""
        with open(self.filepath, 'r', encoding=self.encoding) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON in {self.filepath}\n"
                    f"Error: {e}\n"
                    f"Check:\n"
                    f"  1. File is valid JSON\n"
                    f"  2. Contains an array: [{...}, {...}]\n"
                    f"  3. No trailing commas"
                )

            # Expect array of objects
            if not isinstance(data, list):
                raise ValueError(
                    f"JSON file must contain an array, not {type(data).__name__}\n"
                    f"Expected: [{...}, {...}]\n"
                    f"Got: {str(data)[:100]}..."
                )

            for item in data:
                yield item

    def _read_jsonl(self):
        """Read JSON Lines file, yield each line as object."""
        with open(self.filepath, 'r', encoding=self.encoding) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines
                if not line:
                    continue

                try:
                    item = json.loads(line)
                    yield item
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"Invalid JSON on line {line_num} of {self.filepath}\n"
                        f"Line: {line[:100]}...\n"
                        f"Error: {e}"
                    )

    def _try_convert_number(self, value):
        """Try to convert string to int or float."""
        if not isinstance(value, str):
            return value

        # Try int
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        # Return as string
        return value


# Test when run directly
if __name__ == "__main__":
    import sys

    print("File Source - Test")
    print("=" * 60)

    # Create a test CSV file
    test_csv = "test_data.csv"
    with open(test_csv, 'w') as f:
        f.write("id,name,age\n")
        f.write("1,Alice,28\n")
        f.write("2,Bob,34\n")
        f.write("3,Carol,45\n")

    # Test CSV
    print("\nTest 1: CSV File")
    print("-" * 60)
    source = FileSource(test_csv, format="csv")
    for item in source.run():
        print(f"  {item}")

    # Create a test JSON file
    test_json = "test_data.json"
    with open(test_json, 'w') as f:
        json.dump([
            {"id": 1, "name": "Alice", "age": 28},
            {"id": 2, "name": "Bob", "age": 34}
        ], f)

    # Test JSON
    print("\nTest 2: JSON File")
    print("-" * 60)
    source = FileSource(test_json, format="json")
    for item in source.run():
        print(f"  {item}")

    # Create a test JSONL file
    test_jsonl = "test_data.jsonl"
    with open(test_jsonl, 'w') as f:
        f.write('{"id": 1, "name": "Alice"}\n')
        f.write('{"id": 2, "name": "Bob"}\n')

    # Test JSONL
    print("\nTest 3: JSONL File")
    print("-" * 60)
    source = FileSource(test_jsonl, format="jsonl")
    for item in source.run():
        print(f"  {item}")

    # Cleanup
    os.remove(test_csv)
    os.remove(test_json)
    os.remove(test_jsonl)

    print("\n" + "=" * 60)
    print("✓ File Source works!")
