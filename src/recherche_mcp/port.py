"""Façade abstraction maison — port hexagonal pour découpler du SDK MCP.

Permet de remplacer FastMCP par un autre SDK MCP (officiel ou autre) sans
toucher au code métier. Conformément au principe Capability-Context Separation
(GLM 4.6, ADR 2026-05-08).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable


class MCPServerPort(ABC):
    """Port: ce que le métier attend du serveur MCP, indépendant du SDK."""

    @abstractmethod
    def register_tool(
        self,
        name: str,
        handler: Callable[..., Any],
        description: str,
    ) -> None: ...

    @abstractmethod
    def register_resource(self, uri: str, handler: Callable[..., Any]) -> None: ...

    @abstractmethod
    def run(self, transport: str = "stdio") -> None: ...
