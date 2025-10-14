Customization Cheat-Sheet (for students)

Use a different feed

Change url= to another RSS feed, e.g.:

NASA Tech: "https://www.nasa.gov/technology/feed/"

Example placeholder: "https://example.com/rss.xml"

Keep it HTTPS when possible.

Don’t fetch full pages (faster, lighter)

Set fetch_page=False

Adjust output_keys to drop "page_text", e.g. ["title", "link"]

Update the yield to match those keys.

Emit in batches instead of per item

Set emit_mode="batch" and pick batch_size/batch_seconds.

Your source function will receive lists of items; iterate before yielding.

Run longer

Increase life_time (e.g., life_time=60) or remove it to let it run indefinitely.

See the article link in the console

Include "link" in output_keys and in the yielded dict.

Throttle or speed up

Remove or change the time.sleep(0.05) in from_rss().

Common gotchas

Some feeds rate-limit; if items stop appearing, increase poll_seconds in the connector or run less frequently.

Not all feeds expose the same fields; use .get() and check keys before assuming.