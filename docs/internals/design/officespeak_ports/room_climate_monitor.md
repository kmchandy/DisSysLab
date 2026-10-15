# Paper port 5 of 5: `room_climate_monitor`

Ported by hand against `officespeak_revised.md` (with ports 2–4's additions).
Nothing here runs yet.

Two sensors report independently: one temperature, one humidity. A
synchronizer joins one reading of each, and a checker raises an alert when
the room is both too hot and too humid. It is the worked example for joining
branches.

## Before

```
Sources: starter
Sinks: console_printer

Agents:
TEMP_SENSOR is a temp_sensor.
HUMIDITY_SENSOR is a humidity_sensor.
JOIN is a synchronizer(inboxes=['temp', 'humidity']).
CHECKER is a checker.

Connections:
starter's out are TEMP_SENSOR and HUMIDITY_SENSOR.
TEMP_SENSOR's out is JOIN's temp.
HUMIDITY_SENSOR's out is JOIN's humidity.
JOIN's out is CHECKER.
CHECKER's out is console_printer.
```

- The two "sensors" are generated Python roles, not sources. There was no
  way for an office to have its own source, so each is woken by `starter`
  and emits four readings held in the code: `{"temp": 82.0}`,
  `{"humidity": 65.0}`. The hand-off notes had timestamps on the readings;
  the shipped roles dropped them.
- So `JOIN` pairs the k-th temperature with the k-th humidity, by position
  alone.
- `checker.py` returns a new `{"temp", "humidity", "alert": true}` when
  temp > 80 and humidity > 60, and `None` otherwise: the message silently
  disappears.

## After

```
# Office: room_climate_monitor

Sources: temp_sensor is a file_source(filepath="temp.jsonl"),
         humidity_sensor is a file_source(filepath="humidity.jsonl")
Sinks: console_printer, discard

Agents:
Join is a synchronizer(inboxes=["temp", "humidity"], on="slot").
Checker is a checker(max_temp=80, max_humidity=60).
Rex is a router(on="alert").

Connections:
temp_sensor's out is Join's temp.
humidity_sensor's out is Join's humidity.
Join's out is Checker.
Checker's out is Rex.
Rex's yes is console_printer.
Rex's no is discard.
```

```
temp_sensor ─────→ Join's temp     ┐
                                    ├→ Join → Checker → Rex ─ yes → console_printer
humidity_sensor ─→ Join's humidity ┘                       └ no  → discard
```

`temp.jsonl` and `humidity.jsonl` (the readings that were in the code; `slot`
is the minute each reading belongs to):

```
{"slot": "10:00", "temp": 70.0}        {"slot": "10:00", "humidity": 45.0}
{"slot": "10:01", "temp": 82.0}        {"slot": "10:01", "humidity": 65.0}
{"slot": "10:02", "temp": 79.0}        {"slot": "10:02", "humidity": 55.0}
{"slot": "10:03", "temp": 85.0}        {"slot": "10:03", "humidity": 70.0}
```

`roles/checker.py`

```python
"""
---
emits: whether the room is both too hot and too humid
in: temp, humidity
out: alert (yes | no)
---
Arguments: max_temp (default 80), max_humidity (default 60).
"""

def step(item, settings):
    hot = item["temp"] > settings["max_temp"]
    humid = item["humidity"] > settings["max_humidity"]
    return {"alert": "yes" if hot and humid else "no"}


class Checker:
    def __init__(self, max_temp=80, max_humidity=60):
        self.settings = {"max_temp": max_temp, "max_humidity": max_humidity}

    def __call__(self, item):
        return step(item, self.settings)
```

The console shows the same two alerts as before (10:01 and 10:03), now with
their `slot`:

```
{"slot": "10:01", "temp": 82.0, "humidity": 65.0, "alert": "yes"}
{"slot": "10:03", "temp": 85.0, "humidity": 70.0, "alert": "yes"}
```

What disappears: `starter`, three generated files that import `dissyslab`,
the readings held in code, and the silent `None`. What appears: two data
files, a key on the synchronizer, and a router whose `no` branch says where
the quiet readings go.

## Findings for the spec

1. **Sensors are sources.** The old roles pretended to be sources because an
   office could not have its own. With `sources/` (port 3) a real sensor is
   `sources/temp_sensor.py` declaring `out: slot, temp`; for testing,
   `file_source` stands in. The office is the same either way except for the
   one `Sources:` line. A good teaching point: swap the stand-in for the real
   thing without touching the network.

2. **`file_source`'s fields come from the file, not the code.** Its docstring
   cannot declare `out:`. **Proposal:** `dsl check` reads the file and reports
   the fields it finds; every line must have the same fields, or it is an
   error. Nothing new to write, and nothing hidden: the check shows what it
   derived, as it does for a nested office's boundary fields (3.4). Same for
   `list_source`.

3. **The key is a design decision.** Two independent sensors never stamp
   exactly the same time, so `on="timestamp"` would never match. The key must
   be something both sides agree on: here a `slot`, the minute a reading
   belongs to. A real sensor source would compute its slot. One paragraph for
   the synchronizer's teaching page; no spec change. The shipped office is
   also a live case of port 2's hazard: with positions only, one lost
   humidity reading would pair every later temperature with the wrong
   humidity.

4. **A role that returns nothing.** Returning `None` dropped the message
   silently. Under 4.1 an annotator always returns an object, so the decision
   becomes a field and the drop becomes a visible `discard` branch.
   Consistent with the spec; no change.

5. **`starter` is unused in all five ports.** In the three that used it
   (`debate`, `returns_desk`, this one) it only woke a role that stood in for
   a source by holding or reading data. Seven gallery offices list it; I have
   not checked the other four. **Proposal:** retire `starter` if those four
   turn out the same.

6. **`are … and …`.** `starter's out are TEMP_SENSOR and HUMIDITY_SENSOR.` is
   accepted today (four gallery offices use it). **Proposal:** teach and
   generate one form (`is`, commas), and keep accepting the other, since it
   hides nothing.
