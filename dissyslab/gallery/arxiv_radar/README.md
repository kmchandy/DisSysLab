# arxiv_radar

New papers from three arXiv categories pass through two roles in a row:
Carla adds `paper_type`, Iris adds `relevance` and `reason`. The display
is told which fields to show; it never guesses.

    arxiv_cs_ai, arxiv_cs_lg, arxiv_cs_cl -> Carla -> Iris -> intelligence_display

The arXiv sources read arXiv's RSS feed, so each paper arrives with its
`authors` and `abstract` as fields of their own.

**Make it yours.** The reader's interests are one paragraph of
`roles/relevance_rater.md`.

**A question to try.** Iris does not read Carla's field. Could they run
side by side? What would you add? (A synchronizer, and a key: `url`.)
