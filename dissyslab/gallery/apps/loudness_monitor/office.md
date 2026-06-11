# Office: loudness_monitor

Sources: audio_clip(path="./samples/thunderstorm.wav", chunk_ms=200)
Sinks:   intelligence_display

Agents:
Alex is an rms_meter.
Bryn is a threshold_detector(db_threshold=-30, debounce_ms=400).

Connections:
audio_clip's destination is Alex.
Alex's out is Bryn.
Bryn's out is intelligence_display.
