# components/transformers/reward_analyzer.py

"""
RewardAnalyzer: Analyzes reward statistics from a CartPole training checkpoint.

One of three parallel analyzers in Module 06. Examines the rewards from the
last checkpoint window and determines whether performance is improving,
plateauing, or declining relative to the previous checkpoint.

Usage:
    from components.transformers.reward_analyzer import RewardAnalyzer
    from dsl.blocks import Transform

    analyzer = RewardAnalyzer()
    node = Transform(fn=analyzer.run, name="reward_analyzer")
"""

import numpy as np


class RewardAnalyzer:
    """
    Analyzes reward statistics from a training checkpoint.

    Stateful: remembers the previous checkpoint's mean reward to determine
    whether performance is trending up, down, or flat.

    Input (checkpoint dict):
        {
            "episode":     int,
            "rewards":     list of floats,
            "mean_reward": float,
            "max_reward":  float,
            ...
        }

    Output:
        {
            "episode":      int,
            "mean_reward":  float,
            "max_reward":   float,
            "min_reward":   float,
            "std_reward":   float,
            "trend":        "improving" | "plateauing" | "declining",
            "trend_delta":  float,   # change from previous checkpoint
        }
    """

    # Threshold for calling a change "improvement" vs "plateau"
    IMPROVEMENT_THRESHOLD = 5.0   # reward units

    def __init__(self):
        self._prev_mean = None

    def run(self, checkpoint: dict) -> dict:
        """
        Analyze reward statistics from one checkpoint.

        Args:
            checkpoint: Dict from CartPoleSource containing rewards list

        Returns:
            Dict with reward statistics and trend assessment
        """
        rewards     = checkpoint["rewards"]
        episode     = checkpoint["episode"]
        mean_reward = float(np.mean(rewards))
        max_reward  = float(np.max(rewards))
        min_reward  = float(np.min(rewards))
        std_reward  = float(np.std(rewards))

        # Determine trend vs previous checkpoint
        if self._prev_mean is None:
            trend       = "starting"
            trend_delta = 0.0
        else:
            trend_delta = mean_reward - self._prev_mean
            if trend_delta > self.IMPROVEMENT_THRESHOLD:
                trend = "improving"
            elif trend_delta < -self.IMPROVEMENT_THRESHOLD:
                trend = "declining"
            else:
                trend = "plateauing"

        self._prev_mean = mean_reward

        return {
            "episode":     episode,
            "mean_reward": round(mean_reward, 2),
            "max_reward":  round(max_reward,  2),
            "min_reward":  round(min_reward,  2),
            "std_reward":  round(std_reward,  2),
            "trend":       trend,
            "trend_delta": round(trend_delta, 2),
        }


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("RewardAnalyzer — Self Test")
    print("=" * 60)

    analyzer = RewardAnalyzer()

    # Simulate checkpoints with improving rewards
    test_checkpoints = [
        {"episode":  50, "rewards": [10, 15, 12, 18, 11], "mean_reward": 13.2, "max_reward": 18},
        {"episode": 100, "rewards": [20, 25, 22, 28, 21], "mean_reward": 23.2, "max_reward": 28},
        {"episode": 150, "rewards": [22, 24, 23, 25, 22], "mean_reward": 23.2, "max_reward": 25},
        {"episode": 200, "rewards": [15, 18, 14, 17, 16], "mean_reward": 16.0, "max_reward": 18},
    ]

    expected_trends = ["starting", "improving", "plateauing", "declining"]

    print(f"\n{'Episode':>8}  {'Mean':>6}  {'Max':>6}  {'Min':>6}  {'Std':>6}  {'Trend':>12}  {'Delta':>8}")
    print("-" * 70)

    passed = 0
    for cp, expected in zip(test_checkpoints, expected_trends):
        result = analyzer.run(cp)
        ok     = result["trend"] == expected
        icon   = "✓" if ok else "✗"
        print(
            f"{result['episode']:>8}  "
            f"{result['mean_reward']:>6.1f}  "
            f"{result['max_reward']:>6.1f}  "
            f"{result['min_reward']:>6.1f}  "
            f"{result['std_reward']:>6.1f}  "
            f"{result['trend']:>12}  "
            f"{result['trend_delta']:>+8.1f}  "
            f"{icon}"
        )
        if ok:
            passed += 1
        else:
            print(f"         Expected trend: {expected}")

    print()
    print(f"Results: {passed}/{len(test_checkpoints)} passed")
    if passed == len(test_checkpoints):
        print("✓ RewardAnalyzer working correctly")
