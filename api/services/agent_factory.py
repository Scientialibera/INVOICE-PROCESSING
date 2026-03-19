"""Builds the SpendAnalyzer agent using the Microsoft Agent Framework."""
from __future__ import annotations

import logging
from functools import lru_cache

from azure.identity import DefaultAzureCredential

from agent_framework import AzureOpenAIAssistantsClient

from api.common.config import get_api_settings
from api.services.blob_gateway import load_system_prompt
from api.tools import discover_tools

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_client() -> AzureOpenAIAssistantsClient:
    s = get_api_settings()
    return AzureOpenAIAssistantsClient(
        credential=DefaultAzureCredential(),
        endpoint=s.AZURE_OPENAI_ENDPOINT,
        model=s.AZURE_OPENAI_DEPLOYMENT,
        api_version=s.AZURE_OPENAI_API_VERSION,
    )


def build_agent():
    """Create and configure the SpendAnalyzer agent with all tools."""
    s = get_api_settings()
    client = _get_client()

    system_prompt = load_system_prompt()
    tools = discover_tools()

    agent_tools = list(tools)

    if s.AGENT_ENABLE_CODE_INTERPRETER:
        agent_tools.append(client.get_code_interpreter_tool())

    agent = client.create_agent(
        name=s.AGENT_NAME,
        instructions=system_prompt,
        tools=agent_tools,
    )

    logger.info(
        "Agent built: name=%s, tools=%d (code_interpreter=%s)",
        s.AGENT_NAME,
        len(agent_tools),
        s.AGENT_ENABLE_CODE_INTERPRETER,
    )
    return agent, client
