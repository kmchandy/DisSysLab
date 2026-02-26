# examples/module_06/app.py

"""
Module 06: Reinforcement Learning Agent Analyzer

A Q-learning agent trains on CartPole-v1 while three analyzers watch
in parallel — each examining a different aspect of its behavior.
MergeSynch waits for all three to finish before sending results to
the dashboard.

Network topology:

    cartpole_source ──→ reward_analyzer  ──┐
                    ├─→ policy_analyzer  ──┼──→ merge_synch ──→ dashboard
                    └─→ curve_analyzer   ──┘                └──→ archive

This is the gather-scatter pattern:
    - scatter: one checkpoint fans out to three parallel analyzers
    - gather:  MergeSynch collects all three results before proceeding

Each analyzer runs in its own thread simultaneously — this is distributed
systems doing real parallel computation.

Requirements:
    pip install gymnasium numpy

Run from the DisSysLab root directory:
    python3 -m examples.module_06.app
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink, MergeSynch
from components.sources.cartpole_source              import CartPoleSource
from components.transformers.reward_analyzer         import RewardAnalyzer
from components.transformers.policy_analyzer         import PolicyAnalyzer
from components.transformers.learning_curve_analyzer import LearningCurveAnalyzer
from components.sinks.rl_dashboard                   import RLDashboard
from components.sinks                                import JSONLRecorder


# ── Source: Q-learning agent ──────────────────────────────────────────────────
# Trains for 1000 episodes, emitting a checkpoint every 50.
# → 20 checkpoints total, ~2 minutes to run.
# To train longer: increase total_episodes
# To see more detail: decrease checkpoint_every

cart = CartPoleSource(
    total_episodes=1000,
    checkpoint_every=50,
    seed=42
)

# ── Three parallel analyzers ──────────────────────────────────────────────────
# Each receives the same checkpoint and examines a different aspect.
# They run in parallel threads — MergeSynch waits for all three.

reward_an = RewardAnalyzer()
policy_an = PolicyAnalyzer()
curve_an  = LearningCurveAnalyzer()

# ── Sinks ─────────────────────────────────────────────────────────────────────
dashboard = RLDashboard()
recorder  = JSONLRecorder(
    path="rl_training_log.jsonl",
    mode="w",
    flush_every=1,
    name="rl_archive"
)


def archive_merged(merged: list) -> None:
    """
    Flatten merged list into a single dict for JSONL archiving.

    MergeSynch emits a list [reward_result, policy_result, curve_result].
    This combines them into one flat dict so each line in the JSONL file
    contains the full picture for that checkpoint.
    """
    reward_r, policy_r, curve_r = merged
    flat = {
        "episode":          reward_r["episode"],
        "mean_reward":      reward_r["mean_reward"],
        "max_reward":       reward_r["max_reward"],
        "min_reward":       reward_r["min_reward"],
        "std_reward":       reward_r["std_reward"],
        "reward_trend":     reward_r["trend"],
        "trend_delta":      reward_r["trend_delta"],
        "epsilon":          policy_r["epsilon"],
        "phase":            policy_r["phase"],
        "n_visited_states": policy_r["n_visited_states"],
        "action_dist":      policy_r["action_dist"],
        "q_value_mean":     policy_r["q_value_mean"],
        "slope":            curve_r["slope"],
        "r_squared":        curve_r["r_squared"],
        "curve_verdict":    curve_r["verdict"],
        "projected_200":    curve_r["projected_200"],
    }
    recorder.run(flat)


# ── Build the network ─────────────────────────────────────────────────────────

cartpole_source = Source(fn=cart.run,         name="cartpole")
reward_node     = Transform(fn=reward_an.run, name="reward_analyzer")
policy_node     = Transform(fn=policy_an.run, name="policy_analyzer")
curve_node      = Transform(fn=curve_an.run,  name="curve_analyzer")
merge           = MergeSynch(num_inputs=3,    name="merge_synch")
dashboard_sink  = Sink(fn=dashboard.run,      name="dashboard")
archive_sink    = Sink(fn=archive_merged,     name="archive")

g = network([
    # Scatter: one source fans out to three analyzers
    (cartpole_source, reward_node),
    (cartpole_source, policy_node),
    (cartpole_source, curve_node),

    # Gather: three analyzers merge synchronously
    (reward_node, merge, "in_0"),
    (policy_node, merge, "in_1"),
    (curve_node,  merge, "in_2"),

    # Output: dashboard + archive both receive the merged result
    (merge, dashboard_sink),
    (merge, archive_sink),
])


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("Starting training. Each row = 50 episodes of Q-learning.")
    print("Watch the agent improve in real time.")
    print()
    g.run_network(timeout=300)
    print()
    print("Training complete.")
    print("Results saved to rl_training_log.jsonl")
    print()
    print("To plot the learning curve:")
    print("  import json, matplotlib.pyplot as plt")
    print("  data = [json.loads(l) for l in open('rl_training_log.jsonl')]")
    print("  plt.plot([d['episode'] for d in data], [d['mean_reward'] for d in data])")
    print("  plt.xlabel('Episode'); plt.ylabel('Mean Reward'); plt.show()")
