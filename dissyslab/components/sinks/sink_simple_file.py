# components/sinks/sink_simple_file.py

"""Sink that writes each message as a line to a file."""


class FileLineWriter:
    """
    Writes message values to a file, one per line.

    Examples:
        >>> writer = FileLineWriter("output.txt")
        >>> writer.run(42)      # Writes "42\n"
        >>> writer.run("hello") # Writes "hello\n"
        >>> writer.finalize()   # Closes file
    """

    def __init__(self, filename):
        """
        Args:
            filename: Path to file to write to
        """
        self.filename = filename
        self.file = open(filename, 'w')

    def run(self, msg):
        """
        Write message value to file as a line.

        Args:
            msg: Dict with 'value' key to write
        """
        self.file.write(f"{msg}\n")
        self.file.flush()

    def finalize(self):
        """Close the file."""
        self.file.close()
        print(f"[FileLineWriter] Closed {self.filename}")
