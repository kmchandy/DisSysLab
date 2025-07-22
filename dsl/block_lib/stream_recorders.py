"""
This file contains blocks for recording and duplicating streams.
These include blocks to:
- Save stream output to memory or disk
- Monitor or duplicate streams non-destructively

The base class is StreamSaver, with subclasses for different destinations.
"""

from dsl.core import SimpleAgent
from typing import Optional, Union
import os

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

    tags: recorder, base, save, stream
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
#                StreamToList                     |
# =================================================

class StreamToList(StreamSaver):
    """
    Name: StreamToList

    Summary:
    A block that saves all incoming stream messages to a Python list.

    Parameters:
    - name: Optional name.
    - description: Optional description.

    Behavior:
    - Appends each non-"__STOP__" message to self.saved.
    - Discards "__STOP__" signal.

    Use Cases:
    - For testing or storing intermediate results.
    - Easily inspect output in memory after network runs.

    tags: recorder, memory, list, debug, test
    """

    def __init__(self, name="to_list", description="Save stream to list"):
        super().__init__(name=name, description=description)
        self.saved = []

    def _save_msg(self, agent, msg):
        if msg != "__STOP__":
            self.saved.append(msg)


# =================================================
#                StreamToFile                     |
# =================================================

class StreamToFile(StreamSaver):
    """
    Name: StreamToFile

    Summary:
    A block that writes each stream message to a file, one per line.

    Parameters:
    - filename: Path to the file where messages will be written.
    - name: Optional name.
    - description: Optional description.

    Behavior:
    - Writes each non-"__STOP__" message to the file.
    - Closes the file on "__STOP__".

    Use Cases:
    - Archive stream data
    - Write logs or audit trails

    tags: recorder, file, write, output, stream log
    """

    def __init__(self, filename, name="to_file", description="Save stream to file"):
        super().__init__(name=name, description=description)
        self.filename = filename
        self.file = open(filename, "w")

    def _save_msg(self, agent, msg):
        if msg == "__STOP__":
            self.file.close()
        else:
            self.file.write(str(msg) + "\n")


# =================================================
#                StreamCopy                       |
# =================================================

class StreamCopy(SimpleAgent):
    """
    Name: StreamCopy

    Summary:
    A block that duplicates each input message to two output ports: "main" and "watch".

    Parameters:
    - name: Optional name.
    - description: Optional description.

    Behavior:
    - On receiving a message:
      - Sends the message to "main" and "watch".
    - Sends "__STOP__" to both outputs when stream ends.

    Use Cases:
    - Debugging a stream while allowing normal processing
    - Sending data to a logger and a downstream agent

    tags: stream, copy, duplicate, monitor, debug
    """

    def __init__(self, name: str = None, description: str = None):
        def handle_msg(agent, msg):
            if msg == "__STOP__":
                agent.send("__STOP__", "main")
                agent.send("__STOP__", "watch")
            else:
                agent.send(msg, "main")
                agent.send(msg, "watch")

        super().__init__(
            name=name or "StreamCopy",
            description=description or "Duplicates stream to main and watch",
            inport="in",
            outports=["main", "watch"],
            init_fn=None,
            handle_msg=handle_msg
        )


# =================================================
#              StreamToFileCopy                   |
# =================================================

class StreamToFileCopy(SimpleAgent):
    """
    Name: StreamToFileCopy

    Summary:
    A block that forwards each message and writes a copy to a file.

    Parameters:
    - name: Optional name.
    - description: Optional description.
    - filepath: File path to write messages (one per line).

    Behavior:
    - Appends each message to the specified file.
    - Forwards the message unchanged to the "out" port.

    Use Cases:
    - Tap into a live stream for monitoring
    - Preserve raw stream while allowing further processing

    tags: monitor, log, stream, file, copy, duplicate
    """

    def __init__(
        self,
        name: str = None,
        description: str = None,
        filepath: str = "stream_log.txt",
    ):
        self.filepath = filepath

        def handle_msg(agent, msg):
            with open(agent.filepath, "a") as f:
                f.write(repr(msg) + "\n")
            agent.send(msg, "out")

        super().__init__(
            name=name or "StreamToFileCopy",
            description=description or f"Stream monitor that logs to {filepath}",
            inport="in",
            outports=["out"],
            init_fn=None,
            handle_msg=handle_msg,
        )
