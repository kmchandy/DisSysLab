"""
---
emits: one message per bird species heard in an audio clip
kind: author
needs: birdnetlib, librosa, resampy
in: path, filename
out: found (yes | no), title, text, file, level (HIGH | MEDIUM | LOW)
out if found is yes: species, scientific_name, confidence, start_time, end_time
---
Arguments: min_confidence -- detections below this are ignored (default 0.5).

BirdNET is a resource: built once when the office starts, used for every
clip. ``step`` is everything else, and is pure: test it with a
hand-written list of detections, no BirdNET installed.
"""


def level(confidence):
    if confidence >= 0.8:
        return "HIGH"
    if confidence >= 0.5:
        return "MEDIUM"
    return "LOW"


def step(item, detections):
    """BirdNET's detections for one clip -> the messages to send."""
    name = item["filename"]
    if not detections:
        return [{"found": "no", "title": f"No birds in {name}",
                 "text": "No species above the confidence threshold.",
                 "file": name, "level": "LOW"}]
    return [{"found": "yes",
             "title": d["common_name"],
             "text": f"Heard {d['start_time']:.1f}-{d['end_time']:.1f}s into {name}.",
             "file": name,
             "level": level(d["confidence"]),
             "species": d["common_name"],
             "scientific_name": d["scientific_name"],
             "confidence": d["confidence"],
             "start_time": d["start_time"],
             "end_time": d["end_time"]}
            for d in detections]


class BirdClassifier:
    def __init__(self, min_confidence=0.5):
        from birdnetlib.analyzer import Analyzer

        self.settings = {"min_confidence": float(min_confidence)}
        self.analyzer = Analyzer()  # downloads the model (~50 MB) the first time

    def __call__(self, item):
        from birdnetlib import Recording

        recording = Recording(self.analyzer, item["path"],
                              min_conf=self.settings["min_confidence"])
        recording.analyze()
        return step(item, recording.detections)
