---
emits: one plain-English sentence saying what the item is about
in: title, text
out: summary
---
You read one news article, given as a JSON object. Its "title" and "text"
fields are the headline and the body.

Write one plain sentence, under 30 words, that says what it is about.
Use only facts in the article.

Return only a JSON object with one field, "summary", whose value is the
sentence.
