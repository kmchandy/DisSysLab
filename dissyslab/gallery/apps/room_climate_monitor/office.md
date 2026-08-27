# Office: room_climate_monitor

# Two sensors, one reading. A temperature agent and a humidity agent
# report independently and a `synchronizer` waits for both before the
# checker judges the room -- the worked example for joining branches.

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
