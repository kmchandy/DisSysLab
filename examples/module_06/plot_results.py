# examples/module_06/plot_results.py

"""
Plot the learning curve from rl_training_log.jsonl

Run after app.py has completed:
    python3 examples/module_06/plot_results.py

Requires:
    pip install matplotlib
"""

import json
import sys
import os
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np


# ── Load data ─────────────────────────────────────────────────────────────────

LOGFILE = "rl_training_log.jsonl"

if not os.path.exists(LOGFILE):
    print(f"Error: {LOGFILE} not found.")
    print("Run app.py first:  python3 -m examples.module_06.app")
    sys.exit(1)

with open(LOGFILE) as f:
    data = [json.loads(line) for line in f if line.strip()]

if not data:
    print(f"Error: {LOGFILE} is empty.")
    sys.exit(1)

print(f"Loaded {len(data)} checkpoints from {LOGFILE}")

# ── Extract series ────────────────────────────────────────────────────────────

episodes = [d["episode"] for d in data]
mean_rewards = [d["mean_reward"] for d in data]
max_rewards = [d["max_reward"] for d in data]
min_rewards = [d["min_reward"] for d in data]
std_rewards = [d["std_reward"] for d in data]
epsilons = [d["epsilon"] for d in data]
slopes = [d["slope"] for d in data]
r_squareds = [d["r_squared"] for d in data]
n_visited = [d["n_visited_states"] for d in data]
q_means = [d["q_value_mean"] for d in data]

mean_arr = np.array(mean_rewards)
std_arr = np.array(std_rewards)

# ── Plot ──────────────────────────────────────────────────────────────────────

fig = plt.figure(figsize=(14, 10))
fig.suptitle("CartPole Q-Learning — Training Analysis",
             fontsize=14, fontweight="bold")

gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)

# ── Panel 1: Learning curve ───────────────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, :])   # full width
ax1.plot(episodes, mean_rewards, "b-o", linewidth=2,
         markersize=5, label="Mean reward")
ax1.fill_between(
    episodes,
    mean_arr - std_arr,
    mean_arr + std_arr,
    alpha=0.2, color="blue", label="±1 std dev"
)
ax1.plot(episodes, max_rewards, "g--", linewidth=1,
         alpha=0.6, label="Max reward")
ax1.plot(episodes, min_rewards, "r--", linewidth=1,
         alpha=0.6, label="Min reward")
ax1.axhline(y=200, color="green",  linestyle=":",
            alpha=0.5, label="Good (200)")
ax1.axhline(y=475, color="purple", linestyle=":",
            alpha=0.5, label="Excellent (475)")
ax1.set_xlabel("Episode")
ax1.set_ylabel("Reward")
ax1.set_title("Learning Curve — Mean ± Std Dev per Checkpoint")
ax1.legend(loc="upper left", fontsize=8)
ax1.grid(True, alpha=0.3)

# ── Panel 2: Exploration rate ─────────────────────────────────────────────────
ax2 = fig.add_subplot(gs[1, 0])
ax2.plot(episodes, epsilons, "orange", linewidth=2, marker="o", markersize=4)
ax2.axhline(y=0.5,  color="gray", linestyle="--",
            alpha=0.5, label="Exploring threshold")
ax2.axhline(y=0.1,  color="gray", linestyle=":",
            alpha=0.5, label="Exploiting threshold")
ax2.set_xlabel("Episode")
ax2.set_ylabel("Epsilon (ε)")
ax2.set_title("Exploration Rate Decay")
ax2.legend(fontsize=8)
ax2.grid(True, alpha=0.3)

# ── Panel 3: Improvement rate ─────────────────────────────────────────────────
ax3 = fig.add_subplot(gs[1, 1])
ax3.plot(episodes, slopes, "purple", linewidth=2, marker="o", markersize=4)
ax3.axhline(y=0, color="red", linestyle="--", alpha=0.5, label="Zero slope")
ax3.fill_between(episodes, slopes, 0,
                 where=[s > 0 for s in slopes],
                 alpha=0.2, color="green", label="Improving")
ax3.fill_between(episodes, slopes, 0,
                 where=[s < 0 for s in slopes],
                 alpha=0.2, color="red",   label="Declining")
ax3.set_xlabel("Episode")
ax3.set_ylabel("Slope (reward/episode)")
ax3.set_title("Improvement Rate (from LearningCurveAnalyzer)")
ax3.legend(fontsize=8)
ax3.grid(True, alpha=0.3)

# ── Panel 4: States visited ───────────────────────────────────────────────────
ax4 = fig.add_subplot(gs[2, 0])
ax4.plot(episodes, n_visited, "teal", linewidth=2, marker="o", markersize=4)
ax4.set_xlabel("Episode")
ax4.set_ylabel("Unique states visited")
ax4.set_title("State Space Coverage")
ax4.grid(True, alpha=0.3)

# ── Panel 5: Q-value growth ───────────────────────────────────────────────────
ax5 = fig.add_subplot(gs[2, 1])
ax5.plot(episodes, q_means, "brown", linewidth=2, marker="o", markersize=4,
         label="Mean Q-value")
ax5.set_xlabel("Episode")
ax5.set_ylabel("Mean Q-value")
ax5.set_title("Q-Value Growth (confidence in decisions)")
ax5.legend(fontsize=8)
ax5.grid(True, alpha=0.3)

# ── Save and show ─────────────────────────────────────────────────────────────

outfile = "rl_training_analysis.png"
plt.savefig(outfile, dpi=150, bbox_inches="tight")
print(f"Saved to {outfile}")
plt.show()

# ── Print summary ─────────────────────────────────────────────────────────────

print()
print("=" * 50)
print("Training Summary")
print("=" * 50)
print(f"Episodes trained:     {episodes[-1]}")
print(f"Checkpoints logged:   {len(data)}")
print()
print(f"First checkpoint:     mean reward = {mean_rewards[0]:.1f}")
print(f"Last checkpoint:      mean reward = {mean_rewards[-1]:.1f}")
improvement = mean_rewards[-1] - mean_rewards[0]
pct = (improvement / mean_rewards[0]) * 100 if mean_rewards[0] > 0 else 0
print(f"Total improvement:    {improvement:+.1f} ({pct:+.0f}%)")
print()
print(f"Best checkpoint:      episode {episodes[mean_rewards.index(max(mean_rewards))]}"
      f"  mean={max(mean_rewards):.1f}")
print(f"Max single episode:   {max(max_rewards):.0f}")
print()
print(f"Final epsilon:        {epsilons[-1]:.4f}")
print(f"Final slope:          {slopes[-1]:+.4f} reward/episode")
print(f"Final R²:             {r_squareds[-1]:.4f}")
print(f"States explored:      {n_visited[-1]}")
print("=" * 50)


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    pass   # script runs top-to-bottom, nothing extra needed
