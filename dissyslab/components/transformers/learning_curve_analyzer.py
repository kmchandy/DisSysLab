# dissyslab/components/transformers/learning_curve_analyzer.py

"""
LearningCurveAnalyzer: Fits a trend line to reward history across checkpoints.

One of three parallel analyzers in Module 06. Maintains a history of mean
rewards across all checkpoints seen so far, fits a linear trend using
numpy.polyfit, and estimates whether the agent is still improving or has
plateaued.

This is the only stateful analyzer — it needs history across multiple
checkpoints to fit a meaningful trend line.

Usage:
    from dissyslab.components.transformers.learning_curve_analyzer import LearningCurveAnalyzer
    from dissyslab.blocks import Transform

    analyzer = LearningCurveAnalyzer()
    node = Transform(fn=analyzer.run, name="curve_analyzer")
"""

import numpy as np


class LearningCurveAnalyzer:
    """
    Fits a linear trend to the agent's reward history.

    Maintains a running list of (episode, mean_reward) pairs across all
    checkpoints. At each checkpoint, fits a linear trend using numpy.polyfit
    to estimate the improvement rate (slope) and goodness of fit (R²).

    The slope tells you: "on average, how many more reward points does
    the agent earn per episode?"

    Input (checkpoint dict):
        {
            "episode":     int,
            "mean_reward": float,
            ...
        }

    Output:
        {
            "episode":       int,
            "n_checkpoints": int,     # how many checkpoints seen so far
            "slope":         float,   # reward improvement per episode
            "r_squared":     float,   # goodness of fit (0-1)
            "verdict":       str,     # "improving" | "plateauing" | "declining"
            "projected_200": float,   # projected mean reward 200 episodes ahead
        }
    """

    # Minimum checkpoints before fitting a trend (need at least 2 points)
    MIN_CHECKPOINTS = 2

    # Slope thresholds for verdict
    IMPROVING_SLOPE  =  0.05   # reward units per episode
    DECLINING_SLOPE  = -0.05

    def __init__(self):
        self._episodes = []    # x axis
        self._rewards  = []    # y axis

    def run(self, checkpoint: dict) -> dict:
        """
        Update reward history and fit trend line.

        Args:
            checkpoint: Dict from CartPoleSource

        Returns:
            Dict with trend statistics and verdict
        """
        episode     = checkpoint["episode"]
        mean_reward = checkpoint["mean_reward"]

        # Accumulate history
        self._episodes.append(episode)
        self._rewards.append(mean_reward)

        n = len(self._episodes)

        if n < self.MIN_CHECKPOINTS:
            # Not enough data to fit a line yet
            return {
                "episode":       episode,
                "n_checkpoints": n,
                "slope":         0.0,
                "r_squared":     0.0,
                "verdict":       "gathering data",
                "projected_200": round(mean_reward, 2),
            }

        # Fit linear trend: reward = slope * episode + intercept
        x      = np.array(self._episodes)
        y      = np.array(self._rewards)
        coeffs = np.polyfit(x, y, deg=1)
        slope  = float(coeffs[0])
        intercept = float(coeffs[1])

        # R² — how well the line fits
        y_pred    = np.polyval(coeffs, x)
        ss_res    = np.sum((y - y_pred) ** 2)
        ss_tot    = np.sum((y - np.mean(y)) ** 2)
        r_squared = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0
        r_squared = max(0.0, min(1.0, r_squared))

        # Verdict based on slope
        if slope > self.IMPROVING_SLOPE:
            verdict = "improving"
        elif slope < self.DECLINING_SLOPE:
            verdict = "declining"
        else:
            verdict = "plateauing"

        # Project 200 episodes ahead
        projected = slope * (episode + 200) + intercept

        return {
            "episode":       episode,
            "n_checkpoints": n,
            "slope":         round(slope, 4),
            "r_squared":     round(r_squared, 4),
            "verdict":       verdict,
            "projected_200": round(projected, 2),
        }


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("LearningCurveAnalyzer — Self Test")
    print("=" * 60)

    analyzer = LearningCurveAnalyzer()

    # Simulate a realistic improving reward sequence
    # (matches what CartPoleSource produces with seed=42)
    test_checkpoints = [
        {"episode":  50,  "mean_reward": 23.0},
        {"episode": 100,  "mean_reward": 24.3},
        {"episode": 150,  "mean_reward": 22.7},
        {"episode": 200,  "mean_reward": 36.1},
        {"episode": 250,  "mean_reward": 46.5},
        {"episode": 300,  "mean_reward": 46.1},
        {"episode": 350,  "mean_reward": 51.8},
        {"episode": 400,  "mean_reward": 49.0},
        {"episode": 450,  "mean_reward": 48.9},
        {"episode": 500,  "mean_reward": 54.6},
        {"episode": 550,  "mean_reward": 53.7},
        {"episode": 600,  "mean_reward": 52.8},
        {"episode": 650,  "mean_reward": 66.6},
        {"episode": 700,  "mean_reward": 77.1},
        {"episode": 750,  "mean_reward": 67.1},
        {"episode": 800,  "mean_reward": 91.1},
        {"episode": 850,  "mean_reward": 89.5},
        {"episode": 900,  "mean_reward": 94.5},
        {"episode": 950,  "mean_reward": 102.6},
        {"episode": 1000, "mean_reward": 114.5},
    ]

    print(f"\n{'Ep':>6}  {'N':>3}  {'Slope':>8}  {'R²':>6}  {'Verdict':>14}  {'Proj+200':>10}")
    print("-" * 60)

    for cp in test_checkpoints:
        result = analyzer.run(cp)
        print(
            f"{result['episode']:>6}  "
            f"{result['n_checkpoints']:>3}  "
            f"{result['slope']:>8.4f}  "
            f"{result['r_squared']:>6.4f}  "
            f"{result['verdict']:>14}  "
            f"{result['projected_200']:>10.1f}"
        )

    print()
    final = analyzer.run(test_checkpoints[-1])
    print(f"Final slope:  {final['slope']:.4f} reward/episode")
    print(f"Final R²:     {final['r_squared']:.4f}")
    print(f"Final verdict: {final['verdict']}")
    print()

    # Verify final verdict is "improving"
    if final["verdict"] == "improving" and final["slope"] > 0:
        print("✓ LearningCurveAnalyzer working correctly")
    else:
        print("✗ Expected improving verdict with positive slope")
