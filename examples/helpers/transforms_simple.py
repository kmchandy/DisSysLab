# dsl/connectors/transforms_simple.py

"""
Example transform classes for teaching purposes.

All transforms follow the class-based pattern:
- __init__ for parameters and state
- A method that takes (msg) and returns transformed msg or None
"""

import re


# ============================================================================
# Numeric Transforms
# ============================================================================

class Doubler:
    """Double a numeric value in messages."""

    def transform(self, msg):
        """Double the 'value' field."""
        return {"value": msg["value"] * 2}


class Scaler:
    """
    Scale a numeric value by a factor.

    Example:
        >>> scaler = Scaler(factor=10)
        >>> transform = Transform(fn=scaler.scale)
    """

    def __init__(self, factor):
        self.factor = factor

    def scale(self, msg):
        """Scale the 'value' field by factor."""
        return {"value": msg["value"] * self.factor}


class Adder:
    """
    Add a constant to a numeric value.

    Example:
        >>> adder = Adder(amount=100)
        >>> transform = Transform(fn=adder.add)
    """

    def __init__(self, amount):
        self.amount = amount

    def add(self, msg):
        """Add amount to the 'value' field."""
        return {"value": msg["value"] + self.amount}


class RangeMapper:
    """
    Map a value from one range to another.

    Example:
        >>> # Map 0-100 to 0-1
        >>> mapper = RangeMapper(in_min=0, in_max=100, out_min=0, out_max=1)
        >>> transform = Transform(fn=mapper.map)
    """

    def __init__(self, in_min, in_max, out_min, out_max):
        self.in_min = in_min
        self.in_max = in_max
        self.out_min = out_min
        self.out_max = out_max

    def map(self, msg):
        """Map value from input range to output range."""
        value = msg["value"]
        # Normalize to 0-1
        normalized = (value - self.in_min) / (self.in_max - self.in_min)
        # Scale to output range
        mapped = self.out_min + normalized * (self.out_max - self.out_min)
        return {"value": mapped}


# ============================================================================
# Stateful Transforms (Counters, Indexers)
# ============================================================================

class Counter:
    """
    Add an index/count to each message.

    Example:
        >>> counter = Counter()
        >>> transform = Transform(fn=counter.add_index)
    """

    def __init__(self, start=0):
        self.count = start

    def add_index(self, msg):
        """Add 'index' field with current count."""
        self.count += 1
        return {**msg, "index": self.count}


class Batcher:
    """
    Batch messages into groups.

    Example:
        >>> batcher = Batcher(batch_size=10)
        >>> transform = Transform(fn=batcher.batch)
    """

    def __init__(self, batch_size):
        self.batch_size = batch_size
        self.batch = []

    def batch(self, msg):
        """Collect messages into batches."""
        self.batch.append(msg)

        if len(self.batch) >= self.batch_size:
            # Return the full batch
            result = {"batch": self.batch.copy()}
            self.batch.clear()
            return result

        # Not ready yet, filter this message
        return None


class MovingAverage:
    """
    Compute moving average over a window.

    Example:
        >>> avg = MovingAverage(window_size=5)
        >>> transform = Transform(fn=avg.average)
    """

    def __init__(self, window_size):
        self.window_size = window_size
        self.values = []

    def average(self, msg):
        """Add value and return moving average."""
        self.values.append(msg["value"])

        # Keep only last window_size values
        if len(self.values) > self.window_size:
            self.values.pop(0)

        avg = sum(self.values) / len(self.values)
        return {**msg, "moving_avg": avg}


# ============================================================================
# Text Transforms
# ============================================================================

class TextCleaner:
    """
    Clean text by removing emojis and extra whitespace.

    Example:
        >>> cleaner = TextCleaner()
        >>> transform = Transform(fn=cleaner.clean)
    """

    def clean(self, msg):
        """Remove emojis and normalize whitespace."""
        text = msg["text"]
        # Remove emojis and special characters
        cleaned = re.sub(r'[^\w\s.,!?-]', '', text)
        # Normalize whitespace
        cleaned = ' '.join(cleaned.split())
        return {**msg, "clean_text": cleaned}


class LowerCaser:
    """Convert text to lowercase."""

    def lowercase(self, msg):
        """Convert 'text' field to lowercase."""
        return {**msg, "text": msg["text"].lower()}


class WordCounter:
    """
    Count words in text.

    Example:
        >>> counter = WordCounter()
        >>> transform = Transform(fn=counter.count)
    """

    def count(self, msg):
        """Add 'word_count' field."""
        text = msg.get("text", "")
        word_count = len(text.split())
        return {**msg, "word_count": word_count}


