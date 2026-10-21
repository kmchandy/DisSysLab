# incident_room: three analysts and a writer share one whiteboard (Lab 2).

sources:
    evidence: file_source(path="evidence.jsonl")

sinks:
    report: jsonl_recorder(path="report.jsonl")
    console_printer

agents:
    Board: board
    Rex: router(on="to")
    Lena: logs_analyst
    Max: metrics_analyst
    Rae: reports_analyst
    Wren: incident_writer

connections:
    evidence -> Board -> Rex
    Rex.logs -> Lena -> Board
    Rex.metrics -> Max -> Board
    Rex.reports -> Rae -> Board
    Rex.writer -> Wren -> report, console_printer
