# Office: paxos

# DRAFT -- for review.
#
# Three proposers and five acceptors, the agents of figure 1 of
# course/Paxos.html.
#
# A proposer sends the same read, and later the same write, to every
# acceptor, so it needs one outbox for all five. An acceptor's reply, on
# the other hand, goes to the proposer that asked and to nobody else, so
# an acceptor needs one outbox per proposer. It needs only one for the
# learners, because it tells them both the same thing.
#
# A majority of five acceptors is three, which is the `majority=3` below.
#
# Each proposer has its own alarm clock, waking it every T ± delta
# milliseconds. Nothing in the algorithm depends on when a proposer
# tries; T decides only how often transactions overlap. See
# roles/ticker.py on choosing it. Drop the seeds for a different run
# every time.

Sources: starter
Sinks:   console_printer

Agents:
CLOCK0 is a ticker(ticks=10, T=5, delta=2, seed=0).
CLOCK1 is a ticker(ticks=10, T=5, delta=2, seed=1).
CLOCK2 is a ticker(ticks=10, T=5, delta=2, seed=2).
P0 is a proposer(value="green", majority=3).
P1 is a proposer(value="blue", majority=3).
P2 is a proposer(value="red", majority=3).
Q0 is an acceptor.
Q1 is an acceptor.
Q2 is an acceptor.
Q3 is an acceptor.
Q4 is an acceptor.
L0 is a learner(majority=3).
L1 is a learner(majority=3).

Connections:
starter's destination are CLOCK0, CLOCK1 and CLOCK2.

CLOCK0's out is P0.
CLOCK1's out is P1.
CLOCK2's out is P2.

P0's out are Q0, Q1, Q2, Q3 and Q4.
P1's out are Q0, Q1, Q2, Q3 and Q4.
P2's out are Q0, Q1, Q2, Q3 and Q4.

Q0's P0 is P0.
Q0's P1 is P1.
Q0's P2 is P2.

Q1's P0 is P0.
Q1's P1 is P1.
Q1's P2 is P2.

Q2's P0 is P0.
Q2's P1 is P1.
Q2's P2 is P2.

Q3's P0 is P0.
Q3's P1 is P1.
Q3's P2 is P2.

Q4's P0 is P0.
Q4's P1 is P1.
Q4's P2 is P2.

Q0's learners are L0 and L1.
Q1's learners are L0 and L1.
Q2's learners are L0 and L1.
Q3's learners are L0 and L1.
Q4's learners are L0 and L1.

L0's out is console_printer.
L1's out is console_printer.
