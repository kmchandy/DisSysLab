# dissyslab/components/sinks/sink_simple_file.py

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
        self.file = open(filename, 'w', encoding="utf-8")

    def run(self, msg):
        """
        Write message value to file as a line.

        Args:
            msg: Dict with 'value' key to write
        """
        self.file.write(f"{msg}\n")
        self.file.flush()

    def finalize(self):
        """Close the file. Safe to call more than once."""
        if self.file is not None and not self.file.closed:
            self.file.close()
            print(f"[FileLineWriter] Closed {self.filename}")

    def close(self):
        """Alias for finalize(), for callers that expect close()."""
        self.finalize()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.finalize()
        return False

    def __del__(self):
        # Last-resort close. An office that is killed mid-run -- exactly
        # what the checkpoint/resume tests do -- never reaches
        # finalize(), so without this the handle stays open until the
        # process exits. POSIX hides that (you may unlink an open file);
        # Windows does not, and a test that writes into a temp dir then
        # tries to remove it fails on the still-open handle.
        try:
            self.finalize()
        except Exception:  # noqa: BLE001 - never raise from __del__
            pass
