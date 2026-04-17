# Module 06: Gather-Scatter — Watching an AI Agent Learn

A reinforcement learning agent trains on CartPole while three analyzers
watch in parallel. Each analyzer examines a different aspect of the agent's
behavior. The results snap together and print as a live dashboard.

This module introduces the **gather-scatter pattern** — the most powerful
topology in distributed systems.

---

## Part 1: Run It (5 minutes)

```bash
pip install gymnasium
python3 -m examples.module_06.app
```

You should see output like this, updating every 50 training episodes:

```
╔═════════════════════════════════════════════════════════════════╗
║   🤖  CartPole Q-Learning — Live Training Dashboard             ║
║   Watching 3 analyzers run in parallel via MergeSynch           ║
╚═════════════════════════════════════════════════════════════════╝

┌─ Episode   50  (checkpoint  1/20) ──────────────────────────────
│  Rewards   🚀 mean=   23.0  max=   77.0  std= 12.3  Δ=  +0.0
│  Policy    🎲 phase=exploring       ε=0.704  ←53% →47%  states=171
│  Curve     🔍 gathering data  slope=+0.0000/ep  R²=0.000  proj+200=23.0
└─────────────────────────────────────────────────────────────────

┌─ Episode  500  (checkpoint 10/20) ──────────────────────────────
│  Rewards   📈 mean=   54.6  max=  122.0  std= 24.1  Δ= +12.3
│  Policy    🔄 phase=transitioning   ε=0.030  ←55% →45%  states=353
│  Curve     📈 improving       slope=+0.0769/ep  R²=0.847  proj+200=73.0
└─────────────────────────────────────────────────────────────────

┌─ Episode 1000  (checkpoint 20/20) ──────────────────────────────
│  Rewards   📈 mean=  114.5  max=  429.0  std= 89.2  Δ= +11.9
│  Policy    🎯 phase=exploiting      ε=0.010  ←56% →44%  states=457
│  Curve     📈 improving       slope=+0.0872/ep  R²=0.928  proj+200=119.5
└─────────────────────────────────────────────────────────────────
```

The agent starts at mean reward ~23. By episode 1000 it reaches ~115,
occasionally balancing perfectly (reward=500). Watch the three rows change
as the agent learns.

---

## Part 2: Understand It (20 minutes)

### What is CartPole?

CartPole is a classic RL problem: a pole is attached to a cart that can
slide left or right. The agent must push the cart left or right to keep
the pole from falling. Each step the pole stays upright = 1 reward point.
Maximum score per episode = 500.

A random agent scores ~20. A trained agent scores ~150–500.

### What is Q-learning?

Q-learning is a table-based RL algorithm. It maintains a **Q-table** —
a lookup table mapping (state, action) pairs to expected future reward.

```
Q(state, action) = "how much total reward can I expect if I take
                    this action in this state?"
```

The update rule after each step:

```python
Q(state, action) += learning_rate * (
    reward
    + gamma * max(Q(next_state))   # best future reward
    - Q(state, action)             # what we expected
)
```

Over thousands of episodes, the Q-table converges to a good policy.

### The gather-scatter pattern

The network topology is:

```
cartpole_source ──→ reward_analyzer  ──┐
                ├─→ policy_analyzer  ──┼──→ merge_synch ──→ dashboard
                └─→ curve_analyzer   ──┘                └──→ archive
```

**Scatter**: one checkpoint fans out to three analyzers simultaneously.
Each analyzer runs in its own thread — they work in parallel, not in series.

**Gather**: `MergeSynch` waits until all three analyzers have finished,
then emits a list `[reward_result, policy_result, curve_result]` to the
dashboard.

This is the key insight: the dashboard sees one complete picture per
checkpoint, assembled from three independent analyses. No analyzer needs
to know about the others.

### The three analyzers

**RewardAnalyzer** — answers "how well is the agent performing right now?"

Computes mean, max, min, std of rewards over the last 50 episodes and
compares to the previous checkpoint to determine trend.

```python
{"mean_reward": 54.6, "max_reward": 122.0, "trend": "improving", "trend_delta": +12.3}
```

**PolicyAnalyzer** — answers "how is the agent behaving?"

Examines the Q-table to see which actions the agent prefers across visited
states. Tracks epsilon (exploration rate) to name the training phase.

```python
{"epsilon": 0.030, "phase": "transitioning", "action_dist": {"push_left": 0.55, "push_right": 0.45}}
```

**LearningCurveAnalyzer** — answers "is the agent still getting better?"

Maintains a history of all mean rewards seen so far and fits a linear
trend using `numpy.polyfit`. The slope tells you the improvement rate
in reward points per episode.

```python
{"slope": 0.0769, "r_squared": 0.847, "verdict": "improving", "projected_200": 73.0}
```

This is the only **stateful** analyzer. It needs to remember all previous
checkpoints to fit a trend. It uses the same pattern as `JSONLRecorder`
and `CartPoleSource` — a class with state and a `run` method.

### MergeSynch in detail

```python
merge = MergeSynch(num_inputs=3, name="merge_synch")

g = network([
    (reward_node, merge.in_0),   # ← port name required
    (policy_node, merge.in_1),
    (curve_node,  merge.in_2),
    (merge, dashboard_sink),
])
```

