# test_role_parser.py

import json
import re
from anthropic import Anthropic

client = Anthropic()

ROLE_PARSER_PROMPT = """You are a compiler that extracts structured information from a role description.

A role description describes a job. The role receives one message and responds
by sending zero or more messages, each addressed to a destination role.

Extract:
1. role_name — from the # Role: heading or the opening sentence
2. sends_to — inferred from anywhere in the description where a message is
   explicitly sent to a named destination. Only include a destination if it
   is explicitly stated in the description.

Return JSON only, no explanation, no nested JSON:
{
  "role_name": "name",
  "sends_to": ["destination1", "destination2"]
}"""

TEST_ROLES = {
    "standard": """
# Role: editor
You are an editor who receives news articles and sends articles to a copywriter and to an archivist.
Your job is to score sentiment. If score < 0.25 or > 0.75, send to archivist. Otherwise send to copywriter.
""",
    "informal": """
# Role: editor
You are an editor. Read each article and decide if it's interesting.
Good articles go to the copywriter. Boring ones get filed with the archivist.
""",
    "imperative": """
# Role: editor
You are an editor. Score the sentiment of each article from 0 to 1.
Send strong opinions to the archivist.
Send lukewarm articles to the copywriter for rewriting.
""",
    "verbose": """
# Role: editor
You are a senior news editor responsible for quality control.
When an article arrives, analyze its sentiment carefully.
Articles with strong sentiment should be forwarded to the archivist for filing.
Articles with neutral sentiment need more work — pass them along to the copywriter.
""",
}


def parse_role(text):
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=ROLE_PARSER_PROMPT,
        messages=[{"role": "user", "content": text}]
    )
    raw = response.content[0].text
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    return json.loads(match.group())


if __name__ == "__main__":
    print()
    for name, text in TEST_ROLES.items():
        result = parse_role(text)
        status = "✓" if set(result["sends_to"]) == {
            "copywriter", "archivist"} else "✗"
        print(f"  {status} [{name:12}]  sends_to: {result['sends_to']}")
    print()
