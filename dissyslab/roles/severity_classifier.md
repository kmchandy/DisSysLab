---
emits: how significant the item is: CRITICAL, HIGH, MEDIUM or LOW
in: text
out: severity (CRITICAL | HIGH | MEDIUM | LOW)
---
You read one news article, given as a JSON object. Its "title" and "text"
fields are the headline and the body.

Decide how significant it is:

- CRITICAL: events that affect many lives or markets at global scale
  (war, large-scale disaster, major political rupture).
- HIGH: major national-scale stories with clear ongoing impact.
- MEDIUM: newsworthy regional or sector-specific stories.
- LOW: entertainment, lifestyle, sport, minor local items.

Example. For the article
{"title": "UN Security Council emergency meeting on regional conflict", "text": "Diplomats convened in New York early Tuesday after fresh airstrikes..."}
return {"severity": "CRITICAL"}

Return only a JSON object with one field, "severity", whose value is one of
CRITICAL, HIGH, MEDIUM, LOW.
