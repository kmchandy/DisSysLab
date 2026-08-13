# Tester feedback log — mac_speed_suite

A running, verbatim record of feedback from domain-expert testers, newest first.
Each entry is logged as received; our responses and the resulting roadmap items
live in `PHASE1_DESIGN.md` and follow-on design notes, not here.

---

## 2026-08-12 — the trader

> On the table, it's not wrong, it's measuring the wrong unit. Every number in it
> is a property of a daily return series. What I need in order to decide whether
> something is worth trading is properties of trades. How many were there? How
> long were they held? What did the average winner make and the average loser
> lose? What was the worst single one? Twenty trades and two hundred trades can
> produce an identical-looking Sharpe and they mean completely different things,
> and right now I can't tell them apart from the output. That's the same gap that
> let a strategy which never opened a position at all still get a row in the
> table.
>
> So: keep the table, but put a trade count, an average hold, a win rate and an
> average win/loss next to it. There are other numbers too, the RR of the trade,
> the Expected Return and so on. If a number is built on twelve trades I want to
> see the twelve.
>
> The one thing I'd add before anything else is out-of-sample by default. Not as
> a flag, as the normal behavior Pick the winner on the first half of the window,
> then show me how that pick actually did on the second half, right there next to
> the ranking. When I did that by hand your current winner went from 2nd to 10th
> and a variant that never gets mentioned was 1st in both halves. That single
> change would do more than any number of extra metrics, because it's the
> difference between a tool that helps me and a tool that flatters me. Honestly
> it's the thing I'd want most.
>
> Third, sizing. In practice I don't hold plus or minus one unit of notional. I
> risk a fixed amount per trade and the distance to my stop determines how big the
> position is. If you size that way, every result comes out in R multiples: "made
> 14R over 60 trades, average winner 2.1R, average loser -0.8R." Those numbers are
> directly comparable across stocks with different prices and different
> volatilities, which annualized return on constant notional isn't. It's also just
> the language traders actually think in, nobody at my desk says "annualized
> Sharpe," everyone says "that was a 3R trade."
>
> Fourth, costs as a dial. Doesn't have to be sophisticated, one
> commission-plus-slippage number in basis points that I can set, with turnover
> shown next to the result. A good chunk of what looks like an edge on daily bars
> is a fill assumption, and being able to watch the number move as I turn costs up
> is more convincing than any single figure. For now I'd actually ignore this
> comment because it's getting to granular, but just thought I'd mention.
>
> On the initial-portfolio question: I'd want that, but I think it's a different
> app rather than a feature of this one. "Is this strategy any good" and "given
> what I'm already holding, what should I do tomorrow" are separate questions with
> separate outputs. The first wants history, statistics and out-of-sample
> discipline. The second wants today's state, what I hold, what it's doing, what's
> changed since yesterday, what's near a level and almost no statistics at all.
> Trying to serve both from one table is probably what makes both worse.
