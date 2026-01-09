# dsl/sinks/example_sinks.py

"""
Example sink functions and classes for teaching purposes.

These demonstrate common patterns for terminal nodes in pipelines.
"""


# ============================================================================
# Simple Function Sinks
# ============================================================================

def print_sink(msg):
    """Print each message to console."""
    print(msg)


def print_pretty(msg):
    """Print messages in a formatted way."""
    if isinstance(msg, dict):
        print("Message:")
        for key, value in msg.items():
            print(f"  {key}: {value}")
    else:
        print(f"Message: {msg}")
    print()


# ============================================================================
# Collector Sinks (Stateful)
# ============================================================================

class ListCollector:
    """
    Collect all messages in a list.

    Example:
        >>> collector = ListCollector()
        >>> sink = Sink(fn=collector.collect)
        >>> # After pipeline runs:
        >>> print(collector.results)
    """

    def __init__(self):
        self.results = []

    def collect(self, msg):
        """Append message to results list."""
        self.results.append(msg)

    def __len__(self):
        return len(self.results)

    def clear(self):
        """Clear collected results."""
        self.results.clear()


class CountingSink:
    """
    Count messages and print periodic updates.

    Example:
        >>> counter = CountingSink(report_every=100)
        >>> sink = Sink(fn=counter.count)
    """

    def __init__(self, report_every=10):
        self.count = 0
        self.report_every = report_every

    def count(self, msg):
        """Count each message."""
        self.count += 1
        if self.count % self.report_every == 0:
            print(f"Processed {self.count} messages")


# ============================================================================
# File Writer Sinks
# ============================================================================

class FileWriter:
    """
    Write messages to a file.

    Example:
        >>> writer = FileWriter("output.txt")
        >>> sink = Sink(fn=writer.write)
        >>> # Later:
        >>> writer.close()
    """

    def __init__(self, filename, mode="w"):
        self.filename = filename
        self.mode = mode
        self.file = None
        self.opened = False

    def write(self, msg):
        """Write message to file."""
        if not self.opened:
            self.file = open(self.filename, self.mode)
            self.opened = True

        self.file.write(str(msg) + "\n")
        self.file.flush()

    def close(self):
        """Close the file."""
        if self.file:
            self.file.close()
            self.opened = False


class JSONLWriter:
    """
    Write messages as JSON Lines (one JSON object per line).

    Example:
        >>> writer = JSONLWriter("output.jsonl")
        >>> sink = Sink(fn=writer.write)
    """

    def __init__(self, filename, mode="w"):
        import json
        self.filename = filename
        self.mode = mode
        self.file = None
        self.opened = False
        self.json = json

    def write(self, msg):
        """Write message as JSON line."""
        if not self.opened:
            self.file = open(self.filename, self.mode)
            self.opened = True

        self.file.write(self.json.dumps(msg) + "\n")
        self.file.flush()

    def close(self):
        """Close the file."""
        if self.file:
            self.file.close()
            self.opened = False


# ============================================================================
# Validation/Filter Sinks
# ============================================================================

class ValidationSink:
    """
    Validate messages and collect errors.

    Example:
        >>> def is_valid(msg):
        ...     return "value" in msg and msg["value"] > 0
        >>> 
        >>> validator = ValidationSink(is_valid)
        >>> sink = Sink(fn=validator.validate)
        >>> print(f"Valid: {validator.valid_count}, Invalid: {validator.invalid_count}")
    """

    def __init__(self, validation_fn):
        self.validation_fn = validation_fn
        self.valid_count = 0
        self.invalid_count = 0
        self.errors = []

    def validate(self, msg):
        """Validate and count messages."""
        try:
            if self.validation_fn(msg):
                self.valid_count += 1
            else:
                self.invalid_count += 1
                self.errors.append(msg)
        except Exception as e:
            self.invalid_count += 1
            self.errors.append((msg, str(e)))


# ============================================================================
# Statistics Sinks
# ============================================================================

class StatsSink:
    """
    Collect statistics about numeric messages.

    Example:
        >>> stats = StatsSink(key="value")
        >>> sink = Sink(fn=stats.process)
        >>> print(f"Mean: {stats.mean()}, Max: {stats.max_val}")
    """

    def __init__(self, key="value"):
        self.key = key
        self.values = []
        self.count = 0
        self.sum_val = 0
        self.min_val = None
        self.max_val = None

    def process(self, msg):
        """Process numeric message."""
        if isinstance(msg, dict):
            value = msg.get(self.key)
        else:
            value = msg

        if value is not None:
            self.values.append(value)
            self.count += 1
            self.sum_val += value

            if self.min_val is None or value < self.min_val:
                self.min_val = value
            if self.max_val is None or value > self.max_val:
                self.max_val = value

    def mean(self):
        """Calculate mean of collected values."""
        return self.sum_val / self.count if self.count > 0 else 0

    def summary(self):
        """Get summary statistics."""
        return {
            "count": self.count,
            "sum": self.sum_val,
            "mean": self.mean(),
            "min": self.min_val,
            "max": self.max_val
        }


__all__ = [
    "print_sink",
    "print_pretty",
    "ListCollector",
    "CountingSink",
    "FileWriter",
    "JSONLWriter",
    "ValidationSink",
    "StatsSink"
]
