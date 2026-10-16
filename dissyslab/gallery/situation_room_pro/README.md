# situation_room_pro

Three feeds. Sasha drops repeats. Four annotators analyse each article at
the same time, each adding one field (entities, severity, topic,
location). A synchronizer joins the four copies of each article by its
`url`, and Riley writes a headline and a short summary.

    bbc_world, npr_news, al_jazeera -> Sasha -> Eve, Sam, Tom, Greta
    Eve -> Sync.entities      Sam -> Sync.severity
    Tom -> Sync.topic         Greta -> Sync.location
    Sync -> Riley -> intelligence_display, jsonl_recorder

**"Pro" is one argument:** `Riley: writer(ai="anthropic")`. The four
classifiers run on the default (often a small, local) model; the writing
goes to a stronger one.

**The key is `url`.** The deduplicator makes it unique, which is what the
synchronizer needs. If one annotator's reply for an article does not fit
its `out:`, that article alone is held back and reported; the others are
unaffected.

All roles here are built in (`dissyslab/roles/`); this folder has
no `roles/`.
