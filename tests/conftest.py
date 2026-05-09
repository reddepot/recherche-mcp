"""Fixtures pytest partagées."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
import yaml

from recherche_mcp.dispatch import DispatchMatrix
from recherche_mcp.models import Domain, Question


@pytest.fixture(autouse=True)
def reset_dispatch_singleton():
    """Avant chaque test, reset le singleton DispatchMatrix."""
    DispatchMatrix.reset()
    yield
    DispatchMatrix.reset()


@pytest.fixture
def question_clinique() -> Question:
    return Question(
        text=(
            "Quelle est la prévalence du burnout chez les médecins du travail "
            "libéraux en France 2024-2026, et quels outils de prévention validés "
            "sont opérationnalisables en cabinet pluri-praticien ?"
        ),
        domain=Domain.CLINIQUE,
    )


@pytest.fixture
def cases_fixture() -> list[dict]:
    path = Path(__file__).parent / "fixtures" / "cases.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))["cases"]


@pytest.fixture
def tmp_dispatch_yaml(tmp_path):
    """Crée un dispatch_matrix.yaml temporaire pour tests."""
    content = {
        "clinique": [
            {
                "name": "perplexity-deep-research",
                "rationale": "Test fixture",
                "invocation": "auto",
                "priority": 1,
            }
        ],
        "mixte": [
            {
                "name": "anthropic-claude-web-search",
                "rationale": "Test fallback",
                "invocation": "auto",
                "priority": 1,
            }
        ],
    }
    p = tmp_path / "dispatch.yaml"
    p.write_text(yaml.safe_dump(content), encoding="utf-8")
    return p
