# components/sinks/console_sink.py

"""
ConsoleSink: Simple sink that prints messages to console.

This is a reusable sink component that can be imported and used
in any network for testing and debugging.
"""


class ConsoleSink:
    """
    Simple sink that prints messages to the console.

    This is designed to work with the DSL's sink_map decorator
    and provides formatted output for debugging and testing.

    Example:
        >>> from components.sinks.console_sink import ConsoleSink
        >>> console = ConsoleSink()
        >>> console.run({"text": "Hello world"})

        ========================================
        Message #1
        ========================================
        text: Hello world
        ========================================
    """

    def __init__(self, verbose: bool = True):
        """
        Initialize the console sink.

        Args:
            verbose: If True, print full message details.
                    If False, print compact one-line format.
        """
        self.count = 0
        self.verbose = verbose

    def run(self, msg):
        """
        Print a message to the console.

        Args:
            msg: Dictionary containing message data
        """
        self.count += 1

        if self.verbose:
            self._print_verbose(msg)
        else:
            self._print_compact(msg)

    def _print_verbose(self, msg):
        """Print message with full formatting."""
        print()
        print("=" * 70)
        print(f"Message #{self.count}")
        print("=" * 70)

        for key, value in msg.items():
            print(f"{key}: {value}")

        print("=" * 70)

    def _print_compact(self, msg):
        """Print message in compact one-line format."""
        print(f"[{self.count}] {msg}")

    def finalize(self):
        """Cleanup - prints summary."""
        print()
        print(f"ConsoleSink: Printed {self.count} messages")
        print()
