# TEMPLATES.md - Building Your Own Connectors

This guide provides **copy-paste templates** for building custom sources and sinks.

Each template includes:
- ✅ Complete working code
- ✅ Test section to verify it works
- ✅ Usage example in a network
- ✅ Link to real component example

**Quick Start:**
1. Copy template
2. Fill in TODOs
3. Run test section
4. Use in your network

---

## Table of Contents

**Source Templates:**
1. [Simple List Source](#template-1-simple-list-source) (easiest)
2. [File Reader Source](#template-2-file-reader-source)
3. [API Reader Source](#template-3-api-reader-source)
4. [Streaming Source](#template-4-streaming-source)

**Sink Templates:**
5. [Simple Collector Sink](#template-5-simple-collector-sink) (easiest)
6. [File Writer Sink](#template-6-file-writer-sink)
7. [API Poster Sink](#template-7-api-poster-sink)
8. [Batch Writer Sink](#template-8-batch-writer-sink)

**Common Patterns:**
9. [Pagination](#pattern-1-pagination)
10. [Rate Limiting](#pattern-2-rate-limiting)
11. [Error Recovery](#pattern-3-error-recovery)
12. [Authentication](#pattern-4-authentication)

---

# Source Templates

Sources produce data. They implement `run()` which returns one item at a time, then `None` when done.

## Template 1: Simple List Source

**Use when:** You have a list of data in memory

**Difficulty:** ⭐ Easiest

```python
# components/sources/my_simple_source.py

class MySimpleSource:
    """
    Template for a source that yields items from a list.
    
    Perfect for: Static data, test data, small datasets
    
    TODO: Replace self.data with your actual data!
    """
    
    def __init__(self):
        """Initialize with your data."""
        # TODO: Replace this with your data source
        self.data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Carol"}
        ]
        self.n = 0
        
        print(f"[MySimpleSource] Loaded {len(self.data)} items")
    
    def run(self):
        """
        Return next item.
        
        Returns None when all items are yielded.
        """
        v = self.data[self.n] if self.n < len(self.data) else None
        self.n += 1
        return v


# ============================================================================
# TEST THIS TEMPLATE
# ============================================================================

if __name__ == "__main__":
    print("Testing Simple List Source")
    print("=" * 60)
    
    # Test 1: Create source
    source = MySimpleSource()
    print("✓ Source created")
    
    # Test 2: Yield all items
    items = []
    while True:
        item = source.run()
        if item is None:
            break
        items.append(item)
        print(f"  Got item: {item}")
    
    # Test 3: Verify count
    print(f"\n✓ Yielded {len(items)} items")
    assert len(items) == 3, "Should yield 3 items"
    
    # Test 4: Verify returns None after exhausted
    assert source.run() is None
    print("✓ Returns None when exhausted")
    
    print("\n" + "=" * 60)
    print("✓ Simple List Source template works!")


# ============================================================================
# USE IN NETWORK
# ============================================================================

"""
Example usage in a network:

from dsl import network
from dsl.blocks import Source, Transform, Sink
from my_simple_source import MySimpleSource

# Create source
source = MySimpleSource()
source_node = Source(fn=source.run, name="my_source")

# Create transform
def add_greeting(item):
    item["greeting"] = f"Hello, {item['name']}!"
    return item

transform_node = Transform(fn=add_greeting, name="add_greeting")

# Create sink
def print_item(item):
    print(f"  {item['greeting']}")

sink_node = Sink(fn=print_item, name="printer")

# Build and run network
g = network([
    (source_node, transform_node),
    (transform_node, sink_node)
])

g.run_network()
"""

# ============================================================================
# REAL EXAMPLE
# ============================================================================

"""
See real implementation in:
    components/sources/demo_file.py (DemoFileSource)
    components/sources/demo_bluesky.py (DemoBlueSkySource)
"""
```

---

## Template 2: File Reader Source

**Use when:** Reading data from CSV, JSON, or text files

**Difficulty:** ⭐⭐ Medium

```python
# components/sources/my_file_source.py

import json
import csv
import os


class MyFileSource:
    """
    Template for reading files (CSV, JSON, JSONL).
    
    Perfect for: Data files, logs, exports
    
    TODO: Customize for your file format!
    """
    
    def __init__(self, filepath, format="json"):
        """
        Initialize file source.
        
        Args:
            filepath: Path to file
            format: "json" | "csv" | "jsonl" | "txt"
        """
        self.filepath = filepath
        self.format = format
        self.n = 0
        self.data = []
        
        # Check file exists
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        # Load file
        self._load_file()
        
        print(f"[MyFileSource] Loaded {len(self.data)} items from {filepath}")
    
    def _load_file(self):
        """Load file into memory."""
        if self.format == "json":
            with open(self.filepath, 'r') as f:
                self.data = json.load(f)
        
        elif self.format == "csv":
            with open(self.filepath, 'r') as f:
                reader = csv.DictReader(f)
                self.data = list(reader)
        
        elif self.format == "jsonl":
            with open(self.filepath, 'r') as f:
                for line in f:
                    if line.strip():
                        self.data.append(json.loads(line))
        
        elif self.format == "txt":
            with open(self.filepath, 'r') as f:
                self.data = [{"line": line.strip()} for line in f if line.strip()]
        
        else:
            raise ValueError(f"Unsupported format: {self.format}")
    
    def run(self):
        """Return next item from file."""
        v = self.data[self.n] if self.n < len(self.data) else None
        self.n += 1
        return v


# ============================================================================
# TEST THIS TEMPLATE
# ============================================================================

if __name__ == "__main__":
    print("Testing File Source")
    print("=" * 60)
    
    # Create test file
    test_file = "test_data.json"
    test_data = [
        {"id": 1, "value": "A"},
        {"id": 2, "value": "B"},
        {"id": 3, "value": "C"}
    ]
    
    with open(test_file, 'w') as f:
        json.dump(test_data, f)
    
    print(f"Created test file: {test_file}")
    
    # Test 1: Create source
    source = MyFileSource(test_file, format="json")
    print("✓ Source created")
    
    # Test 2: Read all items
    items = []
    while True:
        item = source.run()
        if item is None:
            break
        items.append(item)
        print(f"  Got item: {item}")
    
    # Test 3: Verify
    print(f"\n✓ Read {len(items)} items")
    assert len(items) == 3
    assert items[0]["value"] == "A"
    print("✓ Data matches expected")
    
    # Cleanup
    os.remove(test_file)
    print(f"✓ Cleaned up test file")
    
    print("\n" + "=" * 60)
    print("✓ File Source template works!")


# ============================================================================
# REAL EXAMPLE
# ============================================================================

"""
See real implementation in:
    components/sources/file_source.py (FileSource)
"""
```

---

## Template 3: API Reader Source

**Use when:** Fetching data from REST APIs

**Difficulty:** ⭐⭐⭐ Hard

```python
# components/sources/my_api_source.py

import requests
import time


class MyAPISource:
    """
    Template for reading from REST APIs.
    
    Perfect for: Public APIs, internal APIs, web services
    
    TODO: Customize for your API!
    """
    
    def __init__(self, api_url, max_items=100, params=None, headers=None):
        """
        Initialize API source.
        
        Args:
            api_url: Base API URL
            max_items: Maximum items to fetch
            params: Optional query parameters (dict)
            headers: Optional HTTP headers (dict)
        """
        self.api_url = api_url
        self.max_items = max_items
        self.params = params or {}
        self.headers = headers or {}
        self.n = 0
        self.data = []
        
        # Fetch data
        self._fetch_data()
        
        print(f"[MyAPISource] Fetched {len(self.data)} items from API")
    
    def _fetch_data(self):
        """Fetch data from API."""
        try:
            # TODO: Customize this for your API
            response = requests.get(
                self.api_url,
                params=self.params,
                headers=self.headers,
                timeout=30
            )
            
            # Check response
            response.raise_for_status()
            
            # Parse JSON
            data = response.json()
            
            # TODO: Customize parsing for your API response format
            # Example assumes API returns array directly
            if isinstance(data, list):
                self.data = data[:self.max_items]
            elif isinstance(data, dict) and "results" in data:
                # Common pattern: {"results": [...]}
                self.data = data["results"][:self.max_items]
            else:
                self.data = [data]  # Single item response
        
        except requests.exceptions.RequestException as e:
            print(f"[MyAPISource] API error: {e}")
            self.data = []
    
    def run(self):
        """Return next item from API response."""
        v = self.data[self.n] if self.n < len(self.data) else None
        self.n += 1
        return v


# ============================================================================
# TEST THIS TEMPLATE
# ============================================================================

if __name__ == "__main__":
    print("Testing API Source")
    print("=" * 60)
    
    # Test with a free public API
    # Using JSONPlaceholder - a free fake REST API
    api_url = "https://jsonplaceholder.typicode.com/posts"
    
    # Test 1: Create source
    source = MyAPISource(
        api_url=api_url,
        max_items=5,
        params={"userId": 1}
    )
    print("✓ Source created")
    
    # Test 2: Fetch items
    items = []
    while True:
        item = source.run()
        if item is None:
            break
        items.append(item)
        print(f"  Got item {item.get('id')}: {item.get('title', 'N/A')[:40]}...")
    
    # Test 3: Verify
    print(f"\n✓ Fetched {len(items)} items")
    assert len(items) > 0, "Should fetch at least one item"
    assert len(items) <= 5, "Should respect max_items"
    print("✓ API fetch successful")
    
    print("\n" + "=" * 60)
    print("✓ API Source template works!")


# ============================================================================
# REAL EXAMPLE
# ============================================================================

"""
See real implementation in:
    components/sources/bluesky_source.py (BlueSkySource)
    
Common APIs to try:
    - JSONPlaceholder: https://jsonplaceholder.typicode.com/
    - GitHub: https://api.github.com/
    - OpenWeather: https://openweathermap.org/api
"""
```

---

## Template 4: Streaming Source

**Use when:** Continuous data streams (WebSockets, event streams)

**Difficulty:** ⭐⭐⭐⭐ Advanced

```python
# components/sources/my_streaming_source.py

import time
from datetime import datetime, timezone


class MyStreamingSource:
    """
    Template for streaming continuous data.
    
    Perfect for: Real-time data, event streams, sensors
    
    TODO: Customize for your streaming source!
    """
    
    def __init__(self, max_items=None, lifetime=None):
        """
        Initialize streaming source.
        
        Args:
            max_items: Max items to collect (None = unlimited)
            lifetime: Max seconds to stream (None = unlimited)
        """
        self.max_items = max_items
        self.lifetime = lifetime
        self.start_time = None
        self.n = 0
        self.data = []
        
        # Connect and collect
        self._collect_stream()
        
        print(f"[MyStreamingSource] Collected {len(self.data)} items from stream")
    
    def _collect_stream(self):
        """
        Collect items from stream.
        
        TODO: Replace with your actual streaming logic!
        """
        self.start_time = datetime.now(timezone.utc)
        
        # TODO: Connect to your stream (WebSocket, event source, etc.)
        # This is a simulated stream for demonstration
        
        while not self._should_stop():
            # TODO: Replace with actual stream reading
            # For demo, we generate synthetic data
            item = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "value": f"item_{len(self.data) + 1}",
                "count": len(self.data) + 1
            }
            
            self.data.append(item)
            
            # Simulate delay between events
            time.sleep(0.1)
    
    def _should_stop(self):
        """Check if we should stop collecting."""
        # Check max items
        if self.max_items and len(self.data) >= self.max_items:
            return True
        
        # Check lifetime
        if self.lifetime:
            elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            if elapsed >= self.lifetime:
                return True
        
        return False
    
    def run(self):
        """Return next item from collected stream."""
        v = self.data[self.n] if self.n < len(self.data) else None
        self.n += 1
        return v


# ============================================================================
# TEST THIS TEMPLATE
# ============================================================================

if __name__ == "__main__":
    print("Testing Streaming Source")
    print("=" * 60)
    
    # Test 1: Stream with max items
    print("\nTest 1: Stream 5 items")
    source = MyStreamingSource(max_items=5)
    print(f"✓ Collected {len(source.data)} items")
    assert len(source.data) == 5
    
    # Test 2: Stream for time limit
    print("\nTest 2: Stream for 1 second")
    source = MyStreamingSource(lifetime=1)
    print(f"✓ Collected {len(source.data)} items in 1 second")
    assert len(source.data) > 0
    
    # Test 3: Yield items
    print("\nTest 3: Yield collected items")
    items = []
    while True:
        item = source.run()
        if item is None:
            break
        items.append(item)
    
    print(f"✓ Yielded {len(items)} items")
    
    print("\n" + "=" * 60)
    print("✓ Streaming Source template works!")


# ============================================================================
# REAL EXAMPLE
# ============================================================================

"""
See real implementation in:
    components/sources/bluesky_jetstream_source.py (BlueSkyJetstreamSource)
    
Common streaming sources:
    - WebSockets (websocket-client library)
    - Server-Sent Events (SSE)
    - Message queues (RabbitMQ, Kafka)
    - IoT sensors (MQTT)
"""
```

---

# Sink Templates

Sinks consume data. They implement `run(item)` for each item and `finalize()` at the end.

## Template 5: Simple Collector Sink

**Use when:** Collecting items into a list for processing

**Difficulty:** ⭐ Easiest

```python
# components/sinks/my_simple_sink.py


class MySimpleSink:
    """
    Template for a sink that collects items into a list.
    
    Perfect for: Testing, debugging, simple collection
    
    TODO: Customize what you do with collected items!
    """
    
    def __init__(self):
        """Initialize collector."""
        self.items = []
        print(f"[MySimpleSink] Ready to collect items")
    
    def run(self, item):
        """
        Process one item.
        
        Args:
            item: Data item to process
        """
        # TODO: Customize what you do with each item
        self.items.append(item)
        print(f"[MySimpleSink] Collected item {len(self.items)}: {item}")
    
    def finalize(self):
        """
        Called at the end of the stream.
        
        TODO: Customize final processing!
        """
        print(f"\n[MySimpleSink] Finalized: collected {len(self.items)} items")
        
        # TODO: Do something with collected items
        # Examples:
        # - Print summary statistics
        # - Save to file
        # - Send to API
        # - Generate report


# ============================================================================
# TEST THIS TEMPLATE
# ============================================================================

if __name__ == "__main__":
    print("Testing Simple Collector Sink")
    print("=" * 60)
    
    # Test 1: Create sink
    sink = MySimpleSink()
    print("✓ Sink created")
    
    # Test 2: Process items
    test_items = [
        {"id": 1, "value": "A"},
        {"id": 2, "value": "B"},
        {"id": 3, "value": "C"}
    ]
    
    for item in test_items:
        sink.run(item)
    
    print(f"\n✓ Processed {len(test_items)} items")
    
    # Test 3: Finalize
    sink.finalize()
    
    # Test 4: Verify collection
    assert len(sink.items) == 3
    assert sink.items[0]["value"] == "A"
    print("✓ Items collected correctly")
    
    print("\n" + "=" * 60)
    print("✓ Simple Collector Sink template works!")


# ============================================================================
# USE IN NETWORK
# ============================================================================

"""
Example usage in a network:

from dsl import network
from dsl.blocks import Source, Sink
from my_simple_sink import MySimpleSink

# Create source (simple list)
def yield_items():
    for i in range(5):
        yield {"id": i, "value": chr(65 + i)}
    return None

source_node = Source(fn=yield_items, name="generator")

# Create sink
sink = MySimpleSink()
sink_node = Sink(fn=sink.run, name="collector")

# Build and run network
g = network([(source_node, sink_node)])
g.run_network()

# Finalize
sink.finalize()

# Access collected items
print(f"Collected: {sink.items}")
"""

# ============================================================================
# REAL EXAMPLE
# ============================================================================

"""
See real implementation in:
    components/sinks/demo_file_writer.py (DemoFileWriter)
"""
```

---

## Template 6: File Writer Sink

**Use when:** Saving data to files (JSON, CSV, text)

**Difficulty:** ⭐⭐ Medium

```python
# components/sinks/my_file_writer_sink.py

import json
import csv
import os


class MyFileWriterSink:
    """
    Template for writing items to files.
    
    Perfect for: Data export, logging, backups
    
    TODO: Customize for your file format!
    """
    
    def __init__(self, filepath, format="json", mode="w"):
        """
        Initialize file writer.
        
        Args:
            filepath: Where to write file
            format: "json" | "jsonl" | "csv" | "txt"
            mode: "w" (overwrite) | "a" (append)
        """
        self.filepath = filepath
        self.format = format
        self.mode = mode
        self.items = []
        self.file_handle = None
        self.csv_writer = None
        
        # Create directory if needed
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        # Open file for streaming formats
        if format in ["jsonl", "txt"]:
            self.file_handle = open(filepath, mode, encoding="utf-8")
        elif format == "csv":
            self.file_handle = open(filepath, mode, newline='', encoding="utf-8")
        
        print(f"[MyFileWriterSink] Writing to: {filepath} ({format})")
    
    def run(self, item):
        """Write one item."""
        if self.format == "json":
            # Collect all, write in finalize
            self.items.append(item)
        
        elif self.format == "jsonl":
            # Write immediately (one JSON per line)
            self.file_handle.write(json.dumps(item, ensure_ascii=False) + "\n")
            self.items.append(item)  # Track count
        
        elif self.format == "csv":
            # First item: create CSV writer
            if self.csv_writer is None:
                if isinstance(item, dict):
                    fieldnames = list(item.keys())
                    self.csv_writer = csv.DictWriter(self.file_handle, fieldnames=fieldnames)
                    self.csv_writer.writeheader()
            
            # Write row
            self.csv_writer.writerow(item)
            self.items.append(item)  # Track count
        
        elif self.format == "txt":
            # Write as string
            self.file_handle.write(str(item) + "\n")
            self.items.append(item)  # Track count
    
    def finalize(self):
        """Flush and close file."""
        if self.format == "json":
            # Write all items as JSON array
            with open(self.filepath, self.mode, encoding="utf-8") as f:
                json.dump(self.items, f, indent=2, ensure_ascii=False)
        
        # Close file handle
        if self.file_handle:
            self.file_handle.close()
        
        # Report
        file_size = os.path.getsize(self.filepath)
        print(f"[MyFileWriterSink] Wrote {len(self.items)} items ({file_size} bytes)")


# ============================================================================
# TEST THIS TEMPLATE
# ============================================================================

if __name__ == "__main__":
    print("Testing File Writer Sink")
    print("=" * 60)
    
    # Test data
    test_items = [
        {"id": 1, "name": "Alice", "age": 28},
        {"id": 2, "name": "Bob", "age": 34},
        {"id": 3, "name": "Carol", "age": 45}
    ]
    
    # Test 1: JSON format
    print("\nTest 1: JSON format")
    sink = MyFileWriterSink("test_output.json", format="json")
    for item in test_items:
        sink.run(item)
    sink.finalize()
    
    # Verify
    with open("test_output.json") as f:
        data = json.load(f)
        assert len(data) == 3
        print(f"✓ JSON: Wrote {len(data)} items")
    
    # Test 2: JSONL format
    print("\nTest 2: JSONL format")
    sink = MyFileWriterSink("test_output.jsonl", format="jsonl")
    for item in test_items:
        sink.run(item)
    sink.finalize()
    
    # Verify
    with open("test_output.jsonl") as f:
        lines = f.readlines()
        assert len(lines) == 3
        print(f"✓ JSONL: Wrote {len(lines)} lines")
    
    # Test 3: CSV format
    print("\nTest 3: CSV format")
    sink = MyFileWriterSink("test_output.csv", format="csv")
    for item in test_items:
        sink.run(item)
    sink.finalize()
    
    # Verify
    with open("test_output.csv") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 3
        print(f"✓ CSV: Wrote {len(rows)} rows")
    
    # Cleanup
    os.remove("test_output.json")
    os.remove("test_output.jsonl")
    os.remove("test_output.csv")
    print("\n✓ Cleaned up test files")
    
    print("\n" + "=" * 60)
    print("✓ File Writer Sink template works!")


# ============================================================================
# REAL EXAMPLE
# ============================================================================

"""
See real implementation in:
    components/sinks/file_writer.py (FileWriter)
"""
```

---

## Template 7: API Poster Sink

**Use when:** Sending data to REST APIs

**Difficulty:** ⭐⭐⭐ Hard

```python
# components/sinks/my_api_poster_sink.py

import requests
import time


class MyAPIPosterSink:
    """
    Template for POSTing items to REST APIs.
    
    Perfect for: Webhooks, API integrations, data sync
    
    TODO: Customize for your API!
    """
    
    def __init__(self, api_url, headers=None, timeout=10, retry_count=3):
        """
        Initialize API poster.
        
        Args:
            api_url: API endpoint URL
            headers: Optional HTTP headers
            timeout: Request timeout in seconds
            retry_count: Number of retries on failure
        """
        self.api_url = api_url
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout
        self.retry_count = retry_count
        self.post_count = 0
        self.success_count = 0
        self.failure_count = 0
        
        print(f"[MyAPIPosterSink] Configured for: {api_url}")
    
    def run(self, item):
        """POST one item to API."""
        # Convert item to JSON if needed
        if not isinstance(item, dict):
            payload = {"data": str(item)}
        else:
            payload = item
        
        # Retry logic
        for attempt in range(self.retry_count):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=self.headers,
                    timeout=self.timeout
                )
                
                # Check success
                if response.status_code in [200, 201, 202, 204]:
                    self.post_count += 1
                    self.success_count += 1
                    print(f"[MyAPIPosterSink] POST #{self.post_count}: Success")
                    return  # Success!
                else:
                    print(f"[MyAPIPosterSink] POST failed: {response.status_code}")
            
            except requests.exceptions.Timeout:
                print(f"[MyAPIPosterSink] Timeout (attempt {attempt + 1}/{self.retry_count})")
            
            except requests.exceptions.RequestException as e:
                print(f"[MyAPIPosterSink] Error: {e}")
            
            # Retry with backoff
            if attempt < self.retry_count - 1:
                delay = (attempt + 1) * 1
                time.sleep(delay)
        
        # All retries failed
        self.failure_count += 1
        print(f"[MyAPIPosterSink] POST failed after {self.retry_count} attempts")
    
    def finalize(self):
        """Report summary."""
        print(f"\n[MyAPIPosterSink] Summary:")
        print(f"  Total POSTs: {self.post_count}")
        print(f"  Successful: {self.success_count}")
        print(f"  Failed: {self.failure_count}")


# ============================================================================
# TEST THIS TEMPLATE
# ============================================================================

if __name__ == "__main__":
    print("Testing API Poster Sink")
    print("=" * 60)
    
    # Test with JSONPlaceholder (fake REST API)
    api_url = "https://jsonplaceholder.typicode.com/posts"
    
    # Test 1: Create sink
    sink = MyAPIPosterSink(api_url=api_url)
    print("✓ Sink created")
    
    # Test 2: POST items
    test_items = [
        {"title": "Test Post 1", "body": "This is a test", "userId": 1},
        {"title": "Test Post 2", "body": "Another test", "userId": 1}
    ]
    
    print("\nPosting items:")
    for item in test_items:
        sink.run(item)
    
    # Test 3: Finalize
    sink.finalize()
    
    # Test 4: Verify
    assert sink.success_count > 0, "Should have successful POSTs"
    print("\n✓ POSTed successfully")
    
    print("\n" + "=" * 60)
    print("✓ API Poster Sink template works!")


# ============================================================================
# REAL EXAMPLE
# ============================================================================

"""
See real implementation in:
    components/sinks/webhook_sink.py (Webhook)
    
Common APIs to try:
    - JSONPlaceholder: https://jsonplaceholder.typicode.com/posts
    - Webhook.site: https://webhook.site/ (test webhooks)
    - RequestBin: https://requestbin.com/ (inspect requests)
"""
```

---

## Template 8: Batch Writer Sink

**Use when:** Buffering items before writing (efficiency)

**Difficulty:** ⭐⭐⭐ Hard

```python
# components/sinks/my_batch_writer_sink.py

import json


class MyBatchWriterSink:
    """
    Template for batch writing (buffer then flush).
    
    Perfect for: APIs with batch endpoints, efficient I/O
    
    TODO: Customize batch size and flush logic!
    """
    
    def __init__(self, batch_size=10, output_file="batches.json"):
        """
        Initialize batch writer.
        
        Args:
            batch_size: Number of items per batch
            output_file: Where to write batches
        """
        self.batch_size = batch_size
        self.output_file = output_file
        self.buffer = []
        self.batch_count = 0
        
        print(f"[MyBatchWriterSink] Batch size: {batch_size}")
    
    def run(self, item):
        """Add item to buffer, flush if full."""
        self.buffer.append(item)
        
        # Flush if buffer is full
        if len(self.buffer) >= self.batch_size:
            self._flush_batch()
    
    def _flush_batch(self):
        """Write batch to output."""
        if not self.buffer:
            return
        
        self.batch_count += 1
        
        # TODO: Customize what you do with the batch
        # Examples:
        # - Write to file
        # - POST to API
        # - Insert into database
        # - Process in parallel
        
        # Simple example: append to JSON file
        with open(self.output_file, 'a') as f:
            f.write(f"# Batch {self.batch_count}\n")
            json.dump(self.buffer, f, indent=2)
            f.write("\n\n")
        
        print(f"[MyBatchWriterSink] Flushed batch {self.batch_count} ({len(self.buffer)} items)")
        
        # Clear buffer
        self.buffer = []
    
    def finalize(self):
        """Flush remaining items."""
        if self.buffer:
            print(f"[MyBatchWriterSink] Flushing final batch ({len(self.buffer)} items)")
            self._flush_batch()
        
        print(f"[MyBatchWriterSink] Complete: {self.batch_count} batches")


# ============================================================================
# TEST THIS TEMPLATE
# ============================================================================

if __name__ == "__main__":
    import os
    
    print("Testing Batch Writer Sink")
    print("=" * 60)
    
    output_file = "test_batches.json"
    
    # Test 1: Create sink
    sink = MyBatchWriterSink(batch_size=3, output_file=output_file)
    print("✓ Sink created")
    
    # Test 2: Process items (more than one batch)
    print("\nProcessing 8 items (should create 3 batches):")
    for i in range(8):
        item = {"id": i + 1, "value": chr(65 + i)}
        sink.run(item)
    
    # Test 3: Finalize (flush remaining)
    sink.finalize()
    
    # Test 4: Verify batches
    with open(output_file) as f:
        content = f.read()
        batch_count = content.count("# Batch")
        print(f"\n✓ Created {batch_count} batches")
        assert batch_count == 3, "Should create 3 batches (3, 3, 2 items)"
    
    # Cleanup
    os.remove(output_file)
    print("✓ Cleaned up test file")
    
    print("\n" + "=" * 60)
    print("✓ Batch Writer Sink template works!")


# ============================================================================
# USE CASES
# ============================================================================

"""
Batch writing is useful for:

1. API Rate Limits:
   - Buffer items, send in batches
   - Avoid hitting rate limits

2. Database Efficiency:
   - Batch inserts are faster
   - Reduce transaction overhead

3. Network Efficiency:
   - Reduce number of requests
   - Better throughput

4. Processing Efficiency:
   - Process groups of items together
   - Parallelize batch processing
"""
```

---

# Common Patterns

These patterns can be added to any source or sink template.

## Pattern 1: Pagination

**Use when:** API returns data in pages

```python
def _fetch_with_pagination(self, base_url, max_items=100):
    """
    Fetch data from paginated API.
    
    Common pagination styles:
    - Offset/limit: ?offset=0&limit=10
    - Page number: ?page=1&per_page=10
    - Cursor: ?cursor=abc123
    """
    all_items = []
    page = 1
    per_page = 10
    
    while len(all_items) < max_items:
        # TODO: Adjust pagination params for your API
        params = {
            "page": page,
            "per_page": per_page
        }
        
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # TODO: Adjust data extraction for your API
        items = data.get("results", [])
        
        if not items:
            break  # No more pages
        
        all_items.extend(items)
        page += 1
        
        # Check if we've reached the end
        if len(items) < per_page:
            break
    
    return all_items[:max_items]


# Example usage:
"""
class MyPaginatedSource:
    def __init__(self, base_url, max_items=100):
        self.data = self._fetch_with_pagination(base_url, max_items)
        self.n = 0
    
    def run(self):
        v = self.data[self.n] if self.n < len(self.data) else None
        self.n += 1
        return v
"""
```

---

## Pattern 2: Rate Limiting

**Use when:** API has rate limits (e.g., 10 requests/second)

```python
import time
from datetime import datetime, timedelta


class RateLimiter:
    """
    Simple rate limiter.
    
    Usage:
        limiter = RateLimiter(max_calls=10, period=1.0)
        
        for item in items:
            limiter.wait_if_needed()
            make_api_call(item)
    """
    
    def __init__(self, max_calls, period=1.0):
        """
        Args:
            max_calls: Maximum calls per period
            period: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = []
    
    def wait_if_needed(self):
        """Wait if we've exceeded rate limit."""
        now = datetime.now()
        
        # Remove calls outside the current period
        cutoff = now - timedelta(seconds=self.period)
        self.calls = [t for t in self.calls if t > cutoff]
        
        # If at limit, wait
        if len(self.calls) >= self.max_calls:
            oldest_call = min(self.calls)
            wait_time = (oldest_call + timedelta(seconds=self.period) - now).total_seconds()
            
            if wait_time > 0:
                time.sleep(wait_time)
        
        # Record this call
        self.calls.append(datetime.now())


# Example usage:
"""
class MyRateLimitedSource:
    def __init__(self, api_url):
        self.api_url = api_url
        self.limiter = RateLimiter(max_calls=10, period=1.0)  # 10 calls/second
        self.data = []
        self._fetch_data()
    
    def _fetch_data(self):
        for page in range(10):
            self.limiter.wait_if_needed()  # Respect rate limit
            response = requests.get(f"{self.api_url}?page={page}")
            self.data.extend(response.json())
"""
```

---

## Pattern 3: Error Recovery

**Use when:** API calls might fail temporarily

```python
import time


def retry_with_backoff(func, max_retries=3, initial_delay=1, backoff_factor=2):
    """
    Retry function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        backoff_factor: Multiply delay by this each retry
    
    Returns:
        Function result if successful
        
    Raises:
        Last exception if all retries fail
    
    Example:
        response = retry_with_backoff(
            lambda: requests.get(url),
            max_retries=3
        )
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed: {e}")
                print(f"Retrying in {delay}s...")
                time.sleep(delay)
                delay *= backoff_factor
            else:
                print(f"All {max_retries} attempts failed")
    
    raise last_exception


# Example usage:
"""
class MyResilientSource:
    def _fetch_data(self):
        # This will retry up to 3 times with backoff
        response = retry_with_backoff(
            lambda: requests.get(self.api_url, timeout=10),
            max_retries=3,
            initial_delay=1,
            backoff_factor=2
        )
        return response.json()
"""
```

---

## Pattern 4: Authentication

**Use when:** API requires authentication

```python
import os
import requests


class APIAuthenticator:
    """
    Handle common authentication patterns.
    
    Supports:
    - API Key (header or query param)
    - Bearer Token
    - Basic Auth
    """
    
    @staticmethod
    def api_key_header(key=None, header_name="X-API-Key"):
        """
        API key in header.
        
        Example:
            headers = APIAuthenticator.api_key_header(
                key=os.environ.get("API_KEY"),
                header_name="X-API-Key"
            )
            response = requests.get(url, headers=headers)
        """
        key = key or os.environ.get("API_KEY")
        return {header_name: key}
    
    @staticmethod
    def api_key_param(key=None, param_name="api_key"):
        """
        API key in query parameter.
        
        Example:
            params = APIAuthenticator.api_key_param(
                key=os.environ.get("API_KEY")
            )
            response = requests.get(url, params=params)
        """
        key = key or os.environ.get("API_KEY")
        return {param_name: key}
    
    @staticmethod
    def bearer_token(token=None):
        """
        Bearer token authentication.
        
        Example:
            headers = APIAuthenticator.bearer_token(
                token=os.environ.get("BEARER_TOKEN")
            )
            response = requests.get(url, headers=headers)
        """
        token = token or os.environ.get("BEARER_TOKEN")
        return {"Authorization": f"Bearer {token}"}
    
    @staticmethod
    def basic_auth(username=None, password=None):
        """
        Basic authentication.
        
        Example:
            auth = APIAuthenticator.basic_auth(
                username=os.environ.get("API_USER"),
                password=os.environ.get("API_PASS")
            )
            response = requests.get(url, auth=auth)
        """
        username = username or os.environ.get("API_USER")
        password = password or os.environ.get("API_PASS")
        return (username, password)


# Example usage:
"""
class MyAuthenticatedSource:
    def __init__(self, api_url):
        self.api_url = api_url
        
        # Choose authentication method:
        
        # Option 1: API key in header
        self.headers = APIAuthenticator.api_key_header()
        
        # Option 2: Bearer token
        # self.headers = APIAuthenticator.bearer_token()
        
        # Option 3: Basic auth
        # self.auth = APIAuthenticator.basic_auth()
    
    def _fetch_data(self):
        response = requests.get(
            self.api_url,
            headers=self.headers  # or auth=self.auth
        )
        return response.json()
"""
```

---

# Quick Reference

## When to Use Each Template

**Sources:**
- **Simple List:** Static data, testing, small datasets
- **File Reader:** CSV, JSON, logs, exports
- **API Reader:** REST APIs, web services
- **Streaming:** Real-time data, WebSockets, events

**Sinks:**
- **Simple Collector:** Testing, debugging, temporary collection
- **File Writer:** Export, logging, backups
- **API Poster:** Webhooks, integrations, sync
- **Batch Writer:** Efficient I/O, rate limits, bulk operations

**Patterns:**
- **Pagination:** Multi-page API responses
- **Rate Limiting:** API call limits
- **Error Recovery:** Flaky networks, temporary failures
- **Authentication:** Secure APIs

---

# Testing Your Custom Connectors

## Testing Checklist

Before using your connector in production:

- [ ] **Syntax Check:**
  ```bash
  python3 -m py_compile my_connector.py
  ```

- [ ] **Unit Test:**
  ```bash
  python3 my_connector.py  # Run built-in tests
  ```

- [ ] **Integration Test:**
  ```python
  # Test in minimal network
  from dsl import network
  from dsl.blocks import Source, Sink
  
  source = MySource()
  sink = MySink()
  
  g = network([(Source(source.run), Sink(sink.run))])
  g.run_network()
  sink.finalize()
  ```

- [ ] **Edge Cases:**
  - Empty data
  - Network failures (for APIs)
  - Malformed data
  - Rate limits

- [ ] **Production Test:**
  - Start with small dataset
  - Monitor for errors
  - Verify output correctness

---

# Next Steps

## You've Learned:

✅ How to build custom sources
✅ How to build custom sinks
✅ Common patterns for robust connectors
✅ How to test your connectors

## Build Your Own!

Now create connectors for YOUR use case:
- Custom API your company uses?
- Specific file format?
- Database integration?
- IoT sensor data?
- Message queue?

## Get Inspired

Check out the real implementations:
- `components/sources/` - Real source examples
- `components/sinks/` - Real sink examples
- `examples/` - Complete working systems

## Need Help?

Review:
- Module 09 README - Overview of sources and sinks
- API_SETUP.md - Setting up external services
- Your working examples - Copy patterns that work

---

**Happy building! You have all the tools to create production-ready distributed systems!** 🚀
