# Office: backyard_birds

Sources: audio_folder(path="./samples/", glob="*.mp3", max_files=10)
Sinks: intelligence_display,
       jsonl_recorder(path="bird_detections.jsonl")

Agents:
Alex is a bird_classifier(min_confidence=0.5).

Connections:
audio_folder's destination is Alex.
Alex's out is intelligence_display, jsonl_recorder.
