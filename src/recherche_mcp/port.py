"""Façade abstraction maison — port hexagonal pour découpler du SDK MCP.

Permet de remplacer FastMCP par un autre SDK MCP (officiel ou autre) sans
toucher au code métier. Conformément au principe Capability-Context Separation
(GLM 4.6, ADR 2026-05-08).

Audit externe 2026-05-09 (4 voix : ChatGPT/DeepSeek/Kimi/Grok) : précédente
implémentation exposait `.native` qui contournait l'abstraction (faux découplage).
**Cette version supprime `.native`** : le seul moyen d'enregistrer un tool est
`register_tool()`. Le code métier (server.py) ne touche jamais FastMCP directement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Literal


Transport = Literal["stdio", "sse", "streamable-http"]


class MCPServerPort(ABC):
    """Port: ce que le métier attend du serveur MCP, indépendant du SDK."""

    @abstractmethod
    def register_tool(
        self,
        name: str,
        handler: Callable[..., Any],
        description: str = "",
    ) -> None:
        """Enregistre un tool MCP avec son handler.

        Args:
            name: nom du tool exposé (snake_case recommandé).
            handler: fonction Python qui implémente le tool. Sa signature
                définit les paramètres MCP (type hints + Pydantic auto-parsing).
            description: description du tool (default : docstring du handler).
        """

    @abstractmethod
    def run(self, transport: Transport = "stdio") -> None:
        """Lance le serveur sur le transport indiqué."""


class FastMCPAdapter(MCPServerPort):
    """Adapter FastMCP → MCPServerPort.

    Découple le code métier (server.py) du SDK FastMCP. Si breaking changes
    pré-1.0 dans FastMCP ou migration vers SDK officiel mcp 1.x, seul cet
    adapter doit être modifié.

    Audit externe 2026-05-09 : `.native` retiré pour vrai découplage.
    """

    def __init__(self, name: str, instructions: str = ""):
        # Import local pour ne pas charger FastMCP côté code métier
        from fastmcp import FastMCP

        self._mcp = FastMCP(name=name, instructions=instructions)

    def register_tool(
        self,
        name: str,
        handler: Callable[..., Any],
        description: str = "",
    ) -> None:
        """Enregistre un tool MCP via le décorateur FastMCP en interne."""
        self._mcp.tool(name=name, description=description or (handler.__doc__ or ""))(
            handler
        )

    def run(self, transport: Transport = "stdio") -> None:
        """Lance le serveur sur le transport indiqué.

        Phase A : seul "stdio" est supporté en pratique. Streamable HTTP +
        OAuth réservé Phase B Sprint 5.
        """
        self._mcp.run(transport=transport)
