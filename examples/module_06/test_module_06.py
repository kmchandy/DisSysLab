# examples/module_06/test_module_06.py

"""
Tests for Module 06: RL Agent Analyzer

Three layers:
    1. Component tests  — each class works in isolation
    2. Function tests   — transform logic is correct
    3. Network test     — full network produces expected output
"""

import pytest
import numpy as np


from dissyslab.components.sources.cartpole_source import CartPoleSource
from dissyslab.components.transformers.reward_analyzer import RewardAnalyzer
from dissyslab.components.transformers.policy_analyzer import PolicyAnalyzer
from dissyslab.components.transformers.learning_curve_analyzer import LearningCurveAnalyzer
from dissyslab.components.sinks.rl_dashboard import RLDashboard


# ── Shared fixtures ───────────────────────────────────────────────────────────

def make_checkpoint(episode=100, mean_reward=50.0, rewards=None,
                    epsilon=0.3, n_visited=200, action_counts=None):
    """Create a minimal valid checkpoint dict for testing."""
    if rewards is None:
        rewards = [mean_reward] * 10
    if action_counts is None:
        action_counts = [110, 90]
    return {
        "episode":     episode,
        "rewards":     rewards,
        "epsilon":     epsilon,
        "mean_reward": mean_reward,
        "max_reward":  float(max(rewards)),
        "q_table": {
            "n_visited_states": n_visited,
            "action_counts":    action_counts,
            "q_value_mean":     3.2,
            "q_value_max":      8.4,
        }
    }


# ── Layer 1: Component tests ──────────────────────────────────────────────────

class TestCartPoleSource:
    """CartPoleSource emits correct number of checkpoints with correct shape."""

    def test_emits_correct_number_of_checkpoints(self):
        cart = CartPoleSource(total_episodes=200, checkpoint_every=50, seed=0)
        checkpoints = list(cart.run())
        assert len(checkpoints) == 4

    def test_checkpoint_has_required_keys(self):
        cart = CartPoleSource(total_episodes=50, checkpoint_every=50, seed=0)
        checkpoints = list(cart.run())
        cp = checkpoints[0]
        assert "episode" in cp
        assert "rewards" in cp
        assert "epsilon" in cp
        assert "q_table" in cp
        assert "mean_reward" in cp
        assert "max_reward" in cp

    def test_rewards_list_length(self):
        cart = CartPoleSource(total_episodes=100, checkpoint_every=50, seed=0)
        checkpoints = list(cart.run())
        for cp in checkpoints:
            assert len(cp["rewards"]) == 50

    def test_episode_numbers_are_correct(self):
        cart = CartPoleSource(total_episodes=200, checkpoint_every=50, seed=0)
        checkpoints = list(cart.run())
        assert checkpoints[0]["episode"] == 50
        assert checkpoints[1]["episode"] == 100
        assert checkpoints[2]["episode"] == 150
        assert checkpoints[3]["episode"] == 200

    def test_epsilon_decreases_over_time(self):
        cart = CartPoleSource(total_episodes=200, checkpoint_every=50, seed=0)
        checkpoints = list(cart.run())
        epsilons = [cp["epsilon"] for cp in checkpoints]
        assert epsilons[0] > epsilons[-1]

    def test_q_table_summary_has_required_keys(self):
        cart = CartPoleSource(total_episodes=50, checkpoint_every=50, seed=0)
        checkpoints = list(cart.run())
        qt = checkpoints[0]["q_table"]
        assert "n_visited_states" in qt
        assert "action_counts" in qt
        assert "q_value_mean" in qt
        assert "q_value_max" in qt

    def test_agent_learns_over_time(self):
        """Mean reward should increase from first to last checkpoint."""
        cart = CartPoleSource(total_episodes=1000,
                              checkpoint_every=50, seed=42)
        checkpoints = list(cart.run())
        first_mean = np.mean([cp["mean_reward"] for cp in checkpoints[:3]])
        last_mean = np.mean([cp["mean_reward"] for cp in checkpoints[-3:]])
        assert last_mean > first_mean, \
            f"Agent should improve: {first_mean:.1f} → {last_mean:.1f}"


