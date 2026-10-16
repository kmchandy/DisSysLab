# org_two_office_news

An office can be one agent of a bigger office. This office has no agents
of its own: two offices, `news_monitor` and `news_editor`, connected like
any two agents.

    al_jazeera, bbc_world -> monitor.articles
    monitor.kept -> editor.articles
    editor.briefings -> intelligence_display

Each inner office declares its ports under `inputs:` and `outputs:`.
Inside, an input acts like a source and an output like a sink
(`articles -> Felix`, `Rex.yes -> kept`). Outside, they are ports, like a
function's parameters (`monitor.articles`).

`news_monitor` is `org_news_filter`'s filter and router; `news_editor`
uses the built-in `summarizer`. An office with `inputs:` cannot be run on
its own: run the outer one.
