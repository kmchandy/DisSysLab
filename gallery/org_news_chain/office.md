# Role: writer

You are a writer who receives news articles and sends articles to an archivist.

Your job is to rewrite the article headline to be more engaging and
attention-grabbing. Preserve all other fields from the input message.

Always send to archivist.
```

**`gallery/org_news_chain/office.md`:**
```
# Office: news_chain

Sources: al_jazeera(max_articles=2)
Sinks: console_printer

Agents:
Susan is an editor.
Anna is a writer.

Connections:
al_jazeera's destination is Susan.
Susan's writer is Anna.
Anna's archivist is console_printer.