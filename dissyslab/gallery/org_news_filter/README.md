# org_news_filter

Two news feeds. Felix, an English role, decides whether each article is
about a topic and adds `on_topic: yes | no`. Rex, a router, sends `yes`
articles to the screen and `no` articles to `discard`.

    al_jazeera, bbc_world -> Felix -> Rex
    Rex.yes -> console_printer
    Rex.no -> discard

**Make it yours.** Change the paragraph that starts "The topic is" in
`roles/topic_filter.md`. The field is called `on_topic`, not
`about_americas`, so nothing else changes.
