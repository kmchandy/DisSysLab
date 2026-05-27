# dissyslab/components/sources/console_input_source.py
"""Interactive stdin line source (pair of ``console_printer`` for sinks)."""

from __future__ import annotations

import os
import sys
from typing import Optional


class ConsoleInputSource:
    """Yield one user line per ``run()`` call when stdin is a TTY.

    When stdin is not interactive (for example the custom app runs
    ``dsl run`` with ``stdin=DEVNULL``), the first ``run()`` returns
    ``default_message`` if given, else ``OFFICE_CONSOLE_INPUT`` from
    the environment, then subsequent calls return ``None``.
    """

    def __init__(
        self,
        prompt: str = "",
        default_message: Optional[str] = None,
    ) -> None:
        self.prompt = prompt or ""
        self.default_message = default_message
        self._finished = False

    def run(self):
        if self._finished:
            return None

        if sys.stdin.isatty():
            try:
                return input(self.prompt)
            except EOFError:
                self._finished = True
                return None

        msg = self.default_message
        if msg is None:
            msg = os.environ.get("OFFICE_CONSOLE_INPUT")
        self._finished = True
        return msg
