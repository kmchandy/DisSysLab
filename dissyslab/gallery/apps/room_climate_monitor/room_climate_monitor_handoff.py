OFFICE_NAME = "room_climate_monitor"


# ── TEMP_SENSOR / HUMIDITY_SENSOR ───────────────────────────────────────
# No registered hardware-sensor source exists in docs/SOURCES_AND_SINKS.md
# (only RSS feeds, weather/stocks APIs, BlueSky, webhook, MCP, gmail,
# calendar). Reclassified from kind="source" to kind="transform", per
# phase3_source_sink_matching.md's "when nothing fits" -> "stand-in body
# for building/testing" path. Each is now driven by one message from the
# registered `starter` source (a single {"signal": "start"} kick) and
# fires its whole fixed reading sequence in response. Approved by Al
# (2026-07-20): stand-in test data, not real sensor integration.

def _make_temp_sensor_fn():
    _READINGS = [70.0, 82.0, 79.0, 85.0]
    _TIMES = [
        "2026-07-20T10:00:00Z", "2026-07-20T10:01:00Z",
        "2026-07-20T10:02:00Z", "2026-07-20T10:03:00Z",
    ]

    def temp_sensor_fn(msg):
        return [({"temp": v, "timestamp": t}, "out") for v, t in zip(_READINGS, _TIMES)]

    return temp_sensor_fn


def _make_humidity_sensor_fn():
    _READINGS = [45.0, 65.0, 55.0, 70.0]
    _TIMES = [
        "2026-07-20T10:00:00Z", "2026-07-20T10:01:00Z",
        "2026-07-20T10:02:00Z", "2026-07-20T10:03:00Z",
    ]

    def humidity_sensor_fn(msg):
        return [({"humidity": v, "timestamp": t}, "out") for v, t in zip(_READINGS, _TIMES)]

    return humidity_sensor_fn


# ── CHECKER ──────────────────────────────────────────────────────────────
# Phase 2 description: "Read a paired temperature-and-humidity reading for
# the same time. If the temperature is above the 'too hot' threshold and
# the humidity is above the 'too humid' threshold at the same time, write
# a short alert describing both readings and send it on alert. Otherwise
# send nothing." Thresholds weren't given numeric values by Track A; Al
# set them to 80F / 60% (2026-07-20).
#
# NOTE: out_ports=["alert"] is CHECKER's single outbox. Per
# phase3_assistant_instructions.md #3, a single-outport transform must
# always return the literal status string "out" at runtime (assemble.py
# normalizes out_ports=("alert",) -> ("out",) when writing the Role's
# `statuses`), regardless of the semantic name used here for readability.

def _make_checker_fn():
    _TEMP_THRESHOLD_F = 80.0
    _HUMIDITY_THRESHOLD_PCT = 60.0

    def checker_fn(msg):
        temp = msg["temp"]
        humidity = msg["humidity"]
        timestamp = msg.get("timestamp")
        if temp > _TEMP_THRESHOLD_F and humidity > _HUMIDITY_THRESHOLD_PCT:
            when = f" at {timestamp}" if timestamp else ""
            text = (
                f"ALERT: room too hot and humid{when} — "
                f"temperature {temp:.0f}°F (threshold {_TEMP_THRESHOLD_F:.0f}°F), "
                f"humidity {humidity:.0f}% (threshold {_HUMIDITY_THRESHOLD_PCT:.0f}%)."
            )
            return [({"temp": temp, "humidity": humidity, "timestamp": timestamp, "text": text}, "out")]
        return None

    return checker_fn


AGENTS = [
    dict(name="STARTER", kind="source", in_ports=[], out_ports=["out"],
         registered_as="starter", registered_args={}),

    dict(name="TEMP_SENSOR", kind="transform", in_ports=["in"], out_ports=["out"],
         description="The room's temperature sensor; emit one temperature reading (value and timestamp) every few minutes.",
         body_kind="python", body_fn=_make_temp_sensor_fn, body_prompt=None, approved=True),

    dict(name="HUMIDITY_SENSOR", kind="transform", in_ports=["in"], out_ports=["out"],
         description="The room's humidity sensor; emit one humidity reading (value and timestamp) every few minutes, on the same cadence as the temperature sensor so readings can be paired.",
         body_kind="python", body_fn=_make_humidity_sensor_fn, body_prompt=None, approved=True),

    dict(name="JOIN", kind="coordinator", in_ports=["temp", "humidity"], out_ports=["out"],
         registered_as="merge_synch", registered_args={}),

    dict(name="CHECKER", kind="transform", in_ports=["in"], out_ports=["alert"],
         description="Read a paired temperature-and-humidity reading for the same time. If the temperature is above the 'too hot' threshold and the humidity is above the 'too humid' threshold at the same time, write a short alert describing both readings and send it on alert. Otherwise send nothing.",
         body_kind="python", body_fn=_make_checker_fn, body_prompt=None, approved=True),

    dict(name="FACILITIES", kind="sink", in_ports=["in"], out_ports=[],
         description="The concrete place the facilities team receives alerts (for example, an email inbox, a ticketing system, or a shared alerts channel); deliver each alert there.",
         registered_as="console_printer", registered_args={}),
]

CONNECTIONS = [
    ("STARTER", "out", "TEMP_SENSOR", "in"),
    ("STARTER", "out", "HUMIDITY_SENSOR", "in"),
    ("TEMP_SENSOR", "out", "JOIN", "temp"),
    ("HUMIDITY_SENSOR", "out", "JOIN", "humidity"),
    ("JOIN", "out", "CHECKER", "in"),
    ("CHECKER", "alert", "FACILITIES", "in"),
]
