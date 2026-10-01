# Office: paxos

# DRAFT -- for review.
#
# Three proposers and five acceptors, the agents of figure 1 of
# course/lecture_08.html.
#
# A proposer sends the same read, and later the same write, to every
# acceptor, so it needs one outbox for all five. An acceptor's reply, on
# the other hand, goes to the proposer that asked and to nobody else, so
# an acceptor needs one outbox per proposer. It needs only one for the
# learners, because it tells them both the same thing.
#
# A majority of five acceptors is three, which is the `majority=3` below.

Sources: starter
Sinks:   console_printer

Agents:
CLOCK is a ticker(ticks=6, period=0.5).
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
starter's destination is CLOCK.

CLOCK's to_p0 is P0.
CLOCK's to_p1 is P1.
CLOCK's to_p2 is P2.

P0's out are Q0, Q1, Q2, Q3 and Q4.
P1's out are Q0, Q1, Q2, Q3 and Q4.
P2's out are Q0, Q1, Q2, Q3 and Q4.

Q0's to_p0 is P0.
Q0's to_p1 is P1.
Q0's to_p2 is P2.

Q1's to_p0 is P0.
Q1's to_p1 is P1.
Q1's to_p2 is P2.

Q2's to_p0 is P0.
Q2's to_p1 is P1.
Q2's to_p2 is P2.

Q3's to_p0 is P0.
Q3's to_p1 is P1.
Q3's to_p2 is P2.

Q4's to_p0 is P0.
Q4's to_p1 is P1.
Q4's to_p2 is P2.

Q0's to_learners are L0 and L1.
Q1's to_learners are L0 and L1.
Q2's to_learners are L0 and L1.
Q3's to_learners are L0 and L1.
Q4's to_learners are L0 and L1.

L0's out is console_printer.
L1's out is console_printer.
