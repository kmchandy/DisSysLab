# room_climate_monitor

Two sensors report independently. A synchronizer joins one temperature
and one humidity reading for the same minute (`on="slot"`); the checker
adds `alert: yes | no`; a router sends alerts to the screen.

    temp_sensor -> Join.temp
    humidity_sensor -> Join.humidity
    Join -> Checker -> Rex

**The key is a design decision.** Two sensors never stamp exactly the same
time, so they are joined on a value both share: the minute a reading
belongs to. The two files here stand in for real sensors; a real one is a
class in `sources/` declaring `out: slot, temp`, and only its line under
`sources:` changes.
