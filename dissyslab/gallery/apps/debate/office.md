# Office: debate

Sources: starter
Sinks: jsonl_recorder(path="debate_answers.jsonl"),
       jsonl_recorder_briefing(path="debate_transcript.jsonl"),
       debate_display

Agents:
Sasha is a gate.
Qwen is a qwen.
Qwen's AI is openrouter.
GPT is a gpt.
GPT's AI is openai.
Claude is a claude.
Claude's AI is anthropic.
Sync is a synchronizer(inports=["from_qwen", "from_gpt", "from_claude"]).
Riley is a moderator.

Connections:
starter's destination is Sasha.

Sasha's out is Qwen, GPT, Claude.

Qwen's out is Sync's from_qwen.
GPT's out is Sync's from_gpt.
Claude's out is Sync's from_claude.

Sync's out is Riley, jsonl_recorder_briefing, debate_display.

Riley's continue is Qwen, GPT, Claude, debate_display.
Riley's finish is jsonl_recorder, Sasha, debate_display.
