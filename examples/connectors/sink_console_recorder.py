# dsl/connectors/sink_console_recorder.py

from __future__ import annotations

from typing import Any, Dict, Optional
import json


class ConsoleRecorder:
    """
    Console recorder: pretty-print each input message dict.

    Prints messages in a readable, formatted style with:
      - Box drawing characters for visual structure
      - Indented key-value pairs
      - Color coding (optional)
      - Smart formatting for different data types

    Returns the input message unchanged (convenient for debugging),
    but catalog "outputs" should be {} because this is a sink.
    """

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        float_sig: int = 6,
        sort_keys: bool = True,
        max_str: int = 200,
        prefix: str = "",
        use_colors: bool = True,
        compact: bool = False,
    ):
        self._name = name or "console_recorder"
        self.float_sig = int(float_sig)
        self.sort_keys = bool(sort_keys)
        self.max_str = int(max_str)
        self.prefix = prefix
        self.use_colors = use_colors
        self.compact = compact
        self._count = 0

        # ANSI color codes
        self._colors = {
            'key': '\033[36m',      # Cyan
            'string': '\033[32m',   # Green
            'number': '\033[33m',   # Yellow
            'bool': '\033[35m',     # Magenta
            'none': '\033[90m',     # Gray
            'reset': '\033[0m',     # Reset
            'header': '\033[1;34m',  # Bold Blue
        }

    @property
    def __name__(self) -> str:
        return self._name

    def _color(self, text: str, color_type: str) -> str:
        """Apply color if colors are enabled"""
        if not self.use_colors:
            return text
        return f"{self._colors.get(color_type, '')}{text}{self._colors['reset']}"

    def _fmt_value(self, v: Any) -> str:
        """Format a value with appropriate color"""
        if v is None:
            return self._color("None", "none")

        # bool is a subclass of int; handle it first.
        if isinstance(v, bool):
            return self._color(str(v), "bool")

        if isinstance(v, int):
            return self._color(str(v), "number")

        if isinstance(v, float):
            try:
                formatted = format(v, f".{self.float_sig}g")
                return self._color(formatted, "number")
            except Exception:
                return self._color(str(v), "number")

        if isinstance(v, str):
            s = v
            if len(s) > self.max_str:
                s = s[: self.max_str] + "…"
            return self._color(s, "string")

        if isinstance(v, (list, dict)):
            # Pretty format nested structures
            try:
                formatted = json.dumps(v, indent=2, default=str)
                return self._color(formatted, "string")
            except Exception:
                return repr(v)

        return repr(v)

    def _print_compact(self, msg: Dict[str, Any]):
        """Print message in compact single-line format"""
        keys = list(msg.keys())
        if self.sort_keys:
            try:
                keys.sort()
            except Exception:
                pass

        parts = []
        for k in keys:
            try:
                key_colored = self._color(k, "key")
                value_formatted = self._fmt_value(msg.get(k))
                parts.append(f"{key_colored}={value_formatted}")
            except Exception:
                parts.append(f"{k}=<unprintable>")

        line = " ".join(parts)
        print(f"{self.prefix}{line}")

    def _print_pretty(self, msg: Dict[str, Any]):
        """Print message in pretty multi-line format"""
        self._count += 1

        # Header
        header = f"Message #{self._count}"
        print(f"\n{self.prefix}{'─' * 60}")
        print(f"{self.prefix}{self._color(header, 'header')}")
        print(f"{self.prefix}{'─' * 60}")

        # Get sorted keys
        keys = list(msg.keys())
        if self.sort_keys:
            try:
                keys.sort()
            except Exception:
                pass

        # Print each key-value pair
        for i, k in enumerate(keys):
            is_last = (i == len(keys) - 1)
            prefix_char = "└──" if is_last else "├──"

            try:
                key_colored = self._color(k, "key")
                value_formatted = self._fmt_value(msg.get(k))

                # Handle multi-line values
                if '\n' in str(value_formatted):
                    lines = value_formatted.split('\n')
                    print(f"{self.prefix}{prefix_char} {key_colored}:")
                    continuation = "    " if is_last else "│   "
                    for line in lines:
                        print(f"{self.prefix}{continuation}{line}")
                else:
                    print(
                        f"{self.prefix}{prefix_char} {key_colored}: {value_formatted}")
            except Exception:
                print(f"{self.prefix}{prefix_char} {k}: <unprintable>")

    def __call__(self, msg: Dict[str, Any]):
        if not isinstance(msg, dict):
            # Defensive: still print something useful.
            print(f"{self.prefix}{self._fmt_value(msg)}")
            return msg

        if self.compact:
            self._print_compact(msg)
        else:
            self._print_pretty(msg)

        return msg

    def finalize(self):
        """Print final summary"""
        if not self.compact and self._count > 0:
            print(f"\n{self.prefix}{'═' * 60}")
            print(
                f"{self.prefix}{self._color(f'Total messages: {self._count}', 'header')}")
            print(f"{self.prefix}{'═' * 60}\n")
        return None

    run = __call__
