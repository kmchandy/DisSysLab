# =================================================
#   EntityExtractor (regex. simple, not GPT)      |
# =================================================

class EntityExtractor(SimpleAgent):
    """
    Naive entity extractor:
    - Finds sequences of Capitalized Words as proxies for names/places.
    - Adds 'entities': {'people': [...], 'places': [...]} to the message.
    """

    PROPER_NOUN = _re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b")
    PLACE_HINTS = {"City", "County", "Province", "State",
                   "University", "Stadium", "Arena", "Park"}

    def __init__(self, name: Optional[str] = None):
        super().__init__(name=name or "EntityExtractor",
                         inport="in", outports=["out"],
                         handle_msg=self._handle)

    def _handle(self, agent, msg):
        try:
            if not isinstance(msg, dict):
                msg = {"text": str(msg)}
            text = str(msg.get("text", ""))
            cands = list({m.group(1) for m in self.PROPER_NOUN.finditer(text)})
            places = [c for c in cands if any(
                h in c.split() for h in self.PLACE_HINTS)]
            people = [c for c in cands if c not in places]
            out = dict(msg)
            out["entities"] = {"people": people, "places": places}
            agent.send(out, "out")
        except Exception as e:
            print(f"[EntityExtractor] Error: {e}")
