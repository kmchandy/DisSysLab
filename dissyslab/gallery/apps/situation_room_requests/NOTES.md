# situation_room_requests — sketch notes

Same feature pipeline as `apps/situation_room` (dedupe → four parallel
extractors → synchronizer). The only new agent is `Registry`, a custom
Python role, not an LLM role — its logic is exact and auditable, so it
should stay ordinary code.

`Registry` has one inbox, fed by two upstream senders: `Sync` (a
computed feature record for one item) and `webhook` (a stakeholder's
start/stop request). It tells them apart by shape, not by a separate
inport — same fan-in convention used elsewhere (e.g. CHECKER in
tutor_multi). It is not a coordinator; nothing here needs gate,
merge_synch, or select.

Private state: `subscriptions = {request_id: {stakeholder, watch_for,
channel}}`.

Behavior:
- `{"action": "start", "request_id", "stakeholder", "watch_for",
  "channel"}` → add an entry. `watch_for` is the one field the
  stakeholder cares about (e.g. `"severity"`); `channel` is
  `"console"` or `"email"`.
- `{"action": "stop", "request_id"}` → remove the entry. No effect on
  any other subscriber.
- an ordinary feature record (has `entities`/`severity`/`topic`/
  `location`) → always emit the full record on `archive`. Then, for
  each currently active subscription, project just that subscriber's
  `watch_for` field, format one short line, tag it with `request_id`
  and `stakeholder`, and emit on `to_console` or `to_email` per that
  subscription's `channel`.
- `{"action": "publish", "title"?, "text"?, ...}` → this office is a
  pub/sub system: a subscriber may publish, and the item is treated
  exactly like a torrent item, not routed back privately to its
  publisher. Registry normalizes it and forwards it on `to_torrent`
  back to `Sasha`, the same entry point the RSS feeds use.

## How to run this demo (two terminals)

`webhook` never exhausts, so `dsl run` never exits on its own — that
part is by design (see "Running the office" below). What's easy to
miss: subscribing/publishing has to happen from a **second terminal**
while the first one is still running the office. In one terminal:

    dsl run dissyslab/gallery/apps/situation_room_requests

In a second terminal, subscribe (nothing shows on console until you
do this):

    curl -X POST http://localhost:9100/webhook \
      -H 'Content-Type: application/json' \
      -d '{"action":"start","request_id":"treasury_1","stakeholder":"Treasury","watch_for":"severity","channel":"console"}'

Then either wait for the next poll cycle of the torrent (see
`poll_interval` below) or publish an item yourself to see it
immediately:

    curl -X POST http://localhost:9100/webhook \
      -H 'Content-Type: application/json' \
      -d '{"action":"publish","title":"Test alert","text":"...","stakeholder":"demo"}'

A subscription only sees records computed *after* it starts (no
backfill — see above), so if the torrent already drained before you
subscribed, nothing appears until either the next poll or a manual
publish.

Two things this sketch deliberately assumes, per Mani (2026-07-18):
1. **Push, not pull.** Registry notifies active subscribers itself,
   on every new record. Nothing polls it.
2. **No backfill.** A new request only sees records computed after it
   starts, never history from before. Registry's `subscriptions`
   table is the only memory it needs to keep — there's no query-by-
   item-id lookup path in this version, even though features are, in
   the general sense, "stored in memory" once per item.

The compute-once property falls out for free: Sasha/Eve/Sam/Tom/Greta/
Sync run exactly once per item regardless of how many (or how few)
requests are active — Registry sits downstream of all of that, and
only its own fan-out step scales with the number of subscribers, and
that step is cheap (a field lookup and a string format, not a
recomputation).

`roles/subscription_registry.py` is now written and `dsl build`
compiles this office cleanly (verified in a sandbox with no API key —
`dsl build` never calls the LLM backends). Running it for real still
needs Anthropic/OpenRouter credentials for the four extractors plus
`GMAIL_USER`/`GMAIL_APP_PASSWORD` for the email channel.

The two `channel` values are still hardcoded to one demo subscriber
each (console, email) rather than discovered dynamically — good
enough to demonstrate the capability, not a full-fledged app.

RSS sources now use `poll_interval=300` (added 2026-07-18) so the
torrent stays live instead of draining once at startup and going
silent for the rest of the run.

## Plan: replace situation_room

Once this has been run for real (needs Anthropic/OpenRouter +
Gmail credentials — not yet done) and, ideally, an English-
description-first version exists too, the intent is for this office
to **replace** `apps/situation_room` in the gallery, not sit alongside
it. Not done yet — noted here so it isn't lost.
