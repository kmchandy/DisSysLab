# Office: news_monitor

Inputs: article_in
Outputs: article_out

Sinks: discard

Agents:
Alex is a correspondent.
Morgan is an analyst.

Connections:
article_in's destination is Alex.
Alex's analyst is Morgan.
Alex's discard is discard.
Morgan's output is article_out.
Morgan's discard is discard.
