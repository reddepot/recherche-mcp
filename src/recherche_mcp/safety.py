"""Filtre anti-PII pour logs (Q3 décision user 2026-05-09).

Phase A v0.3 (post-audit externe 4 voix) : regex étendus pour usage médecin
du travail français — NIR (avec INIR neutre 3/4), Corse 2A/2B, IPP, RPPS,
ADELI, FINESS, SIRET, IBAN, noms propres avec contexte.

Phase B : NER + classifier + audit séparé.

Limitations connues et documentées :
- Les regex sont volontairement permissifs (accept séparateurs variés . - / espace)
- Faux positifs acceptés sur SIRET/IBAN car contexte médical les côtoie rarement
- Détection de noms propres heuristique (préfixe + capitalisation) — Phase B = NER

Référence : INIR neutre [Décret n°2024-1021](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000050039341),
Ameli https://www.ameli.fr/assure/droits-demarches/principes/numero-securite-sociale.
"""

from __future__ import annotations

import re

# ============================================================================
# Patterns FR — étendus post audit externe 2026-05-09
# ============================================================================

# NIR : sexe(1)+année(2)+mois(2)+département(2 ou 2A/2B Corse)+commune(3)+ordre(3)+clé(2)
# Audit Kimi : INIR neutre (sexe 3/4) prévu décret 2024-1021 → pattern [1-4]
_SEP = r"[\s.\-]?"  # séparateurs courants : espace, point, tiret
_NIR_PATTERN = re.compile(
    rf"\b[1-4]{_SEP}\d{{2}}{_SEP}\d{{2}}{_SEP}(?:\d{{2}}|2[AB]){_SEP}"
    rf"\d{{3}}{_SEP}\d{{3}}{_SEP}\d{{2}}\b"
)

# Date naissance FR/EN : 15/03/1985, 15-03-1985, 15.03.1985, 1985-03-15
_DATE_BIRTH_PATTERN = re.compile(
    r"\b(?:0?[1-9]|[12]\d|3[01])[\s/.\-](?:0?[1-9]|1[0-2])[\s/.\-](?:19|20)\d{2}\b"
    r"|"
    r"\b(?:19|20)\d{2}[\s/.\-](?:0?[1-9]|1[0-2])[\s/.\-](?:0?[1-9]|[12]\d|3[01])\b"
)

# Téléphone FR : 0X XX XX XX XX, +33 X XX XX XX XX, séparateurs variés
_PHONE_FR_PATTERN = re.compile(
    r"(?:^|(?<=\s))(?:0[1-9](?:[\s.\-]?\d{2}){4}|"
    r"\+33\s?[1-9](?:[\s.\-]?\d{2}){4})\b"
)

# Email
_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)

# RPPS (Répertoire Partagé des Professionnels de Santé) : 11 chiffres
# Pattern précis avec contexte mot-clé pour éviter faux positifs (audit Kimi)
_RPPS_PATTERN = re.compile(
    r"\bRPPS\s*:?\s*(\d{11})\b", re.IGNORECASE
)

# ADELI (Automatisation DES LIstes) : 9 chiffres, identifiant ancien des professionnels
_ADELI_PATTERN = re.compile(
    r"\bADELI\s*:?\s*(\d{9})\b", re.IGNORECASE
)

# FINESS (FIchier National des Etablissements Sanitaires et Sociaux) : 9 chiffres
_FINESS_PATTERN = re.compile(
    r"\bFINESS\s*:?\s*(\d{9})\b", re.IGNORECASE
)

# IPP (Identifiant Patient Permanent) : variable selon hôpital, 8-12 chiffres
_IPP_PATTERN = re.compile(
    r"\bIPP\s*:?\s*(\d{8,12})\b", re.IGNORECASE
)

# SIRET : 14 chiffres (numéro d'identification entreprise)
_SIRET_PATTERN = re.compile(
    r"\bSIRET\s*:?\s*(\d{14})\b|\b(\d{3}\s?\d{3}\s?\d{3}\s?\d{5})\b", re.IGNORECASE
)

# IBAN : FR + 25 caractères (lettres+chiffres). Pattern simplifié.
_IBAN_PATTERN = re.compile(
    r"\bFR\d{2}[\s]?[A-Z0-9]{4}[\s]?[A-Z0-9]{4}[\s]?[A-Z0-9]{4}"
    r"[\s]?[A-Z0-9]{4}[\s]?[A-Z0-9]{4}[\s]?\d{3}\b", re.IGNORECASE
)

# Noms propres avec contexte : "M./Mme/Dr./Pr. Nom" — heuristique simple
# Capitalisation requise après le titre.
_NAME_WITH_TITLE_PATTERN = re.compile(
    r"\b(?:M(?:r|me|onsieur|adame|lle|aître)?|Dr|Pr|Prof|Me)\.?\s+"
    r"[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ\-']+(?:\s+[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ\-']+)?\b"
)

# Trigger lexical "né(e) le", "naissance" — flag d'alerte fort
_BIRTH_TRIGGER_PATTERN = re.compile(
    r"\bné(?:e|es?)?\s+le\b|\bnaissance\s*:?\s*", re.IGNORECASE
)


def redact_pii(text: str) -> str:
    """Caviarde les PII en français avec patterns étendus médicaux.

    Ordre de redaction important : patterns les plus spécifiques d'abord
    (RPPS, ADELI, FINESS) avant les patterns génériques (chiffres dans NIR).

    Limitations Phase A :
    - Pas de NER pour noms propres sans titre (faux positifs trop nombreux)
    - SIRET sans contexte = chiffres seuls, peut être confondu avec NIR
    - Phase B : NER + classifier ML

    Returns:
        Texte avec PII remplacées par [REDACTED-{type}].
    """
    text = _RPPS_PATTERN.sub("RPPS:[REDACTED-RPPS]", text)
    text = _ADELI_PATTERN.sub("ADELI:[REDACTED-ADELI]", text)
    text = _FINESS_PATTERN.sub("FINESS:[REDACTED-FINESS]", text)
    text = _IPP_PATTERN.sub("IPP:[REDACTED-IPP]", text)
    text = _SIRET_PATTERN.sub("[REDACTED-SIRET]", text)
    text = _IBAN_PATTERN.sub("[REDACTED-IBAN]", text)
    text = _NIR_PATTERN.sub("[REDACTED-NIR]", text)
    text = _DATE_BIRTH_PATTERN.sub("[REDACTED-DATE]", text)
    text = _PHONE_FR_PATTERN.sub("[REDACTED-TEL]", text)
    text = _EMAIL_PATTERN.sub("[REDACTED-EMAIL]", text)
    text = _NAME_WITH_TITLE_PATTERN.sub("[REDACTED-NAME]", text)
    return text


def has_potential_pii(text: str) -> bool:
    """Heuristique : True si un pattern PII OU un trigger naissance détecté."""
    return any(
        p.search(text)
        for p in (
            _NIR_PATTERN,
            _DATE_BIRTH_PATTERN,
            _PHONE_FR_PATTERN,
            _EMAIL_PATTERN,
            _RPPS_PATTERN,
            _ADELI_PATTERN,
            _FINESS_PATTERN,
            _IPP_PATTERN,
            _SIRET_PATTERN,
            _IBAN_PATTERN,
            _NAME_WITH_TITLE_PATTERN,
            _BIRTH_TRIGGER_PATTERN,
        )
    )
