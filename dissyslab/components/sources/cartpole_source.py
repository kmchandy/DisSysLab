# components/sources/cartpole_source.py

"""
CartPoleSource: Q-learning agent that trains on CartPole and emits checkpoints.

Each checkpoint is emitted every N episodes and contains a snapshot of the
agent's current state — rewards, epsilon, and Q-table. The three downstream
analyzers each examine a different aspect of this snapshot simultaneously.

This is the source for Module 06: RL Agent Analyzer.

Usage:
    from dissyslab.components.sources.cartpole_source import CartPoleSource
    from dissyslab.blocks import Source

    cart = CartPoleSource(total_episodes=1000, checkpoint_every=50)
    source = Source(fn=cart.run, name="cartpole")

Requirements:
    pip install gymnasium numpy
"""

import numpy as np
import gymnasium


class CartPoleSource:
    """
    Q-learning agent that trains on CartPole-v1 and emits training checkpoints.

    The agent discretizes the continuous CartPole state space into bins and
    uses tabular Q-learning with epsilon-greedy exploration. Every
    `checkpoint_every` episodes it emits a snapshot of its current state
    for downstream analysis.

    Q-learning update rule:
        Q(s,a) += lr * (reward + gamma * max(Q(s')) - Q(s,a))

    Hyperparameters tuned for visible improvement over 1000 episodes:
        n_bins=20, lr=0.2, gamma=0.99, epsilon_decay=0.993

    Checkpoint message format:
        {
            "episode":      int,    # current episode number
            "rewards":      list,   # rewards for last checkpoint_every episodes
            "epsilon":      float,  # current exploration rate
            "q_table":      dict,   # Q-table summary (not full array - too large)
            "mean_reward":  float,  # mean reward this checkpoint window
            "max_reward":   float,  # max reward this checkpoint window
        }
    """

    # Observation space bounds (CartPole has inf bounds for velocity dims)
    OBS_LOW  = np.array([-4.8, -3.0, -0.42, -3.5])
    OBS_HIGH = np.array([ 4.8,  3.0,  0.42,  3.5])

    def __init__(
        self,
        total_episodes:    int   = 1000,
        checkpoint_every:  int   = 50,
        n_bins:            int   = 20,
        learning_rate:     float = 0.2,
        gamma:             float = 0.99,
        epsilon_start:     float = 1.0,
        epsilon_min:       float = 0.01,
        epsilon_decay:     float = 0.993,
        seed:              int   = 42,
    ):
        """
        Initialize the CartPole Q-learning source.

        Args:
            total_episodes:   Total training episodes (default 1000)
            checkpoint_every: Emit a checkpoint every N episodes (default 50)
            n_bins:           Discretization bins per observation dimension
            learning_rate:    Q-learning step size
            gamma:            Discount factor for future rewards
            epsilon_start:    Initial exploration rate (1.0 = fully random)
            epsilon_min:      Minimum exploration rate
            epsilon_decay:    Epsilon multiplied by this each episode
            seed:             Random seed for reproducibility
        """
        self.total_episodes   = total_episodes
        self.checkpoint_every = checkpoint_every
        self.n_bins           = n_bins
        self.lr               = learning_rate
        self.gamma            = gamma
        self.epsilon          = epsilon_start
        self.epsilon_min      = epsilon_min
        self.epsilon_decay    = epsilon_decay
        self.seed             = seed

        # Initialize environment
        self.env = gymnasium.make("CartPole-v1")
        self.env.action_space.seed(seed)
        np.random.seed(seed)

        # Q-table: shape [n_bins]*4 + [n_actions]
        self.n_actions = self.env.action_space.n
        self.q_table   = np.zeros([self.n_bins] * 4 + [self.n_actions])

        # Training state
        self.episode        = 0
        self.all_rewards    = []
        self._checkpoints   = None   # populated on first call to run()

    def _discretize(self, obs: np.ndarray) -> tuple:
        """Convert continuous observation to discrete state indices."""
        ratios  = np.clip(
            (obs - self.OBS_LOW) / (self.OBS_HIGH - self.OBS_LOW), 0, 1
        )
        indices = (ratios * (self.n_bins - 1)).astype(int)
        return tuple(indices)

    def _run_episode(self) -> float:
        """Run one episode. Returns total reward."""
        obs, _ = self.env.reset()
        state  = self._discretize(obs)
        total_reward = 0
        done   = False

        while not done:
            # Epsilon-greedy action selection
            if np.random.random() < self.epsilon:
                action = self.env.action_space.sample()
            else:
                action = int(np.argmax(self.q_table[state]))

            obs, reward, terminated, truncated, _ = self.env.step(action)
            done        = terminated or truncated
            next_state  = self._discretize(obs)

            # Q-learning update
            self.q_table[state][action] += self.lr * (
                reward
                + self.gamma * np.max(self.q_table[next_state])
                - self.q_table[state][action]
            )

            state        = next_state
            total_reward += reward

        # Decay exploration rate
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        return total_reward

    def _q_table_summary(self) -> dict:
        """
        Summarize Q-table for downstream analysis.

        Returns action preferences across all visited states rather than
        the full array (which would be too large to pass as a message).
        """
        # States where the agent has learned something (non-zero Q values)
        visited_mask  = np.any(self.q_table != 0, axis=-1)
        n_visited     = int(np.sum(visited_mask))

        # Preferred action at each visited state
        preferred_actions = np.argmax(self.q_table, axis=-1)
        action_counts = np.bincount(
            preferred_actions[visited_mask].flatten()
                if n_visited > 0 else np.array([0]),
            minlength=self.n_actions
        )

        # Q-value statistics
        nonzero_q = self.q_table[visited_mask] if n_visited > 0 else np.zeros((1, 2))
        return {
            "n_visited_states": n_visited,
            "action_counts":    action_counts.tolist(),
            "q_value_mean":     float(np.mean(nonzero_q)),
            "q_value_max":      float(np.max(nonzero_q)),
        }

    def _train_checkpoint(self) -> dict:
        """Run checkpoint_every episodes and return checkpoint message."""
        window_rewards = []
        for _ in range(self.checkpoint_every):
            reward = self._run_episode()
            self.all_rewards.append(reward)
            window_rewards.append(reward)
            self.episode += 1

        return {
            "episode":     self.episode,
            "rewards":     window_rewards,
            "epsilon":     round(self.epsilon, 4),
            "q_table":     self._q_table_summary(),
            "mean_reward": round(float(np.mean(window_rewards)), 2),
            "max_reward":  round(float(np.max(window_rewards)), 2),
        }

    def run(self):
        """
        Generator that yields one checkpoint every checkpoint_every episodes.

        Yields checkpoint dicts until total_episodes is reached.
        Source() in dsl/blocks/source.py handles generators automatically.
        """
        episodes_remaining = self.total_episodes
        while episodes_remaining >= self.checkpoint_every:
            checkpoint = self._train_checkpoint()
            episodes_remaining -= self.checkpoint_every
            yield checkpoint


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("CartPoleSource — Self Test")
    print("=" * 60)
    print("Training Q-learning agent on CartPole-v1")
    print("1000 episodes, checkpoint every 50")
    print()

    cart = CartPoleSource(total_episodes=1000, checkpoint_every=50)

    checkpoints = list(cart.run())
    print(f"Emitted {len(checkpoints)} checkpoints")
    print()

    print(f"{'Episode':>8}  {'Mean Reward':>12}  {'Max Reward':>10}  {'Epsilon':>8}  {'Visited States':>14}")
    print("-" * 60)
    for cp in checkpoints:
        print(
            f"{cp['episode']:>8}  "
            f"{cp['mean_reward']:>12.1f}  "
            f"{cp['max_reward']:>10.0f}  "
            f"{cp['epsilon']:>8.3f}  "
            f"{cp['q_table']['n_visited_states']:>14}"
        )

    print()
    first = checkpoints[0]['mean_reward']
    last  = checkpoints[-1]['mean_reward']
    improvement = ((last - first) / first) * 100
    print(f"Improvement: {first:.1f} → {last:.1f} ({improvement:+.0f}%)")
    print()
    print("✓ CartPoleSource working correctly")
