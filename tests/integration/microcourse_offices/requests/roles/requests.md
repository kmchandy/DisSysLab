---
kind: author
in: text (text, at most 2000 chars)
out: vehicle (tahoe | silverado | equinox | trax | malibu)
---
You read one message a customer typed into a car dealership's chat.

List the cars on the lot that the customer asks about: Tahoe, Silverado,
Equinox, Trax, Malibu. Return only a JSON list with one object per car,
each with the field "vehicle", in lower case. Return [] if the customer
asks about none of them.
