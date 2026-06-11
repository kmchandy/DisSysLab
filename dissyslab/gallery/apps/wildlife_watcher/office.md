# Office: wildlife_watcher

Sources: image_folder(folder="./samples/", max_images=20)
Sinks:   intelligence_display

Agents:
Alex is an animal_classifier.
Bryn is a confidence_filter(min_confidence=0.4, category_field="category", category_whitelist="animal").

Connections:
image_folder's destination is Alex.
Alex's out is Bryn.
Bryn's out is intelligence_display.
