[**Wardrobe Assistant**]

> **Current DisSysLab implementation** uses **uploaded reference photos** (`media/uploads/…`) via `wardrobe_inventory.json` (`photo_media`). **Flat-sketch / vector-style garment art** is not generated in-app (deferred until a dedicated image model pipeline exists). Product paragraphs below still describe the longer-term vision.

> **DSL office (implemented):** `custom_app/user_offices/wardrobe_assistant/` — calendar + NOAA weather → wardrobe-grounded outfits → situation display, JSONL archive, Gmail. Scaffold for the standalone SPA: repo root [`wardrobe_assistant/README.md`](../wardrobe_assistant/README.md).

> **Standalone SPA (`wardrobe_assistant/`):** Delivers **tabs** for occasion chat (no calendar), clean/worn stacks + launder, outfit pick history, blind + photo shopping assist, plus Run for the calendar DSL office. Editing `wardrobe_inventory.json` / roles is still easiest from the **Custom App**. **Sketch generation + auto photo→catalog + history→calendar RAG** remain future work ([`WARDROBE_STYLIST_IMPLEMENTATION_PLAN.md`](docs/WARDROBE_STYLIST_IMPLEMENTATION_PLAN.md)).

**Detailed status + phased plan:** [docs/WARDROBE_STYLIST_IMPLEMENTATION_PLAN.md](docs/WARDROBE_STYLIST_IMPLEMENTATION_PLAN.md)

This is a system of agents that do a couple of things:
    - monitor your calendar for upcoming events
    - For each event, get information on date, get weather details about 
    - the time and place if it is provided (otherwise default to pasadena CA)
    - then using the information on weather and event type:
        - the office should have access to a wardrobe.....which is basically gotten 
        - as input from the user, in terms of text description of all the clothes that the user has
        - or pictures:
        The wardrobe:
            - The user either input text description or list of the clothes they have via the chatbot in the react app
            - The user can also just upload pictures of all their clothes: the agents process the images, then make a list
            of all the clothes uploaded, 
            - For every clothes in the wardrobe, either uploaded by text or as images, the agents will generate a 2d representation
            of each clothing item (flat sketches like figures, can be .pngs) to represent them (so no storing the original pictures, 
            just these generated flat sketches), which will be associated with the text description of each clothing in the wardrobe 
            storage.
    - Now since we have a wardrobe, we use information on weather, event type and date, to have the agents suggest an outfit from the
    wardrobe for the user to wear, then in the react app, it will use the flat sketches to show how the outfit would look.
    - for outfit layouts with flat sketches, always have the top/shirt at the top and the bottom directly below the top, e.g. the trousers shorts, e.t.c.
    - if you have multiple things for the top e.g. a t-shirt and a jacket, you would want to put all the top items in the same row in the order you'd wear them, them all the bottoms in the same row in the order you'd wear them. 
    - So after processing the outfit for each event, the office would display it on the screen i nthe react app, and send an email of the outfit and layout to the user email.

Now this is the primary pipeline.

[***The above items have to be implemented in the user_offices office wardrobe_assistant, it is like calendar stylist but with more functionality.....edit wardrobe_assistant to implement all the above functions....you can scrap it and start from scratch...but do see how it handles images currently as a starting point, and also do see calendar_stylist for reading events, weather and all that stuff ***]

[***Now for the below stuff, we are going to create a separater folder in disysyslab, called wardrobe_assistant, this will be a separate full_stack react app running on it's own, just like an extension of the wardrobe assistant office, it should be able to do all the above, and then extend with the functionalities below ***]

Secondary tasks include:
We want for this office other buttons on the diplay screen that do different things:
- regular outfit generation without having to fetch events, ....... so like the user has a chat section just below the display where they are being asked, what type of event they are going to, and after they say, a couple (1-3) outfit suggestions are displayed, and the user has the option to pick which one they picked.......
- once an outfit is picked, the office will update the wardrobe database....oh yeah the wardrobe should keep track of all the clothes that were worn and those that are still clean.....and should have the option to readd clothes to the clean stack once they are laundered.
- it would be nice also if on the display the system could show the clean stack and the worn stack....and give the user to reuse clothes, with a custom amount of wearing for each item custom set by the user e.g. jeans can be worn 5 times before being moved to the dirt pile, 
- also keeping track of outfits worn in the past would be great....could even use them for future suggestions.....
- another functioanlity would be helping the user buy clothes.....to add to the wardrobe:
    - blind suggestion would be the agents just blindly telling the user what things would be great editions to their wardrobe
    based on their style and based on the current wardrobe depending on how they would create nicer ooutfits with already existing clothing items
    - if the user is contemplating buying different items, they could upload images and get suggestions on weather or not they would be a gret addition to the wardrobe based on weather similar items already exist, or if the items to be added would go great with already existing clothing items.