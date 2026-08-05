# Trying out the backtest-strategy-builder skill

Thanks for taking a look at this. Here's what it is and how to try it --
kept short on purpose, since the point is to see what happens when you
just describe a strategy idea yourself, not to walk you through it.

## What this is

A Cowork skill that lets you add a new trading strategy to an existing
backtesting system (`mac_speed_suite`, part of the open-source DisSysLab
framework) just by describing the strategy in plain English. The system
already runs three strategies (a moving-average crossover, Donchian
channels, and the Turtle system) on real historical stock data; the skill
is meant to let a fourth, fifth, etc. get added the same way, without
anyone needing to touch the underlying Python framework.

## Setup (two things, both one-time)

1. **Install the skill.** Open the attached `backtest-strategy-builder.skill`
   file -- it should show a "Save skill" button.
2. **Connect the DisSysLab repo.** Clone `https://github.com/kmchandy/DisSysLab`
   (it's public) and connect that folder to Cowork.

## What to do

Just tell Claude, in your own words, what trading strategy you'd like to
try -- anything from a well-known rule (momentum, mean-reversion, a
moving-average variant, whatever you're curious about) to something
you've been meaning to test. No need to mention the skill by name or say
anything about "signals" or "contracts" -- just describe the trading
idea the way you'd describe it to a colleague.

## What would help most

Whatever you actually notice is useful feedback -- there's no wrong
reaction. A few things that would be especially helpful to know:

- Did it work? Did you trust the result?
- Where (if anywhere) did you get confused, or did something feel off?
- Would you have known how to fix it yourself if something went wrong?

If you're willing, sharing the conversation transcript and whatever files
it produced (or just `git diff` / `git status` output from the repo
afterward) would help a lot -- it's the clearest record of what actually
happened.

## One more thing

This is part of an ongoing research project on the DisSysLab/OfficeSpeak
framework, and your feedback may be referenced in a paper about it. If
you're fine being named, say so; otherwise your feedback will be kept
anonymous. Either way, thank you for trying this.
