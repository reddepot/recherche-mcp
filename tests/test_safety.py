"""Tests filtre anti-PII pour `safety.py`."""

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
            "user@example.com",
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
        """`redact_pii(redact_pii(x)) == redact_pii(x)` — applications répétées sûres."""
        text = "Mail: test@example.com et tel 0612345678"
        once = redact_pii(text)
        twice = redact_pii(once)
        assert once == twice


# Tests des extensions PII médicales : RPPS, ADELI, FINESS, IPP, SIRET, IBAN,
# noms avec titre, NIR Corse 2A/2B, NIR sexe 1-4 (anticipation INIR neutre).


@pytest.mark.unit
class TestRedactRPPS:
    def test_rpps_with_keyword(self):
        out = redact_pii("Médecin RPPS 12345678901 référent SST")
        assert "[REDACTED-RPPS]" in out
        assert "12345678901" not in out

    def test_rpps_lowercase(self):
        out = redact_pii("rpps: 98765432109")
        assert "[REDACTED-RPPS]" in out

    def test_rpps_without_keyword_not_redacted(self):
        # 11 chiffres bruts sans contexte = pas RPPS détecté (acceptable)
        text = "Numéro 12345678901 sans contexte"
        out = redact_pii(text)
        assert "[REDACTED-RPPS]" not in out


@pytest.mark.unit
class TestRedactADELI:
    def test_adeli_with_keyword(self):
        out = redact_pii("Identifiant ADELI: 123456789")
        assert "[REDACTED-ADELI]" in out


@pytest.mark.unit
class TestRedactFINESS:
    def test_finess_with_keyword(self):
        out = redact_pii("Établissement FINESS 123456789")
        assert "[REDACTED-FINESS]" in out


@pytest.mark.unit
class TestRedactIPP:
    def test_ipp_with_keyword(self):
        out = redact_pii("Patient IPP: 12345678 admis le 03/2026")
        assert "[REDACTED-IPP]" in out

    def test_ipp_long_number(self):
        out = redact_pii("IPP 123456789012")
        assert "[REDACTED-IPP]" in out


@pytest.mark.unit
class TestRedactNIRExtended:
    def test_nir_corse_2a(self):
        """NIR avec département Corse 2A."""
        out = redact_pii("NIR 1 85 04 2A 114 080 12")
        assert "[REDACTED-NIR]" in out

    def test_nir_corse_2b(self):
        out = redact_pii("NIR 2 90 12 2B 156 234 67")
        assert "[REDACTED-NIR]" in out

    def test_nir_with_dots(self):
        """NIR avec séparateurs points (copy-paste dossier médical)."""
        out = redact_pii("Identifiant: 1.85.04.75.114.080.12")
        assert "[REDACTED-NIR]" in out

    def test_nir_with_dashes(self):
        out = redact_pii("NIR: 1-85-04-75-114-080-12")
        assert "[REDACTED-NIR]" in out

    def test_nir_inir_neutre_future(self):
        """INIR neutre (Décret 2024-1021) : sexe 3 ou 4."""
        out = redact_pii("INIR 3 85 04 75 114 080 12")
        assert "[REDACTED-NIR]" in out


@pytest.mark.unit
class TestRedactNameWithTitle:
    @pytest.mark.parametrize(
        "text",
        [
            "Mme Dupont, salariée chez ACME",
            "M. Martin a consulté",
            "Dr Durand a prescrit",
            "Pr Lefèvre est intervenu",
            "Madame Lemaître-Bernard a été reçue",
        ],
    )
    def test_name_with_title_redacted(self, text: str):
        out = redact_pii(text)
        assert "[REDACTED-NAME]" in out

    def test_name_without_title_not_redacted(self):
        # Phase A : pas de NER → noms sans titre passent (faux négatif assumé)
        text = "Dupont a consulté hier"
        out = redact_pii(text)
        # Acceptable Phase A — Phase B = NER pour résoudre


@pytest.mark.unit
class TestRedactSIRET:
    def test_siret_with_keyword(self):
        out = redact_pii("SIRET 12345678901234")
        assert "[REDACTED-SIRET]" in out

    def test_siret_with_spaces(self):
        out = redact_pii("Identifiant 123 456 789 01234")
        assert "[REDACTED-SIRET]" in out


@pytest.mark.unit
class TestRedactIBAN:
    def test_iban_fr(self):
        out = redact_pii("Compte FR76 1234 5678 9012 3456 7890 123")
        assert "[REDACTED-IBAN]" in out


@pytest.mark.unit
class TestPotentialPIIDetection:
    def test_birth_trigger_detected(self):
        """`né le` ou `naissance` triggers détection même sans date."""
        assert has_potential_pii("Salarié né le ...")
        assert has_potential_pii("Date de naissance: à préciser")
        assert has_potential_pii("Naissance précoce dans la famille")

    def test_no_pii_no_trigger(self):
        assert not has_potential_pii(
            "Quelle est la prévalence du burnout chez les médecins du travail ?"
        )
