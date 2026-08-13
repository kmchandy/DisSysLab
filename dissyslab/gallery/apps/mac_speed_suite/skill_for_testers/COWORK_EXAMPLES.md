# Talking to the backtester — example conversations

You drive the whole backtester by talking to Claude Cowork in plain English.
You never edit code or config by hand. You do two kinds of things: **describe a
strategy** you want tested, and **set the parameters** of a run (which stocks,
how far back, how much validation, what stop, what cost). Everything else —
implementing the rule, wiring it in, validating it out-of-sample, stress-testing
it, and writing the report — is done for you.

This page is a menu of things you can say, and what happens when you do. Copy
one, or say it in your own words — the phrasing doesn't matter. Two habits worth
knowing before you start:

- **It tells you what it assumed.** When your request leaves a choice open (which
  moving average? how fast? what counts as "strong"?), Claude comes back with a
  short "here's what I assumed you meant" list *before* running. Read it. If it's
  wrong, just say so — see the correction examples below.
- **Every run leaves a receipt.** The top of `report.html` has a "Run settings"
  panel showing exactly which basket, window, validation, stop, and cost produced
  that report — so you can always tell what you were looking at.

---

## 1. Running and tuning a run

> "Run the backtester and show me the report."

Runs the whole thing as currently set and opens `report.html`. One run does both
validations — walk-forward (out-of-sample) and Monte Carlo — plus the trade
statistics and R multiples.

> "Use these stocks instead: AAPL, MSFT, GOOG, AMZN, META, NVDA."

Changes the basket, re-downloads the data to match, and re-runs. The new basket
shows up in the Run settings panel.

> "Test the last five years instead of ten."

Shortens the history window. Claude will tell you it's cutting the window and to
what dates.

> "Run 500 Monte Carlo samples for a tighter robustness estimate."

Raises the resample count (default is 100). More samples = a smoother
distribution, a slower run.

> "Just do the fast walk-forward this time, skip Monte Carlo."

Turns off the Monte Carlo half for a quicker pass.

> "Set transaction costs to 10 basis points and run it again."

Re-runs at a higher cost assumption. Watch how the rankings and net returns move
as costs rise — a lot of apparent edge on daily bars is a fill assumption.

> "Use a tighter stop — 5% instead of 10% — for the R numbers."

Changes the stop that R multiples are measured against. R for a trade is its
return divided by the stop distance, so a tighter stop makes every trade a larger
number of R. The stop is an assumption, not advice — it's yours to set.

---

## 2. Describing a strategy

Say what you'd say to a colleague. A few starting points:

> "Buy a stock when it closes above its 100-day average, sell when it closes
> below. Test that."

> "Try a mean-reversion rule: buy when the 14-day RSI drops under 30, exit when
> it climbs back over 50."

> "Add a breakout system: go long on a new 55-day high, flat on a new 20-day low."

> "Only hold the strongest names in the basket — the ones outperforming the rest
> — and rotate out of the laggards."

> "Test a trend rule, but only take trades when the whole market is rising."

After you describe one, watch for the **"here's what I assumed you meant"** list —
which average, how many days, whether it can go short, how many bars of warm-up.
Then approve or correct:

> "Yes, that's right — go ahead."

> "No — I meant the 50-day average, not the 200-day."

> "By 'strongest' I meant the highest return over the last three months, not the
> last year."

> "Let it go short too, not just long-or-flat."

Your correction takes effect on the next run — you should see it reflected, and
you shouldn't have to touch any settings yourself.

---

## 3. Reading and interrogating the results

You can ask about anything in the report in plain English, and Claude answers
using *your* run's numbers.

**Trades (not just the return curve):**

> "How many trades did the winning strategy actually make, and how long did it
> hold each one?"

> "What did the average winner make versus the average loser? What was the worst
> single trade?"

> "Show me the twelve trades behind that number."   (opens the per-trade list)

> "Which of these strategies barely traded at all, and which churned constantly?"

**In R:**

> "Put the results in R multiples — what's the expectancy per trade?"

> "Which strategy has the best reward-to-risk, and how does that change if I use a
> wider stop?"

**Out-of-sample (the honest score):**

> "Which strategy holds up best out-of-sample, and how different is that from the
> in-sample ranking?"

> "If I'd picked the in-sample winner, where did it actually land out-of-sample?"

> "Is there a strategy that's strong in both halves of the history?"

**Robustness and costs:**

> "How fragile is this result? What's the chance the best strategy lost money?"

> "How much return is the top strategy giving up to trading costs?"

> "Are these strategies actually different bets, or basically the same one twice?"

**Trust:**

> "Is this result too good to be true? What would make you doubt it?"

> "Will this make money next year?"   (a good answer declines to promise)

---

## 4. Changing your mind mid-stream

You don't have to get it right the first time — this is a conversation.

> "Actually, add a rule that we never hold more than three names at once, and
> re-run."

> "Go back to the version before the last change."

> "Compare this run's out-of-sample ranking to the previous one — did the winner
> change?"

> "Write me a one-paragraph summary I could send a non-technical partner, and be
> honest about what we're *not* claiming."

---

Whatever you try, if something is confusing or an answer doesn't match the
question you asked, that's the most useful thing you can tell us — it's a bug in
the tool's design, not in you.