class SentimentAnalyzer:
    """
    Simple keyword-based sentiment analysis.

    Example:
        >>> analyzer = SentimentAnalyzer()
        >>> transform = Transform(fn=analyzer.analyze)
    """

    def __init__(self):
        self.positive_words = [
            'amazing', 'best', 'excited', 'great', 'promoted',
            'love', 'good', 'excellent', 'wonderful', 'fantastic'
        ]
        self.negative_words = [
            'terrible', 'lost', 'stuck', 'worst', 'hate', 'bad',
            'awful', 'frustrated', 'disappointed', 'waste'
        ]

    def analyze(self, msg):
        """Analyze sentiment of text."""
        text = msg.get("text", "").lower()

        pos_count = sum(1 for word in self.positive_words if word in text)
        neg_count = sum(1 for word in self.negative_words if word in text)

        if pos_count > neg_count:
            sentiment = "POSITIVE"
        elif neg_count > pos_count:
            sentiment = "NEGATIVE"
        else:
            sentiment = "NEUTRAL"

        score = pos_count - neg_count

        return {**msg, "sentiment": sentiment, "score": score}


# ============================================================================
# Filter Transforms (return None to drop messages)
# ============================================================================

class ThresholdFilter:
    """
    Filter messages based on a threshold.

    Example:
        >>> # Only pass messages with value > 10
        >>> filter_obj = ThresholdFilter(threshold=10, keep="above")
        >>> transform = Transform(fn=filter_obj.filter)
    """

    def __init__(self, threshold, keep="above"):
        self.threshold = threshold
        self.keep = keep

    def filter(self, msg):
        """Filter based on threshold."""
        value = msg["value"]

        if self.keep == "above":
            return msg if value > self.threshold else None
        elif self.keep == "below":
            return msg if value < self.threshold else None
        elif self.keep == "equal":
            return msg if value == self.threshold else None
        else:
            return msg


class RangeFilter:
    """
    Keep only messages within a range.

    Example:
        >>> filter_obj = RangeFilter(min_val=0, max_val=100)
        >>> transform = Transform(fn=filter_obj.filter)
    """

    def __init__(self, min_val, max_val):
        self.min_val = min_val
        self.max_val = max_val

    def filter(self, msg):
        """Keep messages in range."""
        value = msg["value"]
        if self.min_val <= value <= self.max_val:
            return msg
        return None


class DuplicateFilter:
    """
    Filter out duplicate messages.

    Example:
        >>> filter_obj = DuplicateFilter(key="id")
        >>> transform = Transform(fn=filter_obj.filter)
    """

    def __init__(self, key="value"):
        self.key = key
        self.seen = set()

    def filter(self, msg):
        """Filter out duplicates based on key."""
        value = msg.get(self.key)

        if value in self.seen:
            return None  # Duplicate, filter it out

        self.seen.add(value)
        return msg


# ============================================================================
# Field Transforms (add, remove, rename fields)
# ============================================================================

class FieldAdder:
    """
    Add a new field to messages.

    Example:
        >>> adder = FieldAdder(field="timestamp", value=12345)
        >>> transform = Transform(fn=adder.add)
    """

    def __init__(self, field, value):
        self.field = field
        self.value = value

    def add(self, msg):
        """Add field to message."""
        return {**msg, self.field: self.value}


class FieldRemover:
    """
    Remove fields from messages.

    Example:
        >>> remover = FieldRemover(fields=["temp", "debug"])
        >>> transform = Transform(fn=remover.remove)
    """

    def __init__(self, fields):
        self.fields = fields if isinstance(fields, list) else [fields]

    def remove(self, msg):
        """Remove specified fields."""
        return {k: v for k, v in msg.items() if k not in self.fields}


class FieldRenamer:
    """
    Rename fields in messages.

    Example:
        >>> renamer = FieldRenamer(mapping={"old_name": "new_name"})
        >>> transform = Transform(fn=renamer.rename)
    """

    def __init__(self, mapping):
        self.mapping = mapping

    def rename(self, msg):
        """Rename fields according to mapping."""
        result = {}
        for key, value in msg.items():
            new_key = self.mapping.get(key, key)
            result[new_key] = value
        return result


__all__ = [
    # Numeric
    "Doubler", "Scaler", "Adder", "RangeMapper",
    # Stateful
    "Counter", "Batcher", "MovingAverage",
    # Text
    "TextCleaner", "LowerCaser", "WordCounter", "SentimentAnalyzer",
    # Filters
    "ThresholdFilter", "RangeFilter", "DuplicateFilter",
    # Field operations
    "FieldAdder", "FieldRemover", "FieldRenamer"
]
