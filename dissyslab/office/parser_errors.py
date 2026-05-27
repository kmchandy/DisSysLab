"""
ParseError — a parser exception with a line-numbered context.

Hand-written parsers earn their keep (over LLM-driven parsers) by giving
the user actionable error messages. ``ParseError`` carries:

* a one-line summary of what went wrong,
* the path to the file that was being read (if any),
* the line number where the error was detected,
* and a snippet of the offending line, with a caret pointing at it.

The string form is suitable for printing directly to a terminal.

Design choices
==============

* Subclasses ``ValueError`` so the existing ``dsl run`` exception
  handler treats it as a user-input error, not an internal failure.

* ``__str__`` prints a multi-line message. Callers that want a
  single-line summary can use ``ParseError.short`` or read the
  ``message`` attribute directly.

* The ``snippet`` and ``column`` arguments are optional. When
  omitted, the formatted message simply quotes the offending line.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union


class ParseError(ValueError):
    """A parse failure with location context.

    Parameters
    ----------
    message
        One-line summary of what went wrong (no leading capital
        required; included verbatim in the formatted output).
    path
        File the parser was reading. ``None`` means "no file
        context" (e.g., the parser was given a string).
    line_no
        1-based line number where the error was detected. ``None``
        means "no line context".
    snippet
        The text of the offending line. If omitted, callers usually
        do not have access to the line text (e.g., when a section
        is missing entirely).
    column
        1-based column where the error starts within ``snippet``.
        Used to draw a caret. ``None`` means "no column context".

    Examples
    --------
    >>> err = ParseError(
    ...     "unknown section 'Cats'",
    ...     path="office.md",
    ...     line_no=5,
    ...     snippet="Cats: tabby, persian",
    ...     column=1,
    ... )
    >>> str(err).startswith("office.md:5:")
    True
    """

    def __init__(
        self,
        message: str,
        *,
        path: Optional[Union[str, Path]] = None,
        line_no: Optional[int] = None,
        snippet: Optional[str] = None,
        column: Optional[int] = None,
    ) -> None:
        self.message = message
        self.path = str(path) if path is not None else None
        self.line_no = line_no
        self.snippet = snippet
        self.column = column
        super().__init__(self._format())

    # ── Formatting ─────────────────────────────────────────────────────

    def _format(self) -> str:
        parts = []
        head = ""
        if self.path is not None:
            head += self.path
            if self.line_no is not None:
                head += f":{self.line_no}"
            head += ": "
        elif self.line_no is not None:
            head = f"line {self.line_no}: "
        head += "parse error: " + self.message
        parts.append(head)

        if self.snippet is not None:
            parts.append(f"    {self.snippet}")
            if self.column is not None and self.column >= 1:
                # Draw a caret under the offending column.
                parts.append("    " + " " * (self.column - 1) + "^")
        return "\n".join(parts)

    @property
    def short(self) -> str:
        """The single-line head of the formatted message (no snippet)."""
        return self._format().splitlines()[0]
