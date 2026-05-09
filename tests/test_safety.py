"""Tests filtre anti-PII (POLYLENS Kimi P1 — couverture safety.py)."""

from __future__ import annotations

import pytest

from recherche_mcp.safety import has_potential_pii, redact_pii


@pytest.mark.unit
class TestRedactNIR:
    """NIR français = sexe(1) + année(2) + mois(2) + dpt(2) + commune(3) + ordre(3) + clé(2) = 15 chiffres."""

    @pytest.mark.parametrize(
        "text,expected_redacted",
        [
            ("Salarié 1 85 04 75 114 080 12", True),
            ("NIR: 285047511408012", True),
            ("Madame 2 90 12 33 156 234 67", True),
        ],
    )
    def test_nir_detected(self, text: str, expected_redacted: bool):
        assert has_potential_pii(text) == expected_redacted
        if expected_redacted:
            assert "[REDACTED-NIR]" in redact_pii(text)

    def test_nir_not_false_positive_on_short_numbers(self):
        text = "Le numéro 12345 n'est pas un NIR"
        assert "[REDACTED-NIR]" not in redact_pii(text)


@pytest.mark.unit
class TestRedactDateBirth:
    @pytest.mark.parametrize(
        "text",
        [
            "Né le 15/03/1985",
            "Born 03-12-1990",
            "Date naissance 5.11.1972",
            "Le 1 1 2000",
        ],
    )
    def test_date_birth_detected(self, text: str):
        out = redact_pii(text)
        assert "[REDACTED-DATE]" in out

    def test_date_recent_not_year_only(self):
        text = "L'année 2024 est intéressante"
        assert "[REDACTED-DATE]" not in redact_pii(text)


@pytest.mark.unit
class TestRedactPhoneFR:
    @pytest.mark.parametrize(
        "text",
        [
            "Tel: 06 12 34 56 78",
            "Appeler 0123456789",
            "+33 6 12 34 56 78",
            "Fax 04.78.50.12.34",
        ],
    )
    def test_phone_fr_detected(self, text: str):
        out = redact_pii(text)
        assert "[REDACTED-TEL]" in out


@pytest.mark.unit
class TestRedactEmail:
    @pytest.mark.parametrize(
        "text",
        [
            "Contact: jean.dupont@example.com",
            "Mail to user+test@sub.domain.fr",
            "redtech@protonmail.com",
        ],
    )
    def test_email_detected(self, text: str):
        out = redact_pii(text)
        assert "[REDACTED-EMAIL]" in out


@pytest.mark.unit
class TestRedactCombined:
    def test_multiple_pii_in_same_text(self):
        text = (
            "Patient né le 15/03/1985, NIR 1 85 04 75 114 080 12, "
            "tél 0612345678, mail test@example.com"
        )
        out = redact_pii(text)
        assert "[REDACTED-DATE]" in out
        assert "[REDACTED-NIR]" in out
        assert "[REDACTED-TEL]" in out
        assert "[REDACTED-EMAIL]" in out

    def test_text_without_pii_unchanged(self):
        text = "Recherche bibliographique sur la SST 2026"
        assert redact_pii(text) == text
        assert not has_potential_pii(text)

    def test_redact_idempotent(self):
        """redact_pii(redact_pii(x)) == redact_pii(x) (Kimi P2)."""
        text = "Mail: test@example.com et tel 0612345678"
        once = redact_pii(text)
        twice = redact_pii(once)
        assert once == twice
