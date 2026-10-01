# Office: paxos

# DRAFT -- for review.
#
# Three proposers and five acceptors, the agents of figure 1 of
# course/lecture_08.html. Every proposer has one outbox per acceptor and
# every acceptor has one outbox per proposer, so a reply reaches only the
# proposer that asked for it: thirty connections, one outbox to one inbox,
# exactly as the figure draws them.
#
# A majority of five acceptors is three, which is the `majority=3` below.
#
# Each acceptor also has one outbox per learner, and tells both learners
# the pair it holds whenever that pair changes.

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

P0's to_q0 is Q0.
P0's to_q1 is Q1.
P0's to_q2 is Q2.
P0's to_q3 is Q3.
P0's to_q4 is Q4.

P1's to_q0 is Q0.
P1's to_q1 is Q1.
P1's to_q2 is Q2.
P1's to_q3 is Q3.
P1's to_q4 is Q4.

P2's to_q0 is Q0.
P2's to_q1 is Q1.
P2's to_q2 is Q2.
P2's to_q3 is Q3.
P2's to_q4 is Q4.

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

Q0's to_l0 is L0.
Q0's to_l1 is L1.
Q1's to_l0 is L0.
Q1's to_l1 is L1.
Q2's to_l0 is L0.
Q2's to_l1 is L1.
Q3's to_l0 is L0.
Q3's to_l1 is L1.
Q4's to_l0 is L0.
Q4's to_l1 is L1.

L0's out is console_printer.
L1's out is console_printer.
