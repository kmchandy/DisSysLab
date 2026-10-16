# debate: three models answer each question; a moderator judges agreement;
# a referee sends the question back for another round or finishes it.

sources:
    problems: file_source(path="problems.jsonl")

sinks:
    answers: jsonl_recorder(path="debate_answers.jsonl")
    transcript: jsonl_recorder(path="debate_transcript.jsonl")
    panel_display

agents:
    Gate: gate
    Qwen: qwen(ai="openrouter")
    GPT: gpt(ai="openai")
    Claude: claude(ai="anthropic")
    Sync: synchronizer(on="problem_id")
    Riley: moderator
    Ref: referee(max_rounds=2)
    Rex: router(on="next")

connections:
    problems -> Gate -> Qwen, GPT, Claude
    Qwen -> Sync.qwen
    GPT -> Sync.gpt
    Claude -> Sync.claude
    Sync -> Riley -> Ref -> Rex, panel_display
    Sync -> transcript
    Rex.continue -> Qwen, GPT, Claude
    Rex.finish -> answers, Gate.done
