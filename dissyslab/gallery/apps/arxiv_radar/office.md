# Office: arxiv_radar

Sources: arxiv_cs_ai(max_articles=3), arxiv_cs_lg(max_articles=3), arxiv_cs_cl(max_articles=3)
Sinks: intelligence_display

Agents:
Carla is a paper_classifier.
Iris is a relevance_rater.

Connections:
arxiv_cs_ai's destination is Carla.
arxiv_cs_lg's destination is Carla.
arxiv_cs_cl's destination is Carla.

Carla's out is Iris.
Iris's out is intelligence_display.
