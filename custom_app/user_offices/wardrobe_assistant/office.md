---
description: Personal wardrobe assistant that creates outfits from your clothes
---

# Office: wardrobe_assistant

Sources: console_input(prompt="What's the occasion? > ", default_message="going to class then admissions office shift")
Sinks: console_printer

Agents:
Stylist is a stylist.

Connections:
console_input's destination is Stylist.
Stylist's outfit is console_printer.
