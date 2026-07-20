# Office: shipment_release

Sources: starter
Sinks: jsonl_recorder(path='releases.jsonl'), console_printer

Agents:
SCAN is a scan.
MANIFEST is a manifest.
MATCH is a match.

Connections:
starter's destination are SCAN and MANIFEST.
SCAN's out is MATCH.
MANIFEST's out is MATCH.
MATCH's out are jsonl_recorder and console_printer.
