# Your first hour with a talk-to-it app

*A guided tour of the paper trader — an app you run by talking to it.*

**Draft v0.1 — for discussion.** This tutorial is the concrete, user-facing
instance of a more general idea (a "talk-to-it" app: a tested core you drive in
plain English). A short note for builders is at the end.

---

## Read this first — this is a different kind of app

You've used a hundred apps that work the same way: there's a screen full of
buttons and menus, and your job is to find the right button for the thing you
want. This app doesn't have buttons. **You tell it what you want, in ordinary
English, and it configures and runs itself.**

That sounds small. It isn't. It changes what *you* do. Instead of hunting for a
feature someone else decided to build, you *describe* the feature you want — and
often you get it, because the app was built to be shaped by description rather
than by clicking.

Three things to know before you start, because they give you permission to play:

- **You can't break it.** Every trade here is *simulated* — paper only, never a
  real order, never real money. Nothing you type can lose a cent.
- **Everything is reversible.** The app keeps a full history. If you don't like a
  change, you say so and it goes back.
- **When you're not sure what to say, ask.** "What can I change here?" is always
  a good move. The app will tell you.

So experiment. The whole point is that you can.

> **What you need to start:** the paper-trader app installed (see the README),
> and Cowork open in its folder. When this tutorial says *you type*, it means you
> type it to Cowork in plain English — not into a command line.

---

## Step 1 — It already works (30 seconds)

Type:

> **Run my paper trader.**

That's the whole instruction. No setup, no form to fill in. In a moment you get a
*brief* — a short page that says what the app holds, what it did today, and how
much the (pretend) account is worth:

```
Paper trade — 2020-01-12   equity $110,818  (cum P&L +10,818)
Holdings: AMD 40 @ 138.20 ($5,528); NVDA 60 @ 59.10 ($3,546); ...
Today: BUY 40 AMD (entry); SELL 25 TSLA (trend flipped)
```

You didn't tell it which stocks, how much money, or what strategy. It filled in
sensible defaults (a basket of well-known stocks, $100,000 of pretend cash, a
simple moving-average strategy) and told you what it assumed. That's on purpose:
the first thing an app should do is *work*, so you can trust it before you tune
it.

**What just happened:** you ran a real strategy over real historical prices and
got a real result — with a single sentence.

---

## Step 2 — Change it by saying so (this is the important one)

Now the part a buttons-and-menus app can't do gracefully. Type:

> **Use a tighter stop — get me out if a position drops 6% instead of 10%.**

Watch what comes back *before* it reruns:

> Okay — I'll set the stop-loss to 6% (it was 10%). Everything else stays the
> same: same stocks, same $100,000, same strategy. Re-running now.

Notice two things. First, you changed a setting **by describing it**, not by
finding a "Stop-loss" field in a settings screen. Second, the app **repeated back
what it understood** before doing it. That echo is your safety net — you can see
it got your intent right, and if it didn't, you just say "no, I meant…".

Try another, and be a little vague on purpose:

> **Only trade the chip makers — AMD, NVDA, and a couple of others you'd put in
> that group.**

It will propose a list ("AMD, NVDA, and I'd add TSM and AVGO — okay?") and wait
for your yes. **You are now configuring the app in a conversation** — the way you'd
brief a colleague, not the way you'd operate a machine.

> **The feeling to notice:** the app reshaped itself from a sentence. If you feel
> that once, you understand the whole idea.

---

## Step 3 — Ask it *why*, not just *what*

A buttons app can show you *what* happened. It usually can't tell you *why*,
because "why" isn't a button. This app can, because it keeps an honest record of
every decision. Type:

> **Why did we sell TSLA today?**

You'll get a plain answer traced from that record: *"The fast moving average
crossed below the slow one on Jan 10, which flips the signal to 'exit'. We
decided at that close and sold at the next open, at $86.04."*

Try:

> **What do I hold right now, and why each one?**

or

> **Show me the days we lost the most money and what the app did on those days.**

This is a genuinely new power. You're not operating the app anymore — you're
*interrogating* it. It can answer because the tested core writes down every
decision as it goes.

---

## Step 4 — Invent something new (you become a co-author)

Here's where it goes past anything a shrink-wrapped app offers. You can ask the
app to build a **new strategy that didn't exist before**. Type:

> **Invent a momentum strategy: buy a stock when it's been rising faster than
> usual, sell when it stalls.**

