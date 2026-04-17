# dissyslab/components/sinks/rl_dashboard.py

"""
RLDashboard: Displays merged RL analysis results to the terminal.

Receives the merged output from MergeSynch — a list of three dicts,
one from each analyzer — and prints a clean per-checkpoint summary.

Usage:
    from dissyslab.components.sinks.rl_dashboard import RLDashboard
    from dissyslab.blocks import Sink

    dashboard = RLDashboard()
    sink = Sink(fn=dashboard.run, name="dashboard")

The merged message format (list from MergeSynch):
    [reward_result, policy_result, curve_result]
"""


# Trend → emoji mapping for visual feedback
TREND_ICONS = {
    "improving":    "📈",
    "plateauing":   "➡️ ",
    "declining":    "📉",
    "starting":     "🚀",
    "gathering data": "🔍",
}

PHASE_ICONS = {
    "exploring":    "🎲",
    "transitioning": "🔄",
    "exploiting":   "🎯",
}


class RLDashboard:
    """
    Terminal dashboard for RL training progress.

    Receives merged output from MergeSynch and prints a structured
    summary showing reward statistics, policy behavior, and learning
    curve trend for each checkpoint.
    """

    def __init__(self, show_header: bool = True):
        self._checkpoint_count = 0
        self._show_header      = show_header

    def run(self, merged: list) -> None:
        """
        Display one checkpoint's merged analysis.

        Args:
            merged: List of [reward_result, policy_result, curve_result]
                    from MergeSynch
        """
        reward_result, policy_result, curve_result = merged

        self._checkpoint_count += 1
        episode = reward_result["episode"]

        if self._show_header and self._checkpoint_count == 1:
            self._print_header()

        # Trend and phase icons
        trend_icon = TREND_ICONS.get(reward_result["trend"], "  ")
        phase_icon = PHASE_ICONS.get(policy_result["phase"], "  ")
        curve_icon = TREND_ICONS.get(curve_result["verdict"], "  ")

        # Action distribution
        dist        = policy_result["action_dist"]
        left_pct    = dist.get("push_left",  0) * 100
        right_pct   = dist.get("push_right", 0) * 100

        print(f"┌─ Episode {episode:>4}  (checkpoint {self._checkpoint_count:>2}/20) "
              f"{'─' * 30}")
        print(f"│  Rewards   {trend_icon} mean={reward_result['mean_reward']:>7.1f}  "
              f"max={reward_result['max_reward']:>7.1f}  "
              f"std={reward_result['std_reward']:>5.1f}  "
              f"Δ={reward_result['trend_delta']:>+6.1f}")
        print(f"│  Policy    {phase_icon} phase={policy_result['phase']:<14}  "
              f"ε={policy_result['epsilon']:.3f}  "
              f"←{left_pct:.0f}% →{right_pct:.0f}%  "
              f"states={policy_result['n_visited_states']}")
        print(f"│  Curve     {curve_icon} {curve_result['verdict']:<14}  "
              f"slope={curve_result['slope']:>+.4f}/ep  "
              f"R²={curve_result['r_squared']:.3f}  "
              f"proj+200={curve_result['projected_200']:.1f}")
        print(f"└{'─' * 65}")
        print()

    def _print_header(self):
        """Print dashboard header on first checkpoint."""
        print()
        print("╔" + "═" * 65 + "╗")
        print("║   🤖  CartPole Q-Learning — Live Training Dashboard" + " " * 13 + "║")
        print("║   Watching 3 analyzers run in parallel via MergeSynch" + " " * 10 + "║")
        print("╚" + "═" * 65 + "╝")
        print()
        print("  Each checkpoint = 50 training episodes")
        print("  📈 improving  ➡️  plateauing  📉 declining")
        print("  🎲 exploring  🔄 transitioning  🎯 exploiting")
        print()


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("RLDashboard — Self Test")
    print("=" * 60)
    print("Simulating merged output from MergeSynch...")
    print()

    dashboard = RLDashboard()

    # Simulate merged messages as MergeSynch would emit them
    test_merges = [
        [
            # reward_result
            {"episode": 50, "mean_reward": 23.0, "max_reward": 77.0,
             "min_reward": 9.0, "std_reward": 12.3,
             "trend": "starting", "trend_delta": 0.0},
            # policy_result
            {"episode": 50, "epsilon": 0.704, "phase": "exploring",
             "n_visited_states": 171,
             "action_dist": {"push_left": 0.526, "push_right": 0.474},
             "dominant_action": "push_left",
             "q_value_mean": 0.5, "q_value_max": 2.1},
            # curve_result
            {"episode": 50, "n_checkpoints": 1, "slope": 0.0,
             "r_squared": 0.0, "verdict": "gathering data",
             "projected_200": 23.0},
        ],
        [
            {"episode": 500, "mean_reward": 54.6, "max_reward": 122.0,
             "min_reward": 18.0, "std_reward": 24.1,
             "trend": "improving", "trend_delta": 12.3},
            {"episode": 500, "epsilon": 0.030, "phase": "transitioning",
             "n_visited_states": 353,
             "action_dist": {"push_left": 0.548, "push_right": 0.452},
             "dominant_action": "push_left",
             "q_value_mean": 5.2, "q_value_max": 11.4},
            {"episode": 500, "n_checkpoints": 10, "slope": 0.0769,
             "r_squared": 0.8473, "verdict": "improving",
             "projected_200": 73.0},
        ],
        [
            {"episode": 1000, "mean_reward": 114.5, "max_reward": 429.0,
             "min_reward": 22.0, "std_reward": 89.2,
             "trend": "improving", "trend_delta": 11.9},
            {"episode": 1000, "epsilon": 0.010, "phase": "exploiting",
             "n_visited_states": 457,
             "action_dist": {"push_left": 0.561, "push_right": 0.439},
             "dominant_action": "push_left",
             "q_value_mean": 8.3, "q_value_max": 16.7},
            {"episode": 1000, "n_checkpoints": 20, "slope": 0.0872,
             "r_squared": 0.9284, "verdict": "improving",
             "projected_200": 119.5},
        ],
    ]

    for merged in test_merges:
        dashboard.run(merged)

    print("✓ RLDashboard working correctly")
