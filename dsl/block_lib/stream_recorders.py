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

from datetime import datetime
from pathlib import Path
import json
from typing import Optional, Literal, Union
from rich import print as rprint

from dsl.core import SimpleAgent

# =================================================
#              Record(SimpleAgent)                 |
# =================================================


class Record(SimpleAgent):
    """
    A flexible recorder block that records messages to a file or list.

    Parameters:
    - mode: "file" or "list"
    - target: filename (str) if mode == "file", or list instance if mode == "list"
    - key: optional key to extract from dict messages
    - name: optional block name

    Behavior:
    - Writes one record per message (in JSON format)
    - If key is provided and message is a dict, records only msg[key]
    - Handles '__STOP__' by forwarding it downstream
    """

    def __init__(
        self,
        mode: Literal["file", "list"],
        target: Union[str, list],
        key: Optional[str] = None,
        name: str = "Record",
    ):
        self.mode = mode
        self.target = target
        self.key = key

        if mode == "file":
            with open(self.target, "w") as f:
                f.write("")
        elif mode == "list":
            if not isinstance(target, list):
                raise ValueError("For mode='list', target must be a list")
        else:
            raise ValueError("mode must be 'file' or 'list'")

        # Define message handler
        def handle_msg(agent, msg):
            if msg == "__STOP__":
                agent.send("__STOP__")
                return

            if self.key and isinstance(msg, dict):
                value = msg.get(self.key)
            else:
                value = msg

            if self.mode == "file":
                with open(self.target, "a") as f:
                    json.dump(value, f)
                    f.write("\n")
            else:
                self.target.append(value)

        # Now call SimpleAgent.__init__
        super().__init__(
            name=name,
            inport="in",
            handle_msg=handle_msg
        )


# =================================================
#                   RecordToFile                  |
# =================================================
class RecordToFile(Record):
    """
    RecordToFile

    A simplified version of the Record block that writes messages to a file.

    Parameters:
    - filename (str): Path to the output file.
    - key (str, optional): If provided, records only msg[key] for dict messages.
    - name (str): Optional block name.

    Behavior:
    - Saves each message as a JSON line in the given file.
    - For dicts, you can specify which field to record.
    - Sends '__STOP__' when recording is complete.

    Example:
    >>> block = RecordToFile("tweets.jsonl", key="data")
    """

    def __init__(self, filename: str, key: Optional[str] = None, name: str = "RecordToFile"):
        super().__init__(mode="file", target=filename, key=key, name=name)


# =================================================
#                   RecordToList                  |
# =================================================
class RecordToList(Record):

    """
    RecordToList

    A simplified version of the Record block that stores messages in a Python list.

    Parameters:
    - target_list (list): The list to store messages in.
    - key (str, optional): If provided, records only msg[key] for dict messages.
    - name (str): Optional block name.

    Behavior:
    - Appends one item per message to the list.
    - For dicts, you can specify which field to record.
    - Sends '__STOP__' when recording is complete.

    Example:
    >>> results = []
    >>> block = RecordToList(results, key="sentiment")
    """

    def __init__(self, target_list: list, key: Optional[str] = None, name: str = "RecordToList"):
        super().__init__(mode="list", target=target_list, key=key, name=name)


# =================================================
#                RecordToConsole                  |
# =================================================
class RecordToConsole(Record):
    """
    RecordToConsole

    A recorder that prints incoming messages or a selected field to the console.

    Parameters:
    - key (str, optional): If provided, prints only msg[key] for dict messages.
    - name (str): Optional block name.

    Behavior:
    - Pretty-prints one message per line using rich.
    - Does not store or write messages.
    - Passes through '__STOP__'.

    Example:
    >>> block = RecordToConsole(key="sentiment")
    """

    def __init__(self, key: Optional[str] = None, name: str = "RecordToConsole"):
        def print_msg(agent, msg):
            if msg == "__STOP__":
                agent.send("__STOP__")
                return

            value = msg.get(key) if key and isinstance(msg, dict) else msg
            rprint(f"[bold green]📤 {value}[/bold green]")

        super().__init__(
            mode="list",  # dummy mode, unused
            target=[],
            key=key,
            name=name
        )
        self.process = print_msg


# =================================================
#                RecordToLogFile                  |
# =================================================
class RecordToLogFile(Record):
    """
    RecordToLogFile

    A recorder that writes messages to a timestamped log file (JSON lines).

    Parameters:
    - base_filename (str): Log file name prefix (e.g., "run").
    - key (str, optional): If provided, records only msg[key].
    - name (str): Optional block name.

    Behavior:
    - Creates 'base_filename_YYYYMMDD_HHMMSS.log'
    - Appends one JSON-formatted message per line.
    - Passes through '__STOP__'.

    Example:
    >>> block = RecordToLogFile("stream", key="data")
    """

    def __init__(self, base_filename: str = "record", key: Optional[str] = None, name: str = "RecordToLogFile"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = f"{base_filename}_{timestamp}.log"
        super().__init__(mode="file", target=log_path, key=key, name=name)
        self.log_path = log_path


def record(
    to: Literal["list", "file", "console", "logfile"] = "list",
    key: Optional[str] = None,
    filename: Optional[str] = None,
    target: Optional[list] = None,
    name: Optional[str] = None,
):
    """
    Create a recorder block for saving or inspecting stream messages.

    Parameters:
    - to: One of "list", "file", "console", "logfile"
    - key: Optional dict key to extract (e.g., key="data")
    - filename: Required for "file" and "logfile"
    - target: Required list for "list" mode, or auto-created if None
    - name: Optional block name

    Returns:
    - A subclass of Record

    Examples:
    >>> rec = record(to="list", target=my_list)
    >>> rec = record(to="file", filename="out.jsonl", key="text")
    >>> rec = record(to="console")
    >>> rec = record(to="logfile", filename="run")
    """
    if to == "list":
        if target is None:
            target = []
        return RecordToList(target_list=target, key=key, name=name or "RecordToList")

    elif to == "file":
        if not filename:
            raise ValueError("filename is required for to='file'")
        return RecordToFile(filename=filename, key=key, name=name or "RecordToFile")

    elif to == "console":
        return RecordToConsole(key=key, name=name or "RecordToConsole")

    elif to == "logfile":
        if not filename:
            filename = "record"
        return RecordToLogFile(base_filename=filename, key=key, name=name or "RecordToLogFile")

    else:
        raise ValueError(f"Unsupported 'to' argument: {to}")
