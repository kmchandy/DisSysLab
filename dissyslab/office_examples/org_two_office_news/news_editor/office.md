# news_editor: one sentence about each article.

inputs:
    articles

outputs:
    briefings

agents:
    Sue: summarizer

connections:
    articles -> Sue -> briefings
