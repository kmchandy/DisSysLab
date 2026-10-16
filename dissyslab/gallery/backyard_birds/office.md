# backyard_birds: which birds are singing in these recordings?
# Alex is not a language model: it is BirdNET, a classifier.

sources:
    clips: audio_folder(path="./samples/", glob="*.mp3", max_files=10)

sinks:
    intelligence_display(color="level", lines=["file"])
    jsonl_recorder(path="bird_detections.jsonl")

agents:
    Alex: bird_classifier(min_confidence=0.5)

connections:
    clips -> Alex -> intelligence_display, jsonl_recorder
