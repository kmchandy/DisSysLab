# Trying out adaptive_tutor + the tutor-subject-builder skill

Thanks for taking a look at this. Here's what it is and how to try it --
kept short on purpose, since the point is to see what happens when you
just describe a topic yourself, not to walk you through it.

## What this is

`adaptive_tutor` is a practice-and-check tutoring app (part of the
open-source DisSysLab framework) -- it asks a question, checks the
answer, gives a bit of encouraging feedback, and keeps a simple score.
It already runs three topics: fractions, multiplication facts, and
telling time. The `tutor-subject-builder` skill lets you add a fourth,
fifth, etc. just by describing the topic in plain English, without
anyone needing to touch the underlying Python.

## Setup (three things, all one-time)

1. **Install the skill.** Open the attached `tutor-subject-builder.skill`
   file -- it should show a "Save skill" button.
2. **Connect the DisSysLab repo.** Clone
   `https://github.com/kmchandy/DisSysLab` (it's public) and connect that
   folder to Cowork.
3. **Add an Anthropic API key.** Unlike some of our other demos, this one
   needs a real LLM call to grade free-text answers (so it can accept
   "one half" and "0.5" as the same answer, for instance). In the
   DisSysLab folder:
   ```
   echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env
   ```

## What to do

If you want to see it running as-is first, that's a fine place to start
-- `dsl build` then `dsl run` from
`dissyslab/gallery/apps/adaptive_tutor/` will run all three existing
topics.

When you're ready to add a topic for your daughter, just tell Claude, in
your own words, what you'd like her to practice -- spelling words, state
capitals, a math skill, whatever she's working on. No need to mention
the skill by name or say anything about "contracts" or "subjects" --
just describe it the way you'd describe it to a teacher.

## What would help most

Whatever you actually notice is useful feedback -- there's no wrong
reaction. A few things that would be especially helpful to know:

- Did it work? Did you trust the result?
- Where (if anywhere) did you get confused, or did something feel off?
- Would you have known how to fix it yourself if something went wrong?
- Separately from whether it worked mechanically: does the tutoring
  itself feel right -- is this something your daughter would actually
  want to use?

If you're willing, sharing the conversation transcript and whatever
files it produced (or just `git diff` / `git status` output from the
repo afterward) would help a lot -- it's the clearest record of what
actually happened.

## One more thing

This is part of an ongoing research project on the DisSysLab/OfficeSpeak
framework, and your feedback may be referenced in a paper about it. If
you're fine being named, say so; otherwise your feedback will be kept
anonymous. Either way, thank you for trying this.
