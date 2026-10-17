# Receive webhooks

**Goal.** An office that listens for HTTP POSTs from another service (a
GitHub push, a form, Zapier, another office) and decides what to do with
each one.

## 1. A listener

Make a folder `my_listener` with `office.md`:

```
sources:
    hook: webhook

sinks:
    console_printer
    noise: jsonl_recorder(path="noise.jsonl")

agents:
    Kind: kind
    Rex: router(on="kind")

connections:
    hook -> Kind -> Rex
    Rex.event -> console_printer
    Rex.noise -> noise
```

and `roles/kind.py`, a Python role that sets empty posts and pings aside:

```python
"""
---
in: text
out: kind (event | noise)
---
"""


class Kind:
    def __call__(self, item):
        return {"kind": "noise" if item.get("text", "") in ("", "ping") else "event"}
```

```bash
dsl check .
dsl run .
```

```
[WebhookSource] Listening on http://localhost:8000/webhook
[WebhookSource] Bound to localhost only. Pass host='0.0.0.0' to accept posts from other machines.
```

The office keeps listening until you press Ctrl-C.

## 2. Post to it

In a second terminal:

```bash
curl -X POST http://localhost:8000/webhook \
  -H 'Content-Type: application/json' \
  -d '{"title":"test","text":"hello from curl"}'
curl -X POST http://localhost:8000/webhook -d 'ping'
```

The first terminal shows the first post; the ping goes to `noise.jsonl`:

```
[WebhookSource] Received POST #1 (15 chars)
[1] {'source': 'webhook', 'title': 'test', 'text': 'hello from curl', 'url': '', 'timestamp': '...', 'kind': 'event'}
[WebhookSource] Received POST #2 (4 chars)
```

Press Ctrl-C. The office stops and prints its run summary:

```
Stopped (Ctrl-C).

Run summary (messages):
  my_listener::Kind              sent      2   received      2
  ...
```

## How a post becomes a message

A JSON body's fields come through as the message's fields; `title`,
`text`, `url` and `timestamp` are filled in if the body does not have
them. A body that is not JSON becomes the `text`. A GitHub push hook,
for example, arrives with its own `ref`, `repository` and `commits`
fields, which a role can read.

## Let a model decide

Replace `roles/kind.py` with an English role, `roles/kind.md`, that
decides from the content:

```
---
in: title, text
out: kind (event | noise)
---
You receive one payload that a web service posted to us, as a JSON object.

It is noise if it is empty, a health check ("ping", "test"), or an
automated notice nobody needs to read. Otherwise it is an event.

Return only a JSON object with one field, "kind", whose value is "event"
or "noise".
```

The office does not change: the role is still called `kind`. (Delete
`kind.py`: two files with one name is an error `dsl check` reports.)

## Reaching it from the internet

`localhost:8000` is reachable only from your own computer. To receive
posts from a real service, give the listener a public address with a
tunnel such as `ngrok http 8000` or `cloudflared tunnel --url
http://localhost:8000`, and paste the URL it prints, with `/webhook` at
the end, into the service's webhook settings.

**Anyone who can reach the port can post to your office**: there is no
authentication. Keep the default `host="127.0.0.1"` unless the listener
is behind something that checks who is posting.

Arguments (`port`, `path`, `host`): `dsl grammar sources`.