class TestRewardAnalyzer:
    """RewardAnalyzer returns correct statistics and trend."""

    def setup_method(self):
        self.analyzer = RewardAnalyzer()

    def test_returns_required_keys(self):
        cp = make_checkpoint()
        result = self.analyzer.run(cp)
        assert "episode" in result
        assert "mean_reward" in result
        assert "max_reward" in result
        assert "min_reward" in result
        assert "std_reward" in result
        assert "trend" in result
        assert "trend_delta" in result

    def test_first_checkpoint_trend_is_starting(self):
        cp = make_checkpoint(episode=50)
        result = self.analyzer.run(cp)
        assert result["trend"] == "starting"

    def test_detects_improvement(self):
        self.analyzer.run(make_checkpoint(episode=50,  mean_reward=20.0))
        result = self.analyzer.run(
            make_checkpoint(episode=100, mean_reward=40.0))
        assert result["trend"] == "improving"

    def test_detects_plateau(self):
        self.analyzer.run(make_checkpoint(episode=50,  mean_reward=50.0))
        result = self.analyzer.run(
            make_checkpoint(episode=100, mean_reward=52.0))
        assert result["trend"] == "plateauing"

    def test_detects_decline(self):
        self.analyzer.run(make_checkpoint(episode=50,  mean_reward=80.0))
        result = self.analyzer.run(
            make_checkpoint(episode=100, mean_reward=60.0))
        assert result["trend"] == "declining"

    def test_mean_reward_is_correct(self):
        rewards = [10.0, 20.0, 30.0]
        cp = make_checkpoint(rewards=rewards, mean_reward=20.0)
        result = self.analyzer.run(cp)
        assert result["mean_reward"] == pytest.approx(20.0, abs=0.1)

    def test_max_reward_is_correct(self):
        rewards = [10.0, 20.0, 30.0]
        cp = make_checkpoint(rewards=rewards, mean_reward=20.0)
        result = self.analyzer.run(cp)
        assert result["max_reward"] == pytest.approx(30.0, abs=0.1)


class TestPolicyAnalyzer:
    """PolicyAnalyzer correctly identifies training phase and action distribution."""

    def setup_method(self):
        self.analyzer = PolicyAnalyzer()

    def test_returns_required_keys(self):
        cp = make_checkpoint()
        result = self.analyzer.run(cp)
        assert "episode" in result
        assert "epsilon" in result
        assert "phase" in result
        assert "n_visited_states" in result
        assert "action_dist" in result
        assert "dominant_action" in result

    def test_high_epsilon_is_exploring(self):
        cp = make_checkpoint(epsilon=0.8)
        result = self.analyzer.run(cp)
        assert result["phase"] == "exploring"

    def test_mid_epsilon_is_transitioning(self):
        cp = make_checkpoint(epsilon=0.3)
        result = self.analyzer.run(cp)
        assert result["phase"] == "transitioning"

    def test_low_epsilon_is_exploiting(self):
        cp = make_checkpoint(epsilon=0.01)
        result = self.analyzer.run(cp)
        assert result["phase"] == "exploiting"

    def test_action_dist_sums_to_one(self):
        cp = make_checkpoint(action_counts=[60, 40], n_visited=100)
        result = self.analyzer.run(cp)
        total = sum(result["action_dist"].values())
        assert total == pytest.approx(1.0, abs=0.01)

    def test_dominant_action_is_most_frequent(self):
        cp = make_checkpoint(action_counts=[80, 20], n_visited=100)
        result = self.analyzer.run(cp)
        assert result["dominant_action"] == "push_left"


class TestLearningCurveAnalyzer:
    """LearningCurveAnalyzer correctly fits trend and assigns verdict."""

    def setup_method(self):
        self.analyzer = LearningCurveAnalyzer()

    def test_returns_required_keys(self):
        cp = make_checkpoint()
        result = self.analyzer.run(cp)
        assert "episode" in result
        assert "n_checkpoints" in result
        assert "slope" in result
        assert "r_squared" in result
        assert "verdict" in result
        assert "projected_200" in result

    def test_first_checkpoint_is_gathering_data(self):
        cp = make_checkpoint(episode=50)
        result = self.analyzer.run(cp)
        assert result["verdict"] == "gathering data"

    def test_improving_trend_detected(self):
        rewards = [20, 30, 40, 50, 60, 70, 80, 90, 100, 110]
        for i, r in enumerate(rewards):
            result = self.analyzer.run(
                make_checkpoint(episode=(i+1)*50, mean_reward=float(r))
            )
        assert result["verdict"] == "improving"
        assert result["slope"] > 0

    def test_plateau_detected(self):
        analyzer = LearningCurveAnalyzer()
        for i in range(10):
            result = analyzer.run(
                make_checkpoint(episode=(i+1)*50, mean_reward=50.0)
            )
        assert result["verdict"] == "plateauing"

    def test_n_checkpoints_increments(self):
        for i in range(5):
            result = self.analyzer.run(
                make_checkpoint(episode=(i+1)*50, mean_reward=float(i*10))
            )
        assert result["n_checkpoints"] == 5

    def test_r_squared_between_0_and_1(self):
        for i in range(5):
            result = self.analyzer.run(
                make_checkpoint(episode=(i+1)*50, mean_reward=float(i*20))
            )
        assert 0.0 <= result["r_squared"] <= 1.0


# ── Layer 2: Integration — all three analyzers on real checkpoints ────────────

