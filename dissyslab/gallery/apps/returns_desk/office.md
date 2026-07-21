# Office: returns_desk

Sources: starter
Sinks: jsonl_recorder(path='outcomes.jsonl'), console_printer

Agents:
TICKETS is a tickets.
SELECT is a select(inports=['ticket', 'manager_reply'], command='command').
CLERK is a clerk.
MANAGER is a manager.

Connections:
starter's destination is TICKETS.
TICKETS's out is SELECT's ticket.
MANAGER's out is SELECT's manager_reply.
SELECT's out is CLERK.
CLERK's to_manager is MANAGER.
CLERK's to_log are jsonl_recorder and console_printer.
CLERK's command is SELECT's command.
