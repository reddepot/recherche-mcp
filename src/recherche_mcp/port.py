"""Façade abstraction maison — port hexagonal pour découpler du SDK MCP.

Permet de remplacer FastMCP par un autre SDK MCP (officiel ou autre) sans
toucher au code métier. Conformément au principe Capability-Context Separation
(GLM 4.6, ADR 2026-05-08).

Implémentation Phase A : FastMCPAdapter (POLYLENS CONV-1 P0 fix).
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
        description: str = "",
    ) -> None: ...

    @abstractmethod
    def run(self, transport: str = "stdio") -> None: ...


class FastMCPAdapter(MCPServerPort):
    """Adapter FastMCP → MCPServerPort.

    Découple le code métier (server.py) du SDK FastMCP. Si breaking changes
    pré-1.0 dans FastMCP ou migration vers SDK officiel mcp 1.x, seul cet
    adapter doit être modifié.
    """

    def __init__(self, name: str, instructions: str = ""):
        # Import local pour ne pas charger FastMCP côté code métier
        from fastmcp import FastMCP

        self._mcp = FastMCP(name=name, instructions=instructions)

    @property
    def native(self):
        """Accès à l'instance FastMCP sous-jacente (pour `@mcp.tool()` legacy)."""
        return self._mcp

    def register_tool(
        self,
        name: str,
        handler: Callable[..., Any],
        description: str = "",
    ) -> None:
        """Enregistre un tool MCP via le décorateur FastMCP."""
        self._mcp.tool(name=name, description=description or handler.__doc__)(handler)

    def run(self, transport: str = "stdio") -> None:
        """Lance le serveur sur le transport indiqué."""
        self._mcp.run(transport=transport)
