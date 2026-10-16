# arxiv_radar: new papers from three arXiv categories, classified and rated
# for relevance to the reader's interests.

sources:
    arxiv_cs_ai(max_articles=3)
    arxiv_cs_lg(max_articles=3)
    arxiv_cs_cl(max_articles=3)

sinks:
    intelligence_display(title="title", text="abstract", color="relevance",
                         lines=["authors", "paper_type", "reason"])

agents:
    Carla: paper_classifier
    Iris: relevance_rater

connections:
    arxiv_cs_ai, arxiv_cs_lg, arxiv_cs_cl -> Carla -> Iris -> intelligence_display
