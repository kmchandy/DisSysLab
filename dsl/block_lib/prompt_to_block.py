from typing import Optional, Union
from dsl.core import SimpleAgent


class PromptToBlock(SimpleAgent):
    """
Name: PromptToBlock

Summary:
A block that wraps an LLM prompt. The block receives messages on the
block's inport 'in' and sends the model's response to the messages
on the block's outport 'out'.

Parameters:
- name: Optional name for the block.
- description: Optional description.
- prompt: A string prompt to be sent to the model.
- model: The OpenAI model to use (e.g., "gpt-3.5-turbo").
- temperature: Sampling temperature (default 0.7).

Behavior:
- Receives a message on "in" (can be used to trigger the prompt).
- Sends the specified prompt to the LLM.
- Emits the model's response on the "out" port.

Use Cases:
- LLM-based tasks like summarization, rephrasing, classification.
- Easily configurable natural language blocks for various pipelines.

Example:
>>> prompt = "You are a helpful assistant. Summarize the user's message."
>>> block = WrapPrompt(prompt=prompt, model="gpt-3.5-turbo")

Tags: LLM, transformer, GPT, prompt, stream
    """

    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        prompt: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
    ):
        if prompt is None:
            raise ValueError("WrapPrompt requires a prompt.")

        self.prompt = prompt
        self.model = model
        self.temperature = temperature
        self.client = get_openai_client()

        def handle_msg(agent, msg):
            try:
                response = agent.client.chat.completions.create(
                    model=agent.model,
                    messages=[{"role": "user", "content": agent.prompt}],
                    temperature=agent.temperature
                )
                reply = response.choices[0].message.content.strip()
                agent.send(reply, "out")
            except Exception as e:
                print(f"❌ WrapPrompt error: {e}")
                agent.send("__STOP__", "out")

        super().__init__(
            name=name or "WrapPrompt",
            description=description or f"LLM prompt block: {prompt[:40]}...",
            inport="in",
            outports=["out"],
            handle_msg=handle_msg,
        )
