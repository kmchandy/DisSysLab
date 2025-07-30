from dsl.core import SimpleAgent
import os
from pathlib import Path


# =================================================
#                StreamSaver                      |
# =================================================


class StreamSaver(SimpleAgent):
    """
    Name: StreamSaver

    Summary:
    Base class for blocks that record stream messages. Subclasses define how to save each message.

    Parameters:
    - name: Optional name for the block.
    - description: Optional description.

    Behavior:
    - Receives messages on the "in" port.
    - Calls the _save_msg method for each incoming message.
    - Subclasses must implement _save_msg to define saving behavior.

    Use Cases:
    - Base class for logging, file writing, memory recording.

    tags: ["record", "memory", "file", "logging", "save"]
    """

    def __init__(
        self,
        name: str = None,
        description: str = None,
    ):
        super().__init__(
            name=name or "StreamSaver",
            description=description or "Records stream messages",
            inport="in",
            outports=[],
            init_fn=None,
            handle_msg=self._save_msg
        )

    def _save_msg(self, agent, msg):
        raise NotImplementedError("Subclasses must implement _save_msg()")


# =================================================
#                  record()                        |
# =================================================


def record(to="memory", name=None, filepath=None):
    """
    Create a recorder block to save or monitor messages.

    Parameters:
    - to:
        - "memory" or "list" → save messages in a list (default)
        - <filepath:str> → save messages to a file
        -    Note:  filepath: Required only if to="file+stream"
        - "file+stream" → save to file and forward downstream
    - name: Optional block name


    Returns:
    - A recorder block

    Examples:
    >>> record()  # Saves to memory
    >>> record(to="results.txt")  # Saves to file
    >>> record(to="file+stream", filepath="log.txt")  # Logs and forwards

    tags: record, memory, file, logging, save
    """

    if to in ("memory", "list"):
        class StreamToList(StreamSaver):
            def __init__(self, name="to_list", description="Save stream to list"):
                super().__init__(name=name or "RecordToList", description=description)
                self.saved = []

            def _save_msg(self, agent, msg):
                if msg != "__STOP__":
                    self.saved.append(msg)

        return StreamToList(name=name)

    # Accept pathlib.Path
    if isinstance(to, Path):
        to = str(to)

    # Detect accidental directory
    if isinstance(to, str) and os.path.isdir(to):
        raise ValueError(f"record(to=...) cannot be a directory: {to}")

    # Write to file only
    if isinstance(to, str) and to not in {"memory", "file+stream"}:
        class StreamToFile(StreamSaver):
            def __init__(self, filename, name="to_file", description="Save stream to file"):
                super().__init__(name=name or "RecordToFile", description=description)
                self.filename = filename
                try:
                    self.file = open(filename, "w", buffering=1)
                except Exception as e:
                    raise IOError(
                        f"Could not open file for writing: {filename}\nError: {e}")

            def _save_msg(self, agent, msg):
                if msg == "__STOP__":
                    self.file.close()
                else:
                    self.file.write(str(msg) + "\n")
                    self.file.flush()

        return StreamToFile(filename=to, name=name)

    if to == "file+stream":
        if not filepath:
            raise ValueError("Missing 'filepath=' when using 'to=file+stream'")

        class StreamToFileCopy(SimpleAgent):
            def __init__(self, name=None, description=None, filepath="stream_log.txt"):
                self.filepath = filepath

                def handle_msg(agent, msg):
                    with open(agent.filepath, "a") as f:
                        f.write(str(msg) + "\n")
                    agent.send(msg, "out")

                super().__init__(
                    name=name or "RecordCopyToFile",
                    description=description or f"Stream monitor that logs to {filepath}",
                    inport="in",
                    outports=["out"],
                    init_fn=None,
                    handle_msg=handle_msg,
                )

        return StreamToFileCopy(filepath=filepath, name=name)

    if to == "stdout":
        class RecordToStdout(StreamSaver):
            def _save_msg(self, agent, msg):
                print(f"📤 {msg}")
        return RecordToStdout(name=name or "StreamToStdout")

    raise ValueError(f"Invalid 'to' argument for record(): {to}")