class TestAnalyzersOnRealCheckpoints:
    """All three analyzers process real CartPole checkpoints correctly."""

    def setup_method(self):
        cart = CartPoleSource(total_episodes=200, checkpoint_every=50, seed=42)
        self.checkpoints = list(cart.run())
        self.reward_an = RewardAnalyzer()
        self.policy_an = PolicyAnalyzer()
        self.curve_an = LearningCurveAnalyzer()

    def test_all_analyzers_return_dicts(self):
        cp = self.checkpoints[0]
        assert isinstance(self.reward_an.run(cp), dict)
        assert isinstance(self.policy_an.run(cp), dict)
        assert isinstance(self.curve_an.run(cp),  dict)

    def test_episode_numbers_match_across_analyzers(self):
        for cp in self.checkpoints:
            r = self.reward_an.run(cp)
            p = self.policy_an.run(cp)
            c = self.curve_an.run(cp)
            assert r["episode"] == p["episode"] == c["episode"] == cp["episode"]

    def test_dashboard_accepts_merged_output(self):
        dashboard = RLDashboard(show_header=False)
        for cp in self.checkpoints:
            r = self.reward_an.run(cp)
            p = self.policy_an.run(cp)
            c = self.curve_an.run(cp)
            # Should not raise
            dashboard.run([r, p, c])


# ── Layer 3: Network test ─────────────────────────────────────────────────────

class TestModule06Network:
    """Full network produces 20 merged checkpoints and archives them."""

    def test_network_runs_and_produces_output(self, tmp_path):
        """Network runs without error and archives all checkpoints."""
        from dissyslab import network
        from dissyslab.blocks import Source, Transform, Sink, MergeSynch
        from dissyslab.components.sinks import JSONLRecorder
        import json

        archive_path = str(tmp_path / "test_rl_log.jsonl")

        cart = CartPoleSource(total_episodes=100, checkpoint_every=50, seed=0)
        reward_an = RewardAnalyzer()
        policy_an = PolicyAnalyzer()
        curve_an = LearningCurveAnalyzer()
        recorder = JSONLRecorder(path=archive_path, mode="w", flush_every=1)

        results = []

        def collect_and_archive(merged):
            results.append(merged)
            reward_r, policy_r, curve_r = merged
            recorder.run({
                "episode":       reward_r["episode"],
                "mean_reward":   reward_r["mean_reward"],
                "slope":         curve_r["slope"],
                "phase":         policy_r["phase"],
            })

        cartpole_source = Source(fn=cart.run,         name="cartpole")
        reward_node = Transform(fn=reward_an.run, name="reward")
        policy_node = Transform(fn=policy_an.run, name="policy")
        curve_node = Transform(fn=curve_an.run,  name="curve")
        merge = MergeSynch(num_inputs=3,    name="merge")
        sink = Sink(fn=collect_and_archive, name="sink")

        g = network([
            (cartpole_source, reward_node),
            (cartpole_source, policy_node),
            (cartpole_source, curve_node),
            (reward_node, merge.in_0),
            (policy_node, merge.in_1),
            (curve_node,  merge.in_2),
            (merge, sink),
        ])

        g.run_network(timeout=60)

        # Should have 2 checkpoints (100 episodes / 50 per checkpoint)
        assert len(results) == 2

        # Each merged result should be a list of 3 dicts
        for merged in results:
            assert len(merged) == 3
            assert isinstance(merged[0], dict)
            assert isinstance(merged[1], dict)
            assert isinstance(merged[2], dict)

        # Archive file should exist with 2 lines
        with open(archive_path) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) == 2
        assert "episode" in lines[0]
        assert "mean_reward" in lines[0]
        assert "slope" in lines[0]

    def test_merge_synch_collects_all_three(self, tmp_path):
        """MergeSynch output is always a list of exactly 3 items."""
        from dissyslab import network
        from dissyslab.blocks import Source, Transform, Sink, MergeSynch

        cart = CartPoleSource(total_episodes=50, checkpoint_every=50, seed=0)
        reward_an = RewardAnalyzer()
        policy_an = PolicyAnalyzer()
        curve_an = LearningCurveAnalyzer()

        merged_outputs = []

        cartpole_source = Source(fn=cart.run,          name="cartpole")
        reward_node = Transform(fn=reward_an.run,  name="reward")
        policy_node = Transform(fn=policy_an.run,  name="policy")
        curve_node = Transform(fn=curve_an.run,   name="curve")
        merge = MergeSynch(num_inputs=3,     name="merge")
        sink = Sink(fn=merged_outputs.append, name="sink")

        g = network([
            (cartpole_source, reward_node),
            (cartpole_source, policy_node),
            (cartpole_source, curve_node),
            (reward_node, merge.in_0),
            (policy_node, merge.in_1),
            (curve_node,  merge.in_2),
            (merge, sink),
        ])

        g.run_network(timeout=60)

        assert len(merged_outputs) == 1
        assert len(merged_outputs[0]) == 3
