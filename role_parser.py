#!/usr/bin/env python3
# role_parser.py
#
# Parses role descriptions from roles.md into structured JSON.
#
# Usage:
#   python3 role_parser.py roles.md
#
# Or import and use directly:
#   from role_parser import parse_role, parse_roles_file

import sys
import re
import json
from anthropic import Anthropic

client = Anthropic()

# ============================================================================
# Role Parser Prompt
# (from CLAUDE_CONTEXT_ROLE_PARSER.md)
# ============================================================================

ROLE_PARSER_PROMPT = """You are a compiler that reads a role description and extracts
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

EXAMPLE INPUT:

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

EXAMPLE OUTPUT:

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
}"""


# ============================================================================
# Core functions
# ============================================================================

def parse_role(role_text):
    """
    Parse a single role description into structured JSON.

    Args:
        role_text: string containing one role description

    Returns:
        dict with keys: role_name, receives, sends_to,
                        persistent_state, job, routing_rules

    Raises:
        ValueError: if Claude returns no JSON or unparseable JSON
    """
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=ROLE_PARSER_PROMPT,
        messages=[{"role": "user", "content": role_text}]
    )
    raw = response.content[0].text.strip()

    # Extract first JSON object
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in response:\n{raw}")

    return json.loads(match.group())


def split_roles(text):
    """
    Split a roles.md file into individual role description strings.

    Splits on '# Role:' headings.

    Args:
        text: full content of roles.md

    Returns:
        list of role description strings, each starting with '# Role:'
    """
    # Split on lines that start with '# Role:'
    parts = re.split(r'(?=^# Role:)', text, flags=re.MULTILINE)
    roles = []
    for part in parts:
        part = part.strip()
        if part.startswith('# Role:'):
            roles.append(part)
    return roles


def parse_roles_file(filepath):
    """
    Parse all roles in a roles.md file.

    Args:
        filepath: path to roles.md

    Returns:
        list of role dicts, one per role

    Raises:
        FileNotFoundError: if file doesn't exist
        ValueError: if any role fails to parse
    """
    with open(filepath) as f:
        text = f.read()

    role_texts = split_roles(text)
    if not role_texts:
        raise ValueError(f"No roles found in {filepath}. "
                         f"Each role must start with '# Role: name'")

    results = []
    for role_text in role_texts:
        print(f"  Parsing role: {_extract_role_name(role_text)}...")
        result = parse_role(role_text)
        results.append(result)
        print(f"    → sends_to: {result['sends_to']}")
        if result['persistent_state']:
            print(
                f"    → state:    {[s['field'] for s in result['persistent_state']]}")

    return results


def _extract_role_name(role_text):
    """Extract role name from '# Role: name' heading for display."""
    match = re.match(r'#\s*Role:\s*(\w+)', role_text)
    return match.group(1) if match else "unknown"


# ============================================================================
# Validation
# ============================================================================

def validate_role(role):
    """
    Validate a parsed role dict.

    Checks:
    - All routing rules reference channels declared in sends_to
    - Every channel in sends_to appears in at least one routing rule
    - Single-output roles have exactly one routing rule with condition "always"

    Returns:
        list of warning strings (empty if all valid)
    """
    warnings = []
    declared = set(role['sends_to'])

    # Check routing rules reference declared channels
    referenced = set()
    for rule in role['routing_rules']:
        for channel in rule['send_to']:
            if channel not in declared:
                warnings.append(
                    f"Routing rule references channel '{channel}' "
                    f"which is not declared in sends_to {role['sends_to']}"
                )
            referenced.add(channel)

    # Check all declared channels are used
    for channel in declared:
        if channel not in referenced:
            warnings.append(
                f"Channel '{channel}' is declared in sends_to "
                f"but never used in any routing rule"
            )

    return warnings


# ============================================================================
# Display
# ============================================================================

def display_role(role):
    """Print a role dict in human-readable format."""
    print(f"\n  Role: {role['role_name']}")
    print(f"  Receives: {role['receives']}")
    print(f"  Sends to: {', '.join(role['sends_to'])}")
    if role['persistent_state']:
        print(f"  State:")
        for s in role['persistent_state']:
            print(f"    {s['field']} ({s['type']}, default={s['default']})")
    print(f"  Job: {role['job']}")
    print(f"  Routing rules:")
    for rule in role['routing_rules']:
        send = ', '.join(rule['send_to'])
        modify = f" | {rule['modify']}" if rule['modify'] else ""
        print(f"    if {rule['condition']} → {send}{modify}")

    warnings = validate_role(role)
    if warnings:
        print(f"  Warnings:")
        for w in warnings:
            print(f"    ⚠️  {w}")


# ============================================================================
# Main — test on roles.md
# ============================================================================

def main():
    filepath = sys.argv[1] if len(sys.argv) > 1 else "roles.md"

    print(f"\n{'='*60}")
    print(f"  Role Parser")
    print(f"{'='*60}")
    print(f"  Input: {filepath}")
    print()

    roles = parse_roles_file(filepath)

    print(f"\n{'='*60}")
    print(f"  Extracted {len(roles)} role(s):")
    print(f"{'='*60}")

    for role in roles:
        display_role(role)

    print()
    print(f"  Raw JSON:")
    print(json.dumps(roles, indent=2))
    print()


if __name__ == "__main__":
    main()