Cowork writes the strategy for you. But — and this is the important habit —
before it trades a cent of (pretend) money on something it just made up, it
**offers to test it**:

> I wrote a momentum strategy. Before we trade on it, I'd like to run a quick
> self-check — especially the *look-ahead* test, which makes sure the strategy
> isn't secretly peeking at tomorrow's prices (the classic way a strategy looks
> great on paper and fails for real). Want me to run it?

Say yes. You'll see something like:

```
Strategy self-check: PASSED
  3/3 checks passed
  [ok]  contract: one signal per day, all valid numbers
  [ok]  determinism: same answer every time
  [ok]  no_lookahead: it never used tomorrow's price to decide today
```

If the invented strategy *had* been cheating, you'd see instead:

```
Strategy self-check: FAILED
  [X]  no_lookahead: a decision on day 89 changed once later days were added —
                     the strategy is peeking. DO NOT trade on this until fixed.
```

and Cowork would offer to fix it rather than trade on it.

**Why this matters to you:** the app didn't just do what you asked — it did it
*and proved it wasn't fooling you*. You are never forced to run the check (if you
just want to explore an idea, go ahead). But the app makes the careful path the
easy path, and tells you plainly when something it built isn't safe to trust yet.
That's the difference between "the computer wrote me a strategy" and "the computer
wrote me a strategy and showed me it isn't cheating."

---

## Step 5 — Now go off-script (the real point)

The four steps above were a guided path so the app would feel familiar. But there
is no fixed path — that was the training wheels. Here's the menu of what you can
actually do, so your imagination has somewhere to go. **When in doubt, just ask
the app "can you…?" — the answer is usually yes, or "not that, but here's what I
can do."**

**Things you can change (just say them):**
- the stocks it trades, the starting cash, the stocks you already own
- the stop-loss, how it sizes positions (evenly, by risk, a fixed slice)
- how cautious it is about trading on small signals (the "no-trade band")

**Things you can ask:**
- "What do I hold and why?" · "Why did we do X on day Y?"
- "How did this month go?" · "Which trades were the best and worst?"
- "Make the ledger into a nice-looking table." (it can reshape its own output)

**Things you can invent:**
- a brand-new strategy from a plain-English description
- a second, competing strategy in its own separate book, run side by side
- a bespoke test ("this strategy should end up holding cash in a crash — check
  that") on top of the automatic ones

**Things it will refuse — and why (that's the app being honest):**
- placing a real trade with real money (this is paper only, always)
- trading on a strategy that failed its look-ahead check (it'll offer to fix it)

---

## What just happened in this hour

You configured an app, asked it to explain itself, and *extended* it with a new
capability — all in plain English, and all on top of a core you never had to
inspect or trust blindly. The parts that must be exactly right (the record of
trades, the timing, the "no cheating" check) are fixed and tested. The parts that
are *your* preference (which stocks, how cautious, which strategy) are yours to
shape by talking.

That's the trade a talk-to-it app offers: **the boring, correctness-critical
machinery is handled for you and never changes; the creative, personal part is
open to you and changes with a sentence.**

---

## For builders (skip if you're just here to trade)

This tutorial is deliberately shaped, and the shape generalizes to any talk-to-it
app — not just trading:

- **Name the shift first.** A user trained on buttons will try to use a
  conversation like a button panel unless you tell them, out loud, that it's
  different — and give them permission to experiment (here: "it's paper, it's
  reversible, ask when unsure").
- **The arc is trust → reshape → interrogate → invent.** It works out of the box
  (Step 1), you change it by describing (Step 2), you ask it *why* (Step 3), you
  extend it yourself (Step 4). The order isn't optional: you can't teach "reshape"
  to someone who doesn't yet believe it works.
- **Affordance disclosure is a feature, not a footnote.** A conversation is a
  blank page; the flexibility is invisible until you *show the user what they can
  say* (Step 5). Buttons advertise themselves; a prompt does not — so you must
  advertise it deliberately.
- **Three tiers of power, rising responsibility.** Tier 1 the tested core (we
  test it), Tier 2 named settings (safe to change), Tier 3 generated features
  (powerful, so the app *helps you test them* — advise, never force).

The claim underneath it all: a tested library plus a skill plus English is a good
way to surface an app — especially where correctness matters — because the app
can do the one thing an unaided assistant can't: *prove its own work.*
