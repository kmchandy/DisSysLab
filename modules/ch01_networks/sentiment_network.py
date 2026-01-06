# modules/ch01_networks/sentiment_network.py

from dsl import network
from dsl.decorators import msg_map
from dsl.connectors.sink_console_recorder import ConsoleRecorder
from .simple_text_analysis import from_social_media, clean_text, analyze_sentiment, to_results


clean = msg_map(input_keys=["text"], output_keys=["text"])(clean_text)

sentiment_analysis = msg_map(
    input_keys=["text"], output_keys=["sentiment", "score"])(analyze_sentiment)

console_recorder = ConsoleRecorder()


# Create and run network
"""
Network Structure:

    +--------------------+
    | from_social_media  | source: generates posts as dicts
    +--------------------+
             |  msg:  {"text": "..."}
             v
    +--------------------+
    |       clean        | transformer: removes emojis
    +--------------------+
             |  msg:  {"text": "..."}
             v
    +--------------------+
    | sentiment_analysis | transformer: determines sentiment
    +--------------------+
             | msg:  {"text": "..."
             v
    +--------------------+
    | console_recorder   | sink: stores and displays results
    +--------------------+
"""

g = network([
    (from_social_media, clean),
    (clean, sentiment_analysis),
    (sentiment_analysis, console_recorder.run)
])

g.run_network()
