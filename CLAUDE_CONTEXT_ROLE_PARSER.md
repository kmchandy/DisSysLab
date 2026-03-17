# DisSysLab — Role Parser

## What a Role Is

A role is a reusable job description for an agent in a DisSysLab organization.
A role describes:
- What the agent receives
- What output channels it sends to
- Any persistent state carried in the message
- Its job
- Its routing rules

Roles are defined once in `roles.md` and reused across many offices.
A role has no knowledge of the org chart — it only knows its own job
and its output channel names.

---

## Role Template

```
# Role: role_name

You are a [job title] who receives [input] and sends
[output] to a [role1] and to a [role2].

The [message] has a section called "[field]" whose value
is a [type]. If absent, treat as [default].

Your job is to [task].

If [condition], send to [role1].
If [condition], send to [role2] and modify [field] by [operation].
```

**Rules for writing a role:**

1. The opening sentence declares ALL output channels. Every "send to X"
   in the routing rules must use a channel name declared here.

2. Persistent state is declared before the job description. Any field
   that accumulates across agents — counters, flags, scores — must be
   declared explicitly. Claude cannot reliably infer implicit state.

3. The job description is one or two sentences. It describes what the
   role does, not where it sends output.

4. Routing rules use exact channel names from the opening sentence.
   Each rule ends with "send to [channel]" or
   "send to [channel] and modify [field] by [operation]".

5. A role with only one output channel omits routing rules entirely —
   it always sends to that channel.

---

## Role Parser Prompt

Use this prompt to extract structured JSON from a role description.

```
You are a compiler that reads a role description and extracts
structured information.

A role description follows this template:
- Opening sentence: "You are a [job title] who receives [input]
  and sends [output] to a [role1]." or "...to a [role1] and
  to a [role2]." or "...to [role1], [role2], [role3]."
  The names after "send to" are output channels.
- Optional persistent state: "The [message] has a section called
  '[field]' whose value is a [type]. If absent, treat as [default]."
- Job description: "Your job is to [task]."
- Routing rules: "If [condition], send to [role]." or
  "If [condition], send to [role] and modify [field] by [operation]."

Return JSON only, no explanation, no nested JSON:
{
  "role_name": "name from # Role: heading",
  "receives": "what the role receives",
  "sends_to": ["role1", "role2"],
  "persistent_state": [
    {"field": "field_name", "type": "type", "default": "default_value"}
  ],
  "job": "one sentence summary of the job",
  "routing_rules": [
    {
      "condition": "condition text",
      "send_to": ["role"],
      "modify": "full modification instruction or null"
    }
  ]
}
```

---

## Example Input

```
# Role: editor

You are an editor who receives news articles and sends
articles to a copywriter and to an archivist.

The article has a section called "rewrites" whose value
is a number. If absent, treat as 0.

Your job is to analyze the sentiment of each article
and score it from 0.0 (most negative) to 1.0 (most positive).

If the score is less than 0.25 or greater than 0.75,
send the article to the archivist.
If the score is between 0.25 and 0.75 and rewrites < 3,
send the article to the copywriter and modify rewrites by adding 1.
If the score is between 0.25 and 0.75 and rewrites >= 3,
send the article to the archivist.
```

## Example Output

```json
{
  "role_name": "editor",
  "receives": "news articles",
  "sends_to": ["copywriter", "archivist"],
  "persistent_state": [
    {"field": "rewrites", "type": "number", "default": 0}
  ],
  "job": "analyze the sentiment of each article and score it from 0.0 (most negative) to 1.0 (most positive)",
  "routing_rules": [
    {
      "condition": "score < 0.25 or score > 0.75",
      "send_to": ["archivist"],
      "modify": null
    },
    {
      "condition": "0.25 <= score <= 0.75 and rewrites < 3",
      "send_to": ["copywriter"],
      "modify": "add 1 to rewrites"
    },
    {
      "condition": "0.25 <= score <= 0.75 and rewrites >= 3",
      "send_to": ["archivist"],
      "modify": null
    }
  ]
}
```

---

## Example: Single-Output Role

A role with one output channel needs no routing rules.

```
# Role: writer

You are a writer who receives news articles and sends
articles to a client.

Your job is to rewrite the article to be more strongly
opinionated — push the sentiment either more positive or
more negative, whichever requires less change.
Preserve all fields from the input message.
```

Extracted JSON:

```json
{
  "role_name": "writer",
  "receives": "news articles",
  "sends_to": ["client"],
  "persistent_state": [],
  "job": "rewrite the article to be more strongly opinionated, preserving all fields",
  "routing_rules": [
    {
      "condition": "always",
      "send_to": ["client"],
      "modify": null
    }
  ]
}
```
