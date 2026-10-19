# incident_room, design B: a pipeline with contracts, no whiteboard (Lab 2 reference, course staff only).
# The tests lay these files over a copy of dissyslab/gallery/incident_room.

sources:
    evidence: file_source(path="evidence.jsonl")

sinks:
    report: jsonl_recorder(path="report.jsonl")
    console_printer

agents:
    Rex: router(on="kind")
    Lena: logs_finding
    Max: metrics_finding
    Rae: reports_finding
    Sync: synchronizer(on="incident", collect="findings")
    Wren: pipeline_writer

connections:
    evidence -> Rex
    Rex.logs -> Lena -> Sync.logs
    Rex.metrics -> Max -> Sync.metrics
    Rex.reports -> Rae -> Sync.reports
    Sync -> Wren -> report, console_printer
