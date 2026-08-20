# Office: adaptive_tutor

# Ports the tutoring app from the pre-DisSysLab prototype
# onto the current office.md/roles framework, and -- unlike that version --
# formalizes what varies between subjects into an explicit, documented
# contract (roles/_subject_common.py), the same way mac_speed_suite
# formalized MAC/Donchian/Turtle into a shared signal/backtest/evaluate
# contract. Three subjects run side by side to prove it: fractions,
# multiplication_facts, and telling_time. Adding a subject means writing one new
# generate_problem function + a role file that registers it -- PLANNER,
# CHECKER, and STUDENT's own code never changes (each subject gets its
# own instance of the same unmodified role file, exactly the way
# mac_speed_suite instantiates BACKTESTER nine separate times, once per
# strategy variant, rather than sharing one runtime instance across all
# nine).
#
# Scope, deliberately: one session per subject, sequential, no live
# terminal, no multi-student concurrency (STUDENT is a scripted stand-in
# -- see roles/scripted_student.py). Those are real, separate features
# already explored in tutor_multi.py; this office exists to prove the
# subject-extension contract, not to rebuild every feature of the
# original app.

Sources: session_starter(variant='easy'), session_starter_2(variant='hard'), session_starter_3(variant='easy')
Sinks: tutor_session_display

Agents:
BANK_FRACTIONS is a fractions_subject.
BANK_MULT is a multiplication_facts_subject.
BANK_TELLING_TIME is a telling_time_subject.
STUDENT_FRACTIONS is a scripted_student.
STUDENT_MULT is a scripted_student.
STUDENT_TELLING_TIME is a scripted_student.
CHECKER_FRACTIONS is a answer_checker.
CHECKER_MULT is a answer_checker.
CHECKER_TELLING_TIME is a answer_checker.
PLANNER_FRACTIONS is a tutor_planner(subject_name='fractions').
PLANNER_MULT is a tutor_planner(subject_name='multiplication_facts').
PLANNER_TELLING_TIME is a tutor_planner(subject_name='telling_time').

Connections:
session_starter's out is PLANNER_FRACTIONS's in_.
session_starter_2's out is PLANNER_MULT's in_.
session_starter_3's out is PLANNER_TELLING_TIME's in_.

PLANNER_FRACTIONS's to_bank is BANK_FRACTIONS's in_.
BANK_FRACTIONS's out is PLANNER_FRACTIONS's in_.
PLANNER_FRACTIONS's to_student is STUDENT_FRACTIONS's in_.
STUDENT_FRACTIONS's out is PLANNER_FRACTIONS's in_.
PLANNER_FRACTIONS's to_checker is CHECKER_FRACTIONS's in_.
CHECKER_FRACTIONS's out is PLANNER_FRACTIONS's in_.

PLANNER_MULT's to_bank is BANK_MULT's in_.
BANK_MULT's out is PLANNER_MULT's in_.
PLANNER_MULT's to_student is STUDENT_MULT's in_.
STUDENT_MULT's out is PLANNER_MULT's in_.
PLANNER_MULT's to_checker is CHECKER_MULT's in_.
CHECKER_MULT's out is PLANNER_MULT's in_.

PLANNER_TELLING_TIME's to_bank is BANK_TELLING_TIME's in_.
BANK_TELLING_TIME's out is PLANNER_TELLING_TIME's in_.
PLANNER_TELLING_TIME's to_student is STUDENT_TELLING_TIME's in_.
STUDENT_TELLING_TIME's out is PLANNER_TELLING_TIME's in_.
PLANNER_TELLING_TIME's to_checker is CHECKER_TELLING_TIME's in_.
CHECKER_TELLING_TIME's out is PLANNER_TELLING_TIME's in_.

PLANNER_FRACTIONS's report is tutor_session_display.
PLANNER_MULT's report is tutor_session_display.
PLANNER_TELLING_TIME's report is tutor_session_display.
