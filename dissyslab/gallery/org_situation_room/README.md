# Situation Room

This example adds live social media streaming to a two-agent pattern.
BlueSky posts arrive seconds apart — the display updates in real time
as events unfold.

Alex filters for significant political and economic developments.
Morgan rewrites each keeper as a briefing note. The display shows the
eight most recent items, refreshing as new ones arrive. Items Alex
discards are archived to a separate file so you can inspect later
what got filtered out.

```
bluesky    ─┐                            ┌→ intelligence_display (live, 8 items)
al_jazeera ─┼→ Alex ─keep─→ Morgan ─briefing─┤
bbc_world  ─┘     │                      └→ briefings.jsonl  (archive)
                  └─discard─→ discards.jsonl (filtered-out items)
```

Unlike apps that check for news every few minutes, BlueSky posts arrive
the moment they are published — seconds apart during breaking events.

---

## The roles

**Alex's job — analyst:**

```
# Role: analyst

You are a news analyst who receives posts and articles and sends
items to either keep or discard.

Your job is to decide if each item is relevant to significant
political developments or economic events — specifically involving
topics such as Trump, Congress, Senate, elections, the Federal Reserve,
tariffs, inflation, markets, Ukraine, Iran, trade policy, or the
broader economy.

Exclude celebrity gossip, sports, entertainment, and personal
opinions with no broader political or economic significance.

If the item is relevant, send to keep.
Otherwise send to discard.
```

**Morgan's job — editor:**

```
# Role: editor

You are an editor who receives keepers from the analyst and sends
crisp briefings.

Your job is to rate each item you receive for its significance
giving the item a significance rating of CRITICAL, HIGH, MEDIUM, or LOW.
Rewrite each item as a crisp one-paragraph briefing note beginning
with the significance rating.
Note whether the item came from social media or news. Preserve the
source, url, timestamp, and author fields. Put your significance
rating in a field called "significance" and your summary in the
"text" field.

Send to briefing.
```

---

## The org chart

```
Sources: bluesky(max_posts=None, lifetime=None),
         al_jazeera(max_articles=10, poll_interval=600),
         bbc_world(max_articles=10, poll_interval=600)
Sinks: intelligence_display(max_items=8),
       jsonl_recorder_discard(path="discards.jsonl"),
       jsonl_recorder_briefing(path="briefings.jsonl")

Agents:
Alex is an analyst.
Morgan is an editor.

Connections:
bluesky's destination is Alex.
al_jazeera's destination is Alex.
bbc_world's destination is Alex.
Alex's keep is Morgan.
Alex's discard is jsonl_recorder_discard.
Morgan's briefing are intelligence_display and jsonl_recorder_briefing.
```

---

## Run it

```bash
dsl run gallery/org_situation_room/
```

The compiler shows you the routing and asks "Does this look right?"
Say yes and your Situation Room starts. The display refreshes in place
as new items arrive.

---

## Make it yours

**Track any topic.** Open `roles/analyst.md` and replace the political
and economic topics with whatever you follow — a sports team, a company,
a scientific field, a city:

```
Your job is to decide if each item is relevant to developments in
artificial intelligence — new models, research breakthroughs, policy
debates, or major product launches.
```

**Change the significance criteria.** Tell Morgan to rate items
differently — by urgency, by geographic relevance, by potential impact
on your field.

**Add more sources.** Wire in additional RSS feeds alongside BlueSky.
The more sources, the more complete your picture.

---

## What you built

Three sources run concurrently — BlueSky streaming continuously,
two RSS feeds polling every ten minutes. Alex and Morgan each run
in their own thread. Items flow through the network the moment they
arrive. The display updates in real time. Alex's discards stream
to one archive on disk; Morgan's briefings stream to another.

This is a persistent distributed system — five concurrent agents
coordinating through messages, running until you stop it.

The next example introduces a feedback loop between agents:
[News Editorial](../org_news_editorial/README.md).
