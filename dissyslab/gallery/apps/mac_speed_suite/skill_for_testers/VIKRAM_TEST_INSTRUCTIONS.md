# Testing the Backtester — a walk-through for Vikram

Hi Vikram — thanks for helping us test this. You don't need to be a programmer,
and you won't be asked to write any code. The whole point of this test is to see
whether someone who *thinks about markets* — not about Python — can describe a
trading idea in plain English and get a trustworthy answer back.

You'll be talking to **Claude Cowork**, which sits on top of a small research tool
we built called the **backtester**. A backtester takes a trading rule (for
example, "hold a stock while it's trending up, step aside when it isn't") and
replays it over years of real historical prices to see how it *would* have done.

Please read this once end to end before Wednesday. It should take about ten
minutes. Then on the day, keep it open beside you and follow along.

---

## What we're really asking you to judge

We are **not** asking "is this a good trading strategy?" We're asking:

1. Could you describe a strategy in your own words and have it understood?
2. When the tool told you what it *assumed* you meant, was it right — and if not,
   could you correct it just by talking?
3. When you read the results, did you **trust** them? Did anything look like a
   number that was too good to be true, or an answer to a question you didn't ask?
4. When you were confused, could you get unstuck by asking Cowork, without coming
   to us?

Anywhere the answer is "no," that's the most valuable thing you can tell us.
Please don't smooth it over — a confused moment from you is a bug in our design.

---

## Part 1 — One-time setup (about 15 minutes)

You only do this once. If you get stuck on any step, that itself is a finding —
note where, and either ask Cowork ("I'm stuck on step 3, can you help?") or send
us a message and move on.

**1. Get the code.** We'll send you a link to the project (a GitHub repository)
and a one-line instruction to download it. If you already have it from us, skip
ahead.

**2. Open the project in Cowork and connect the folder.** In the Claude desktop
app, start a Cowork task and connect the project folder so Claude can see the
files. (There's a folder-connect button in the app; if you can't find it, ask
Cowork "how do I connect my project folder?")

**3. Install the skill.** In the project there's a file ending in `.skill`
called `backtest-strategy-builder.skill`, inside the `skill_for_testers` folder.
When you open it, the app should offer a **"Save skill"** button — click it. This
teaches Cowork the specific vocabulary of this tool. If you don't see the button,
tell us — that's a finding too.

**4. Get the market data.** The tool needs real historical stock prices, and for
legal reasons we don't ship those with the code — you download them yourself, the
exact same way a real user would. You don't need to know how; just say to Cowork:

> "Please download the stock data this app needs."

It will fetch about ten years of daily prices for a basket of five stocks (AMD,
Netflix, Nvidia, Palantir, Tesla) and save them where the tool expects. If it
asks you to install one small thing first (a package called `yfinance`), say yes.

That's setup. You now have a working research tool.

---

## Part 2 — Your first run (the "does it work at all" pass)

Start simple, before you get creative. In Cowork, say:

> "Run the backtester as it's currently set up and show me the report."

Give it a minute or two. When it finishes, it produces a file called
**`report.html`** — open it. Have a look around. You should see, roughly:

- a short **summary** at the top,
- a **Walk-Forward (out-of-sample) validation** section — treat this as the
  headline (more on why below),
- a **Monte Carlo robustness** section,
- a **full-window comparison** of the different strategy variants,
- a **strategy correlation** table,
- and a **per-stock detail** section.

You don't need to understand every number yet. Right now just answer one thing
for us: **did a real, readable report appear?** If yes, you've confirmed the tool
runs on your machine. If it errored out, copy the error text, paste it to Cowork,
and ask "what does this mean and can you fix it?" — then tell us what happened.

---

## Part 3 — Describe your own strategy (the heart of the test)

This is what we most want to watch. **Don't** look for the "right" way to phrase
things. Say what you'd say to a colleague. Some examples to get you going — pick
one, or invent your own:

> "I want to buy a stock when its price crosses above its 100-day average and
> sell when it drops below. Test that."

> "Compare a fast trend-follower against a slow one — which one keeps more of its
> gains after trading costs?"

