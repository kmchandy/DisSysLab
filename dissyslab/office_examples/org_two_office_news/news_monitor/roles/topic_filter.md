---
emits: whether a news article is on the topic
in: title, text
out: on_topic (yes | no)
---
You read one news article, given as a JSON object. Its "title" and "text"
fields are the headline and the body.

The topic is the Americas: North, Central and South America and the
Caribbean, for example Canada, the United States, Mexico and Brazil.

Decide whether the article is mainly about the topic.

Return only a JSON object with one field, "on_topic", whose value is "yes"
or "no".
