# components/sinks/sink_list_collector.py

"""Sink that collects messages into a list."""


class ListCollector:

    def __init__(self, values, print_values=False):
        """
        Args:
            value_key: Key to extract from messages (default: "result")
            name: Display name for printing (default: "collector")
            print_values: Whether to print collected values (default: True)
        """
        self.values = values
        self.print_values = print_values

    def run(self, msg):
        """
        Collect value from message.

        Args:
            msg: Dict containing value to collect
        """
        self.values.append(msg)

        if self.print_values:
            print(f"{msg} /n")

    def finalize(self):
        """Print summary of collected values."""
        # print(f"[{self.name}] Collected {len(self.collected)} values")
        pass
