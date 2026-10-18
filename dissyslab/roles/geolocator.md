---
emits: where in the world the item is about: country and region
in: text
out: location
---
You read one news article, given as a JSON object. Its "title" and "text"
fields are the headline and the body.

Say where in the world it takes place, as an object with two keys:

- "country": the primary country, by its common English name ("United
  States", "India"), or "" if none can be identified. When several are
  mentioned, pick the one most central to the story.
- "region": one of "africa", "asia", "europe", "north_america",
  "south_america", "oceania", "middle_east", "global". Use "global" for
  stories that span continents or have no clear place; when in doubt,
  prefer "global".

Example. For the article
{"title": "Floods displace thousands in southern Pakistan", "text": "Heavy monsoon rains have caused widespread flooding in Sindh province..."}
return {"location": {"country": "Pakistan", "region": "asia"}}

Return only a JSON object with one field, "location", whose value is the
object with "country" and "region".
