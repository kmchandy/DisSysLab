---
emits: one of eight topics, from politics to entertainment
in: text
out: topic (politics | business | technology | science | health | sports | entertainment | other)
---
You read one news article, given as a JSON object. Its "title" and "text"
fields are the headline and the body.

Assign it exactly one topic:

- politics: government, elections, diplomacy, war.
- business: markets, companies, industry, trade.
- technology: software, hardware, AI, the internet, science applied to
  products or daily life.
- science: research findings in physics, biology, medicine, climate,
  space, when not tied to a product.
- health: public health, medicine, healthcare policy, pandemics.
- sports: competitive athletics and games.
- entertainment: film, TV, music, celebrity, gaming.
- other: anything that does not clearly fit one of the seven above. Use
  it when you would have to guess.

Example. For the article
{"title": "AI startup raises $50M to automate code review", "text": "Series B funding led by Sequoia..."}
return {"topic": "technology"}

Return only a JSON object with one field, "topic", whose value is one of
the eight words above, in lower case.