`MergeSynch` collects one message from each input **in round-robin order**
(in_0, then in_1, then in_2) and emits them as a list. It blocks on each
port until a message arrives. If any input sends STOP, the whole merge
terminates.

The dashboard receives `[reward_result, policy_result, curve_result]`
and unpacks it:

```python
def run(self, merged: list) -> None:
    reward_result, policy_result, curve_result = merged
    # ... print dashboard
```

### Why parallel matters

Without parallel analysis the network would be:

```
source → reward_analyzer → policy_analyzer → curve_analyzer → dashboard
```

Each checkpoint would wait for the previous analyzer to finish before
starting the next. With gather-scatter, all three run simultaneously —
the total time per checkpoint equals the slowest analyzer, not the sum
of all three.

For three fast numpy operations this difference is small. For expensive
operations (API calls, model inference, database lookups) it is enormous.

---

## Part 3: Make It Yours (15 minutes)

### Ask Claude to modify it

Try these prompts:

> Add a fourth analyzer that tracks the variance of Q-values over time.
> High variance means the agent is still learning. Low variance means
> it has converged.

> Change the app to run for 3000 episodes instead of 1000 and checkpoint
> every 100 episodes. Does the agent keep improving?

> Add a fifth analyzer that detects if the agent is oscillating — scoring
> very high some episodes and very low others.

### Change hyperparameters by hand

In `cartpole_source.py`, try:

```python
cart = CartPoleSource(
    total_episodes=1000,
    checkpoint_every=50,
    learning_rate=0.5,    # was 0.2 — faster learning, less stable
    epsilon_decay=0.999,  # was 0.993 — slower exploration decay
    seed=42
)
```

Higher learning rate can speed up early learning but cause instability
later. Slower epsilon decay means more exploration for longer.

### Plot the learning curve

After running `app.py`, a file `rl_training_log.jsonl` is saved. Plot it:

```python
import json
import matplotlib.pyplot as plt

data = [json.loads(line) for line in open("rl_training_log.jsonl")]

episodes     = [d["episode"]     for d in data]
mean_rewards = [d["mean_reward"] for d in data]
slopes       = [d["slope"]       for d in data]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

ax1.plot(episodes, mean_rewards, marker="o")
ax1.set_xlabel("Episode")
ax1.set_ylabel("Mean Reward")
ax1.set_title("Learning Curve")
ax1.axhline(y=200, color="green", linestyle="--", label="Good performance")
ax1.legend()

ax2.plot(episodes, slopes, marker="o", color="orange")
ax2.set_xlabel("Episode")
ax2.set_ylabel("Slope (reward/episode)")
ax2.set_title("Improvement Rate Over Time")
ax2.axhline(y=0, color="red", linestyle="--")

plt.tight_layout()
plt.savefig("learning_curve.png")
plt.show()
```

---

## Part 4: Real AI — Swap the Environment (30 minutes)

CartPole is a toy. The same network works on any gymnasium environment.
Change **one line** to try a harder problem:

```python
# In cartpole_source.py, replace:
self.env = gymnasium.make("CartPole-v1")

# With:
self.env = gymnasium.make("MountainCar-v0")   # Harder — sparse rewards
self.env = gymnasium.make("Acrobot-v1")        # Two-link robot arm
```

You will also need to adjust the observation space bounds and bin counts
for each environment — they have different state spaces.

---

## How Each File Works

Test each component independently before running the full network:

```bash
# Each file has a __main__ block showing its behavior
python3 dissyslab/components/sources/cartpole_source.py          # 1000 ep training, shows learning curve
python3 dissyslab/components/transformers/reward_analyzer.py     # analyzes sample checkpoints
python3 dissyslab/components/transformers/policy_analyzer.py     # shows training phases
python3 dissyslab/components/transformers/learning_curve_analyzer.py  # fits trend to sample data
python3 dissyslab/components/sinks/rl_dashboard.py               # shows formatted output
```

| File | What it does |
|------|-------------|
| `cartpole_source.py` | Q-learning agent, emits checkpoint every 50 episodes |
| `reward_analyzer.py` | Reward stats + trend vs previous checkpoint |
| `policy_analyzer.py` | Epsilon, training phase, action preferences |
| `learning_curve_analyzer.py` | Linear trend fit across all checkpoints |
| `rl_dashboard.py` | Terminal dashboard, unpacks MergeSynch output |
| `app.py` | Full network wiring |
| `test_module_06.py` | Tests for all components and the network |

---

## Run the Tests

```bash
pytest examples/module_06/test_module_06.py -v
```

---

## Key Concepts in This Module

**Gather-scatter** — fan out to multiple parallel workers, then collect
all results before proceeding. Use when you need multiple independent
analyses of the same data and want them all before making a decision.

**MergeSynch** — synchronous merge. Waits for one message from each
input in order before emitting. Use when inputs produce at the same rate
and you need all results together. For inputs at different rates, use
`MergeAsynch` instead.

**Stateful transforms** — when an analyzer needs history across multiple
messages, wrap it in a class. The `run` method does one step; the instance
holds the accumulated state.

**Reinforcement learning** — an agent learns by trial and error, receiving
rewards for good actions. Q-learning stores a table of expected rewards
for each (state, action) pair and updates it after every step.

---

## Next Module

Module 07 applies the same gather-scatter pattern to image analysis —
three analyzers examining color, texture, and edges of images in parallel.
The DSL network is identical. Only the source and analyzers change.