> "Only hold the strongest stocks in the basket — the ones outperforming the
> others — and rotate out of the laggards."

> "What if I only trade when the whole market is going up?"

After you describe a strategy, **watch for a moment where Cowork tells you what it
assumed.** It should come back with something like *"Here's what I assumed you
meant…"* — a list of the specific choices it filled in on your behalf (which
average, how fast, what counts as "strongest," and so on).

**This is the most important moment of the whole test.** Read that list. Then:

- If it matches what you had in your head → say "yes, that's right, go ahead."
- If it got something wrong → **just correct it in words.** For example: "No, I
  meant the 50-day average, not the 200-day," or "By strongest I meant highest
  return over the last three months." You should not have to touch any code or
  settings. Watch whether your correction actually takes.

Tell us honestly: *did the tool volunteer its assumptions, or did you have to
drag them out of it?* And *when you corrected it, did the next run reflect your
correction?* If it quietly did something different from what you asked and didn't
tell you, that is exactly the kind of thing we need to catch — please flag it.

Then have it run, and open the new `report.html`.

---

## Part 4 — Reading the report, and pushing on it

Here's a plain-English guide to the parts that matter most. You don't have to
memorize this — you can ask Cowork any of these questions live and it will explain
using *your* results.

**Walk-forward (out-of-sample) — the honest score.** It's easy to invent a rule
that looks brilliant on the exact history you tuned it on. Walk-forward guards
against that: the tool decides the strategy on an early stretch of history, then
scores it on *later* history it "hadn't seen." Think of it as grading the strategy
on a test it couldn't study for. If a strategy looks great in the full-window
comparison but mediocre in walk-forward, the full-window number was flattering it.
**Trust the walk-forward ranking over the full-window one.** Good question to ask
Cowork:

> "Which strategy holds up best out-of-sample, and how different is that from the
> in-sample ranking?"

**Monte Carlo robustness — how much was luck.** The tool reshuffles the history
many times and re-runs, to see how much the outcome bounces around. If a strategy
only wins in one lucky ordering of events, this exposes it. Ask:

> "How fragile is this result? What's the chance this strategy lost money?"

**Transaction costs — the tax on activity.** Every trade costs a little. A
strategy that trades constantly can look great on paper and lose to a lazier one
once costs are subtracted. Ask:

> "How much return is this strategy giving up to trading costs?"

**Correlation — are these really different bets?** Two strategies that always move
together aren't two ideas, they're one idea twice. Ask:

> "Are these strategies actually different, or are they basically the same bet?"

Please pick **at least two** of these questions and ask them live. We want to know
whether Cowork's spoken explanation matched what you saw in the report, and
whether it helped you trust — or rightly *distrust* — a number.

---

## Part 5 — Try to break our trust (optional but gold)

If you're enjoying it, push harder. Some things that would teach us a lot:

- Deliberately describe something vague ("buy low, sell high") and see whether
  Cowork asks you what you mean or just guesses.
- Ask it a pointed question: "Is this result too good to be true? What would make
  you doubt it?" — and see whether it's honest with you.
- Change your mind halfway: run something, then say "actually, add a rule that we
  never hold more than three stocks at once," and see if it adapts.
- Ask it something it *can't* know: "will this make money next year?" — a
  trustworthy tool should decline to promise that.

---

## What to send back to us

Whenever you're done — even if you stopped early — please tell us, in whatever
form is easiest (a note, a voice memo, screenshots):

1. **Did it work?** Where did it stall, if anywhere?
2. **Did you trust the results?** Was there a number you didn't believe, or an
   answer that didn't match your question?
3. **Where were you confused?** The exact moment, even if small.
4. **When something went wrong, could you fix it yourself** by talking to Cowork,
   or did you need us?
5. Anything that delighted or annoyed you.

If it's easy, the single most useful thing you can share is **the transcript of
your conversation with Cowork** — that shows us exactly what you asked and what it
did. Cowork can help you export it; just ask.

Thank you, Vikram. Every confusing moment you report makes this usable for the
next person who isn't a programmer either.
