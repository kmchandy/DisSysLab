---
emits: the people, organisations, places and events named in the item
in: text
out: entities
---
You read one news article, given as a JSON object. Its "title" and "text"
fields are the headline and the body.

List the named entities it mentions, as an object with exactly four keys,
each a list of strings (an empty list if there are none of that kind):

- "people": named individuals, e.g. "Angela Merkel";
- "organizations": named groups, companies, agencies or alliances, e.g.
  "United Nations";
- "places": named cities, countries, regions or landmarks, e.g. "Beijing";
- "events": named events, summits, treaties or disasters, e.g.
  "G20 Summit".

Use the exact spelling in the article. Do not invent entities. Skip common
nouns ("the president") unless the article gives a proper name. Put each
entity in only one list, the most specific.

Example. For the article
{"title": "BRICS leaders meet in Beijing summit", "text": "Modi and Xi joined Putin in Beijing on Tuesday for the BRICS summit."}
return {"entities": {"people": ["Modi", "Xi", "Putin"], "organizations": ["BRICS"], "places": ["Beijing"], "events": ["BRICS summit"]}}

Return only a JSON object with one field, "entities", whose value is the
object with the four lists.
