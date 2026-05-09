#!/usr/bin/env python3
"""Notification quand le seuil d'usage déclencheur de décision est atteint.

Lit le journal usage JSONL, compte les events, et envoie un email si :
- Seuil "early signal" (15 par défaut) atteint pour la première fois
- Seuil "GO Phase B" (30 par défaut) atteint pour la première fois

Usage :
    python scripts/threshold_alert.py              # vérifie + envoie si seuil
    python scripts/threshold_alert.py --dry-run    # vérifie + affiche sans envoyer
    python scripts/threshold_alert.py --force      # ré-envoie même si déjà alerté

Configuration SMTP via variables d'environnement (cohérent alert_health.py
de mcp_meddata) :
    ALERT_SMTP_HOST   (default: ssl0.ovh.net — serveur OVH Zimbra)
    ALERT_SMTP_PORT   (default: 587)
    ALERT_SMTP_USER   (default: redbot@reddie.ovh)
    ALERT_SMTP_PASS   (mot de passe Zimbra — OBLIGATOIRE pour envoi)
    ALERT_MAIL_TO     (default: redtech@protonmail.com)

Le fichier `~/.config/recherche-mcp/smtp.env` (chmod 600) est lu automatiquement
si présent (format dotenv). Sinon, exporter les variables avant exécution.

Exit codes :
    0  Aucune alerte (seuil pas atteint OU déjà alerté)
    1  Alerte envoyée
    2  Configuration SMTP manquante (--send requis mais ALERT_SMTP_PASS absent)
    3  Erreur réseau / SMTP
    4  Pas de events (runs/ vide)
"""

from __future__ import annotations

import argparse
import logging
import os
import smtplib
import sys
from collections import Counter
from email.message import EmailMessage
from pathlib import Path

# Permet usage en script standalone : ajout src/ au path
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from recherche_mcp import usage  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger("threshold_alert")


# ============================================================================
# Seuils
# ============================================================================

THRESHOLDS = {
    "early_signal": {
        "count": 15,
        "subject": "[recherche-mcp] Premier signal — 15 recherches enregistrées",
        "intro": (
            "Le journal usage du skill `/recherche` atteint 15 invocations. "
            "C'est le premier palier qui permet de repérer des patterns "
            "récurrents (≥3 par domaine en moyenne). Pas encore le seuil "
            "GO Phase B mais utile pour ajustement précoce si besoin."
        ),
    },
    "go_phase_b": {
        "count": 30,
        "subject": "[recherche-mcp] ✅ Seuil GO Phase B atteint — 30 recherches",
        "intro": (
            "Le journal usage du skill `/recherche` atteint 30 invocations.\n"
            "C'est le seuil qui aligne :\n"
            "- DSPY_GATE condition (a) : ≥30 décompositions notées\n"
            "- Test Wilcoxon signé apparié Linear vs Graph statistiquement valide\n"
            "- DEVCODE-Vote possible sur poids quality_weights\n\n"
            "→ Décision GO/NO-GO Phase B (γ-α dispatch auto, 25-40 j-h) "
            "peut être prise sur base empirique."
        ),
    },
}


# ============================================================================
# Email
# ============================================================================

def _load_smtp_env() -> None:
    """Charge `~/.config/recherche-mcp/smtp.env` si présent (format dotenv)."""
    cfg = Path.home() / ".config" / "recherche-mcp" / "smtp.env"
    if not cfg.exists():
        return
    for line in cfg.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _build_email(subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("ALERT_SMTP_USER", "redbot@reddie.ovh")
    msg["To"] = os.environ.get("ALERT_MAIL_TO", "redtech@protonmail.com")
    msg.set_content(body)
    return msg


def _send_email(msg: EmailMessage) -> None:
    host = os.environ.get("ALERT_SMTP_HOST", "ssl0.ovh.net")
    port = int(os.environ.get("ALERT_SMTP_PORT", "587"))
    user = os.environ["ALERT_SMTP_USER"]
    password = os.environ["ALERT_SMTP_PASS"]

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)


# ============================================================================
# Logique principale
# ============================================================================

def _alert_marker_path(threshold_key: str) -> Path:
    """`runs/.alert_sent_<key>` — marqueur d'envoi déjà effectué."""
    runs_dir = usage._runs_dir()
    return runs_dir / f".alert_sent_{threshold_key}"


def _build_body(threshold_key: str, count: int, by_domain: dict) -> str:
    cfg = THRESHOLDS[threshold_key]
    domain_lines = "\n".join(
        f"  - {d:18s} : {n}" for d, n in sorted(by_domain.items())
    )
    return f"""\
{cfg['intro']}

## Récapitulatif

Total events : {count}
Distribution par domaine :
{domain_lines}

## Synthèse complète

Lance dans le terminal :

  python scripts/usage_summary.py

## Liens utiles

- Repo : https://github.com/reddepot/recherche-mcp
- Phase B kickoff : docs/phase_b_kickoff.md
- ADR DSPY_GATE : docs/adr/0001-dspy-out-phase-a.md
- ADR quality weights : docs/adr/0002-quality-weights.md

—
Notification automatique (recherche-mcp/scripts/threshold_alert.py)
"""


def check_and_alert(dry_run: bool = False, force: bool = False) -> int:
    """Vérifie les seuils et envoie email si nécessaire.

    Returns exit code (0=rien, 1=alerté, 2=config absente, 3=net err, 4=vide).
    """
    _load_smtp_env()

    events = usage.read_events()
    if not events:
        log.info("Aucun event dans runs/ — pas d'alerte à émettre.")
        return 4

    total = len(events)
    by_domain = dict(Counter(e.domain or "auto" for e in events))
    log.info("Total events: %d, distribution: %s", total, by_domain)

    # Vérifier chaque seuil dans l'ordre (early_signal d'abord, go_phase_b ensuite)
    sent_any = False
    for key in ("early_signal", "go_phase_b"):
        cfg = THRESHOLDS[key]
        if total < cfg["count"]:
            log.debug("Seuil %s (%d) pas encore atteint.", key, cfg["count"])
            continue

        marker = _alert_marker_path(key)
        if marker.exists() and not force:
            log.info("Seuil %s déjà alerté (marqueur : %s).", key, marker)
            continue

        body = _build_body(key, total, by_domain)
        msg = _build_email(cfg["subject"], body)

        if dry_run:
            log.info("--dry-run actif. Email qui aurait été envoyé :")
            print("=" * 60)
            print(f"To: {msg['To']}")
            print(f"From: {msg['From']}")
            print(f"Subject: {msg['Subject']}")
            print("=" * 60)
            print(msg.get_content())
            print("=" * 60)
            sent_any = True
            continue

        if "ALERT_SMTP_PASS" not in os.environ:
            log.error(
                "ALERT_SMTP_PASS manquant. Configurer ~/.config/recherche-mcp/"
                "smtp.env (chmod 600) ou exporter la variable."
            )
            return 2

        try:
            _send_email(msg)
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(
                f"sent_at={events[-1].timestamp}\ntotal_at_send={total}\n",
                encoding="utf-8",
            )
            log.info("✅ Email envoyé pour seuil %s (total=%d).", key, total)
            sent_any = True
        except (smtplib.SMTPException, OSError) as exc:
            log.error("Erreur SMTP : %s", exc)
            return 3

    return 1 if sent_any else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche l'email sans l'envoyer (test).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignorer le marqueur d'envoi déjà effectué.",
    )
    args = parser.parse_args()

    return check_and_alert(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
