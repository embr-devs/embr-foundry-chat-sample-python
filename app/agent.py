"""Agent factory.

The agent is orchestrated *locally* inside this Embr-hosted app using Microsoft
Agent Framework. The only thing that reaches out to Foundry is the LLM inference
call — the agent loop, instructions, tool definitions, and conversation state
all live in this process.
"""

from __future__ import annotations

import os
from functools import lru_cache
from random import randint
from typing import Annotated

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient
from pydantic import Field

SYSTEM_INSTRUCTIONS = """You are a friendly demo assistant running inside an
Embr-hosted Python app. Your language model is served by a deployment in an
Azure AI Foundry project, but you (the agent) are orchestrated by Microsoft
Agent Framework inside the app's own process — so you can call local tools.

When asked about the weather or the current time in a city, use the provided
tools. Keep answers short and conversational.
""".strip()


def get_weather(
    location: Annotated[str, Field(description="City name, e.g. 'Seattle'.")],
) -> str:
    """Return a (fake) current weather report for demo purposes."""
    conditions = ["sunny", "cloudy", "rainy", "windy", "snowy"]
    temp = randint(-5, 35)
    return f"Weather in {location}: {conditions[randint(0, len(conditions) - 1)]}, {temp}°C."


def roll_dice(
    sides: Annotated[int, Field(description="Number of sides on the die.", ge=2, le=100)] = 6,
) -> str:
    """Roll a die with the given number of sides."""
    return f"Rolled a {randint(1, sides)} on a {sides}-sided die."


def _build_client() -> OpenAIChatClient:
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    model = os.environ.get("AZURE_OPENAI_MODEL", "gpt-4o-mini")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")

    if not endpoint or not api_key:
        raise RuntimeError(
            "Missing Foundry model configuration. Set AZURE_OPENAI_ENDPOINT and "
            "AZURE_OPENAI_API_KEY (see README → Foundry portal setup)."
        )

    return OpenAIChatClient(
        azure_endpoint=endpoint,
        api_key=api_key,
        model=model,
        api_version=api_version,
    )


@lru_cache(maxsize=1)
def get_agent() -> Agent:
    return Agent(
        client=_build_client(),
        instructions=SYSTEM_INSTRUCTIONS,
        tools=[get_weather, roll_dice],
    )
