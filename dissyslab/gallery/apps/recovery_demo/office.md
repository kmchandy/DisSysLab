# Office: recovery_demo

Sources: csv_points_source(path="./samples/points.txt", interval=0.005)
Sinks:   intelligence_display

Agents:
Alex is an inside_classifier.
Bob  is an outside_classifier.
Pi   is a pi_combiner.

Connections:
csv_points_source's destination is Alex, Bob.
Alex's out is Pi.
Bob's out is Pi.
Pi's out is intelligence_display.
