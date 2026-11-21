# cake_room: three detectives and a judge share one whiteboard (Lab 2).

sources:
    evidence: file_source(path="evidence.jsonl")

sinks:
    report: jsonl_recorder(path="report.jsonl")

agents:
    Board: board
    Rex: router(on="to")
    Pip: door_detective
    Quinn: shop_detective
    Rae: fridge_detective
    Judy: judge

connections:
    evidence -> Board -> Rex
    Rex.door -> Pip -> Board
    Rex.shop -> Quinn -> Board
    Rex.fridge -> Rae -> Board
    Rex.judge -> Judy -> report
