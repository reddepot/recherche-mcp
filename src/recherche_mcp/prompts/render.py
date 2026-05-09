"""Rendu Jinja2 des templates par domaine pour générer les sous-prompts experts."""

from __future__ import annotations

from pathlib import Path

import jinja2

from ..models import ResearchPlan

# Autoescape sélectif sur formats HTML/XML (anti-XSS pour rendus futurs).
# Templates .j2 et .md restent non-escaped (sortie texte brut).
ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(Path(__file__).parent)),
    autoescape=jinja2.select_autoescape(
        enabled_extensions=("html", "htm", "xml"),
        default_for_string=False,
    ),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _extract_axis_label(text: str) -> str:
    """Extrait l'axe entre crochets en début de sous-Q."""
    if text.startswith("[") and "]" in text:
        return text.split("]", 1)[0].lstrip("[").strip()
    return "axe-générique"


def render_subprompts(plan: ResearchPlan) -> list[dict]:
    """Pour chaque sous-question, rend un prompt expert via le template du domaine.

    Returns:
        Liste de dicts {sub_question_id, prompt} prêts à être copiés-collés
        vers les modèles candidats annoncés par dispatch.
    """
    out = []
    for sq in plan.sub_questions:
        tpl_name = f"domain_{sq.domain_hint.value}.j2"
        try:
            tpl = ENV.get_template(tpl_name)
        except jinja2.TemplateNotFound:
            tpl = ENV.get_template("domain_mixte.j2")
        body = tpl.render(
            parent_question=plan.question.text,
            sub_question=sq.text,
            axis_label=_extract_axis_label(sq.text),
            rationale=sq.rationale,
            confidence=sq.confidence,
            domain=sq.domain_hint.value,
        )
        out.append({"sub_question_id": str(sq.id), "prompt": body})
    return out
