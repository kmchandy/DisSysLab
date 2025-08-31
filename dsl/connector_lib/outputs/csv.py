from __future__ import annotations
from typing import Any, Dict, List, Iterable
import csv
import pathlib
from .base import OutputConnector


class OutputConnectorCSV(OutputConnector):
    """
    Writes a CSV file on {"cmd":"flush","payload":[...],"meta":{...}}.

    'payload' may be:
      - List[Dict[str, Any]]  -> headers = given or inferred from first row's keys
      - List[List[Any]]       -> headers must be provided

    meta:
      {"path":"...", "encoding":"utf-8", "fieldnames":[...], "include_header": True, "mode":"w"}
        - mode: "w" to overwrite (default) or "a" to append
        - include_header: write header row if True and mode == "w"
    """

    def _flush(self, payload: List[Any], meta: Dict[str, Any]) -> None:
        path = pathlib.Path(meta["path"])
        enc = meta.get("encoding", "utf-8")
        mode = meta.get("mode", "w")
        include_header = bool(meta.get("include_header", True))

        path.parent.mkdir(parents=True, exist_ok=True)

        if not payload:
            # Write empty file if "w"; do nothing on "a"
            if mode == "w":
                path.write_text("", encoding=enc)
            return

        # Detect dict-rows vs list-rows
        dict_rows = isinstance(payload[0], dict)
        with path.open(mode, newline="", encoding=enc) as f:
            if dict_rows:
                fieldnames = meta.get("fieldnames")
                if fieldnames is None:
                    # infer from first row (stable order if OrderedDict-like)
                    fieldnames = list(payload[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if mode == "w" and include_header:
                    writer.writeheader()
                for row in payload:
                    if not isinstance(row, dict):
                        raise TypeError(
                            "CSV writer: mixed row types; all rows must be dicts")
                    writer.writerow(row)
            else:
                # list rows
                fieldnames = meta.get("fieldnames")
                if fieldnames is None:
                    raise ValueError(
                        "CSV writer: fieldnames required for list rows")
                writer = csv.writer(f)
                if mode == "w" and include_header:
                    writer.writerow(fieldnames)
                for row in payload:
                    if not isinstance(row, list):
                        raise TypeError(
                            "CSV writer: mixed row types; all rows must be lists")
                    writer.writerow(row)
