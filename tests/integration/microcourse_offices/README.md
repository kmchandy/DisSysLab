# Offices behind the micro-course's illustrations

`course/microcourse.html` shows four offices that are not in the gallery
(tagged "illustration" on the slides): `requests` (an LLM author),
`refunds` (the gallery's clerk, no gate), `felix` (the gallery's
`topic_filter`, with a model that answers "maybe") and `booking` (a sink
with `in:`). `tests/integration/test_course_pages.py` runs each one, with
the scripted model where a model is needed, and checks that every line of
output the slides quote is what `dsl run` prints. `refunds` and `felix`
take their roles from the gallery at test time, so they cannot drift.
