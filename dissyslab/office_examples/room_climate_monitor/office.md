# room_climate_monitor: alert when the room is both hot and humid.

sources:
    temp_sensor: file_source(path="temp.jsonl")
    humidity_sensor: file_source(path="humidity.jsonl")

sinks:
    console_printer
    discard

agents:
    Join: synchronizer(on="slot")
    Checker: checker(max_temp=80, max_humidity=60)
    Rex: router(on="alert")

connections:
    temp_sensor -> Join.temp
    humidity_sensor -> Join.humidity
    Join -> Checker -> Rex
    Rex.yes -> console_printer
    Rex.no -> discard
