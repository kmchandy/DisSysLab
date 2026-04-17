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
        >>> while True:
        ...     customer = source.run()
        ...     if customer is None:
        ...         break
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
        self.n = 0
        self.data = []
        
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
        
        # Load all data at initialization
        self._load_data()
        
        print(f"[FileSource] Loaded {len(self.data)} items from {filepath} ({format})")
    
    def _load_data(self):
        """Load all data from file into self.data."""
        try:
            if self.format == "csv":
                self._load_csv()
            elif self.format == "json":
                self._load_json()
            elif self.format == "jsonl":
                self._load_jsonl()
        except UnicodeDecodeError as e:
            raise ValueError(
                f"Encoding error reading {self.filepath}\n"
                f"Current encoding: {self.encoding}\n"
                f"Try: FileSource('{self.filepath}', encoding='latin-1')\n"
                f"Error: {e}"
            )
    
    def _load_csv(self):
        """Load CSV file into self.data."""
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
                
                self.data.append(converted_row)
    
    def _load_json(self):
        """Load JSON file (expects array) into self.data."""
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
            
            self.data = data
    
    def _load_jsonl(self):
        """Load JSON Lines file into self.data."""
        with open(self.filepath, 'r', encoding=self.encoding) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                try:
                    item = json.loads(line)
                    self.data.append(item)
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
    
    def run(self):
        """
        Return next item from file.
        
        Returns None when complete (signals end of stream).
        """
        v = self.data[self.n] if self.n < len(self.data) else None
        self.n += 1
        return v


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
    finished = False
    while not finished:
        item = source.run()
        if item:
            print(f"  {item}")
        finished = item is None
    
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
    finished = False
    while not finished:
        item = source.run()
        if item:
            print(f"  {item}")
        finished = item is None
    
    # Create a test JSONL file
    test_jsonl = "test_data.jsonl"
    with open(test_jsonl, 'w') as f:
        f.write('{"id": 1, "name": "Alice"}\n')
        f.write('{"id": 2, "name": "Bob"}\n')
    
    # Test JSONL
    print("\nTest 3: JSONL File")
    print("-" * 60)
    source = FileSource(test_jsonl, format="jsonl")
    finished = False
    while not finished:
        item = source.run()
        if item:
            print(f"  {item}")
        finished = item is None
    
    # Cleanup
    os.remove(test_csv)
    os.remove(test_json)
    os.remove(test_jsonl)
    
    print("\n" + "=" * 60)
    print("✓ File Source works!")