"""Filtre anti-PII pour logs (Q3 décision user 2026-05-09).

Phase A : regex basique pour patterns français évidents.
Phase B : NER + classifier + audit séparé.
"""

from __future__ import annotations

import re

# Patterns FR : NIR (Sécu Soc), date naissance, téléphone, email
_NIR_PATTERN = re.compile(
    r"\b[12]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}\b"
)
_DATE_BIRTH_PATTERN = re.compile(
    r"\b(?:0?[1-9]|[12]\d|3[01])[\s/.\-](?:0?[1-9]|1[0-2])[\s/.\-](?:19|20)\d{2}\b"
)
_PHONE_FR_PATTERN = re.compile(
    r"\b(?:0|\+33\s?)[1-9](?:[\s.\-]?\d{2}){4}\b"
)
_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)


def redact_pii(text: str) -> str:
    """Caviarde les PII évidentes en français.

    Limitations Phase A :
    - Pas de détection NER de noms propres (faux positifs trop nombreux)
    - Patterns regex uniquement, ne couvre pas tous les cas
    - Doit être complété par anti-PII NLP en Phase B

    Returns:
        Texte avec PII remplacées par [REDACTED-{type}].
    """
    text = _NIR_PATTERN.sub("[REDACTED-NIR]", text)
    text = _DATE_BIRTH_PATTERN.sub("[REDACTED-DATE]", text)
    text = _PHONE_FR_PATTERN.sub("[REDACTED-TEL]", text)
    text = _EMAIL_PATTERN.sub("[REDACTED-EMAIL]", text)
    return text


def has_potential_pii(text: str) -> bool:
    """Heuristique : True si un pattern PII est détecté."""
    return any(
        p.search(text)
        for p in (_NIR_PATTERN, _DATE_BIRTH_PATTERN, _PHONE_FR_PATTERN, _EMAIL_PATTERN)
    )
