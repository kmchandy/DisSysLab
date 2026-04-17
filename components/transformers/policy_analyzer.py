# components/transformers/policy_analyzer.py

"""
PolicyAnalyzer: Analyzes the agent's policy from a CartPole training checkpoint.

One of three parallel analyzers in Module 06. Examines the Q-table summary
to determine what the agent has learned about action preferences, and tracks
the exploration rate (epsilon) to show the explore → exploit transition.

Usage:
    from dissyslab.components.transformers.policy_analyzer import PolicyAnalyzer
    from dissyslab.blocks import Transform

    analyzer = PolicyAnalyzer()
    node = Transform(fn=analyzer.run, name="policy_analyzer")
"""

import numpy as np


# CartPole action names
ACTION_NAMES = {0: "push_left", 1: "push_right"}


class PolicyAnalyzer:
    """
    Analyzes the agent's policy and exploration behavior.

    Examines the Q-table summary to determine what actions the agent
    prefers across visited states, and tracks epsilon to show the
    transition from exploration to exploitation.

    Input (checkpoint dict):
        {
            "episode":  int,
            "epsilon":  float,
            "q_table":  {
                "n_visited_states": int,
                "action_counts":    list,   # preferred action per visited state
                "q_value_mean":     float,
                "q_value_max":      float,
            },
            ...
        }

    Output:
        {
            "episode":          int,
            "epsilon":          float,
            "phase":            "exploring" | "transitioning" | "exploiting",
            "n_visited_states": int,
            "action_dist":      dict,   # fraction of states preferring each action
            "dominant_action":  str,    # action preferred in most states
            "q_value_mean":     float,
            "q_value_max":      float,
        }
    """

    # Epsilon thresholds for naming the training phase
    EXPLORING_THRESHOLD    = 0.5
    EXPLOITING_THRESHOLD   = 0.1

    def __init__(self):
        pass   # Stateless — no history needed

    def run(self, checkpoint: dict) -> dict:
        """
        Analyze policy from one checkpoint.

        Args:
            checkpoint: Dict from CartPoleSource

        Returns:
            Dict with policy statistics and exploration phase
        """
        episode  = checkpoint["episode"]
        epsilon  = checkpoint["epsilon"]
        q_info   = checkpoint["q_table"]

        # Determine training phase
        if epsilon > self.EXPLORING_THRESHOLD:
            phase = "exploring"
        elif epsilon > self.EXPLOITING_THRESHOLD:
            phase = "transitioning"
        else:
            phase = "exploiting"

        # Action distribution across visited states
        action_counts = q_info["action_counts"]
        total_states  = q_info["n_visited_states"]

        if total_states > 0:
            action_dist = {
                ACTION_NAMES[i]: round(count / total_states, 3)
                for i, count in enumerate(action_counts)
            }
            dominant_idx    = int(np.argmax(action_counts))
            dominant_action = ACTION_NAMES[dominant_idx]
        else:
            action_dist     = {name: 0.0 for name in ACTION_NAMES.values()}
            dominant_action = "unknown"

        return {
            "episode":          episode,
            "epsilon":          epsilon,
            "phase":            phase,
            "n_visited_states": total_states,
            "action_dist":      action_dist,
            "dominant_action":  dominant_action,
            "q_value_mean":     round(q_info["q_value_mean"], 4),
            "q_value_max":      round(q_info["q_value_max"],  4),
        }


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("PolicyAnalyzer — Self Test")
    print("=" * 60)

    analyzer = PolicyAnalyzer()

    # Simulate checkpoints across training phases
    test_checkpoints = [
        {
            "episode": 50, "epsilon": 0.70,
            "q_table": {"n_visited_states": 171, "action_counts": [90, 81],
                        "q_value_mean": 0.5, "q_value_max": 2.1}
        },
        {
            "episode": 300, "epsilon": 0.12,
            "q_table": {"n_visited_states": 317, "action_counts": [180, 137],
                        "q_value_mean": 3.2, "q_value_max": 8.4}
        },
        {
            "episode": 700, "epsilon": 0.01,
            "q_table": {"n_visited_states": 383, "action_counts": [210, 173],
                        "q_value_mean": 6.1, "q_value_max": 14.2}
        },
    ]

    expected_phases = ["exploring", "transitioning", "exploiting"]

    print(f"\n{'Ep':>6}  {'Epsilon':>8}  {'Phase':>14}  {'Visited':>8}  {'Left':>6}  {'Right':>6}  {'Dominant':>12}")
    print("-" * 75)

    passed = 0
    for cp, expected_phase in zip(test_checkpoints, expected_phases):
        result = analyzer.run(cp)
        ok     = result["phase"] == expected_phase
        icon   = "✓" if ok else "✗"
        dist   = result["action_dist"]
        print(
            f"{result['episode']:>6}  "
            f"{result['epsilon']:>8.3f}  "
            f"{result['phase']:>14}  "
            f"{result['n_visited_states']:>8}  "
            f"{dist['push_left']:>6.3f}  "
            f"{dist['push_right']:>6.3f}  "
            f"{result['dominant_action']:>12}  "
            f"{icon}"
        )
        if ok:
            passed += 1

    print()
    print(f"Results: {passed}/{len(test_checkpoints)} passed")
    if passed == len(test_checkpoints):
        print("✓ PolicyAnalyzer working correctly")
