# Network: two_office_news

Sources: al_jazeera(max_articles=5), bbc_world(max_articles=5), npr_news(max_articles=5)
Sinks: intelligence_display

Offices:
  news_monitor is gallery/org_two_office_news/news_monitor
  news_editor is gallery/org_two_office_news/news_editor

Connections:
al_jazeera's destination is news_monitor's article_in.
bbc_world's destination is news_monitor's article_in.
npr_news's destination is news_monitor's article_in.
news_monitor's article_out is news_editor's article_in.
news_editor's article_out is intelligence_display.
