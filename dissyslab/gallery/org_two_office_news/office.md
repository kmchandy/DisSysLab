# org_two_office_news: an office made of two offices.

sources:
    al_jazeera(max_articles=5)
    bbc_world(max_articles=5)

sinks:
    intelligence_display(title="title", text="summary")

agents:
    monitor: office(path="news_monitor")
    editor: office(path="news_editor")

connections:
    al_jazeera, bbc_world -> monitor.articles
    monitor.kept -> editor.articles
    editor.briefings -> intelligence_display
