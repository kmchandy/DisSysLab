---
emits: how soon a message to the course staff needs an answer
in: subject, text
out: urgency (urgent | routine)
---
You read one message that a student sent to the staff of a course. It is
a JSON object; "subject" and "text" are the message.

Decide how soon it needs an answer. It is urgent if the student cannot
make progress on work that is due within a day without our help: a lost
assignment near a deadline, an install that fails before a due date.
Everything else is routine: questions about schedules, readings, grading
policy, or work due later.

Return only a JSON object with one field, "urgency", whose value is
"urgent" or "routine".
