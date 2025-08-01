"""
stream_recorders.py

Provides record(...) to create blocks that save or monitor stream messages.

Available modes:
- "memory" or "list": saves to internal list (default)
- str path: saves to file
- "file+stream": logs to file and forwards message
- "stdout": prints messages to console

Base class: StreamSaver

tags: record, memory, file, stdout, logging
"""

import os
from pathlib import Path
from dsl.core import SimpleAgent


class StreamSaver(SimpleAgent):
    """
    Base class for stream recording blocks.

    Receives messages on 'in' port and passes them to `_save_msg`.

    Subclasses must implement `_save_msg(self, agent, msg)`.
    """

    def __init__(self, name=None, description=None):
        super().__init__(
            name=name or "StreamSaver",
            description=description or "Records stream messages",
            inport="in",
            outports=[],
            handle_msg=self._save_msg
        )

    def _save_msg(self, agent, msg):
        raise NotImplementedError("Subclasses must implement _save_msg().")


def record(to="memory", name=None, filepath=None):
    """
    Returns a recorder block.

    Parameters:
    - to:
        - "memory" / "list": record to internal list
        - str path: write to file
        - "file+stream": write to file and forward message
        - "stdout": print messages
    - name: Optional block name
    - filepath: Required only for "file+stream"

    Returns:
    - A subclass of StreamSaver or a SimpleAgent

    Examples:
    >>> record()  # to memory
    >>> record(to="log.txt")  # to file
    >>> record(to="file+stream", filepath="log.txt")  # log and forward
    >>> record(to="stdout")
    """

    if to in ("memory", "list"):
        class StreamToList(StreamSaver):
            def __init__(self, name="RecordToList", description="Saves stream to list"):
                super().__init__(name=name, description=description)
                self.saved = []

            def _save_msg(self, agent, msg):
                if msg != "__STOP__":
                    self.saved.append(msg)

        return StreamToList(name=name or "RecordToList")

    if isinstance(to, Path):
        to = str(to)

    if isinstance(to, str) and os.path.isdir(to):
        raise ValueError(f"record(to=...) cannot be a directory: {to}")

    if isinstance(to, str) and to not in {"memory", "file+stream", "stdout"}:
        class StreamToFile(StreamSaver):
            def __init__(self, filename, name="RecordToFile", description="Saves stream to file"):
                super().__init__(name=name, description=description)
                self.filename = filename
                try:
                    self.file = open(filename, "w", buffering=1)
                except Exception as e:
                    raise IOError(f"Could not open file: {filename}\n{e}")

            def _save_msg(self, agent, msg):
                if msg == "__STOP__":
                    self.file.close()
                else:
                    self.file.write(str(msg) + "\n")
                    self.file.flush()

        return StreamToFile(filename=to, name=name or "RecordToFile")

    if to == "file+stream":
        if not filepath:
            raise ValueError("Missing 'filepath=' when using 'file+stream'")

        class StreamToFileCopy(SimpleAgent):
            def __init__(self, name=None, description=None, filepath="stream_log.txt"):
                self.filepath = filepath

                def handle_msg(agent, msg):
                    with open(agent.filepath, "a") as f:
                        f.write(str(msg) + "\n")
                    agent.send(msg, "out")

                    if msg == "__STOP__":
                        agent.send("__STOP__", "out")

                super().__init__(
                    name=name or "RecordCopyToFile",
                    description=description or f"Logs messages to {filepath}",
                    inport="in",
                    outports=["out"],
                    handle_msg=handle_msg
                )

        return StreamToFileCopy(filepath=filepath, name=name)

    if to == "stdout":
        class RecordToStdout(StreamSaver):
            def _save_msg(self, agent, msg):
                print(f"📤 {msg}")
                if msg == "__STOP__":
                    return

        return RecordToStdout(name=name or "StreamToStdout")

    raise ValueError(f"Invalid 'to' argument for record(): {to}")
