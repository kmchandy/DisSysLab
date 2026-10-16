"""
---
emits: each round of the debate, and its outcome, on the screen
in: next, problem_id, problem, history
---
"""


class PanelDisplay:
    def __call__(self, msg):
        last = msg["history"][-1]
        print(f"\n[{msg['problem_id']}] round {last['round']}: {msg['problem'][:70]}")
        for name in ("qwen", "gpt", "claude"):
            ans = last[name]
            print(f"  {name:6} {ans['answer']!s:20} ({ans['confidence']})  {ans['reasoning']}")
        if msg["next"] == "finish":
            print(f"  => {msg['final_answer']} ({msg['agreement']}, "
                  f"{msg['rounds_used']} round(s))")
        else:
            print(f"  => another round. {last['note']}")
