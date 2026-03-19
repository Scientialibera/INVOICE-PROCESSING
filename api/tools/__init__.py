"""Auto-discovery of @tool-decorated functions for the agent framework."""
from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from typing import Callable

logger = logging.getLogger(__name__)


def discover_tools() -> list[Callable]:
    """Scan all modules in api/tools/ for functions decorated with @tool."""
    tools: list[Callable] = []
    package = importlib.import_module("api.tools")

    for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
        if modname.startswith("_"):
            continue
        module = importlib.import_module(f"api.tools.{modname}")
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            if hasattr(obj, "_is_tool") or hasattr(obj, "__tool_metadata__"):
                tools.append(obj)
                logger.info("Discovered tool: %s.%s", modname, name)

    logger.info("Total tools discovered: %d", len(tools))
    return tools
