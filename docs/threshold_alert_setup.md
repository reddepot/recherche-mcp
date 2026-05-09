# Notification automatique d'atteinte du seuil GO Phase B

Setup du mécanisme qui envoie un email lorsque le journal usage du skill
`/recherche` atteint le seuil suffisant pour décider GO/NO-GO Phase B.

## Seuils

| Palier | Nb recherches | Email envoyé |
|---|---|---|
| **Early signal** | 15 | Premier signal lisible — pas encore GO |
| **GO Phase B** | 30 | Seuil suffisant pour décision empirique |

Justification du seuil 30 : aligne **DSPY_GATE condition (a)** + permet test
Wilcoxon signé apparié Linear vs Graph + DEVCODE-Vote sur les poids
`quality_weights.yaml`.

## Email destinataire

`redtech@protonmail.com` (push notif iOS Protonmail = notification mobile).

## Installation

### 1. Configurer les credentials SMTP

Créer `~/.config/recherche-mcp/smtp.env` avec :

```env
ALERT_SMTP_PASS=<ton_mot_de_passe_Zimbra_redbot@reddie.ovh>
```

Le reste a des défauts sensibles :
- `ALERT_SMTP_HOST=ssl0.ovh.net`
- `ALERT_SMTP_PORT=587`
- `ALERT_SMTP_USER=redbot@reddie.ovh`
- `ALERT_MAIL_TO=redtech@protonmail.com`

Permissions strictes :

```bash
mkdir -p ~/.config/recherche-mcp
chmod 700 ~/.config/recherche-mcp
chmod 600 ~/.config/recherche-mcp/smtp.env
```

### 2. Test manuel (dry-run, sans envoi)

```bash
cd ~/Developer/projects/recherche-mcp
source .venv/bin/activate
python scripts/threshold_alert.py --dry-run
```

Si `runs/` ne contient pas encore d'events, le script affiche
"Aucun event dans runs/ — pas d'alerte à émettre.".

### 3. Test envoi réel (forcer un envoi pour valider la chaîne SMTP)

```bash
# Génère un event factice pour passer le seuil
python -c "
from recherche_mcp.decompose import LinearDecomposer
from recherche_mcp.models import Question, Domain
from recherche_mcp import usage
for i in range(31):
    q = Question(text=f'Test seuil {i:02d} burnout MdT FR 2026', domain=Domain.CLINIQUE)
    plan = LinearDecomposer().decompose(q)
    usage.log_event(question=q.text, domain='clinique', strategy='linear',
                    n_subq_requested=5, plan=plan, latency_ms=1.0)
"

# Lance l'alerte (envoi réel)
python scripts/threshold_alert.py --force
```

Vérifier réception sur `redtech@protonmail.com`. Une fois validé, supprimer
les events factices :

```bash
rm "$(python -c 'from recherche_mcp.usage import _current_log_path; print(_current_log_path())')"
rm runs/.alert_sent_*
```

### 4. Installation launchd (exécution quotidienne automatique à 9h)

```bash
cp scripts/com.reddepot.recherche-mcp.threshold-alert.plist \
   ~/Library/LaunchAgents/

launchctl load ~/Library/LaunchAgents/com.reddepot.recherche-mcp.threshold-alert.plist
launchctl list | grep recherche-mcp
```

### 5. Vérifier l'exécution

Logs après chaque run :

```bash
cat /tmp/recherche-mcp-threshold.log
cat /tmp/recherche-mcp-threshold.err   # vide si tout OK
```

Forcer une exécution immédiate (pour tester) :

```bash
launchctl start com.reddepot.recherche-mcp.threshold-alert
```

## Désinstallation

```bash
launchctl unload ~/Library/LaunchAgents/com.reddepot.recherche-mcp.threshold-alert.plist
rm ~/Library/LaunchAgents/com.reddepot.recherche-mcp.threshold-alert.plist
```

## Comportement

- Le script vérifie les seuils dans l'ordre : early_signal (15), go_phase_b (30).
- Pour chaque seuil **franchi pour la première fois**, un email est envoyé.
- Un marqueur `runs/.alert_sent_<key>` est créé pour éviter les doublons.
- `--force` ignore le marqueur (utile pour tests).
- `--dry-run` affiche l'email sans l'envoyer.

## Exit codes

| Code | Signification |
|---|---|
| 0 | Aucune alerte envoyée (seuil pas atteint OU déjà alerté) |
| 1 | Alerte envoyée avec succès |
| 2 | Configuration SMTP manquante (`ALERT_SMTP_PASS` absent) |
| 3 | Erreur réseau / SMTP |
| 4 | Aucun event dans `runs/` (rien à compter) |

## Format de l'email

Subject :
`[recherche-mcp] ✅ Seuil GO Phase B atteint — 30 recherches`

Body :
- Récapitulatif total + distribution par domaine
- Commande pour lancer la synthèse complète (`python scripts/usage_summary.py`)
- Liens vers repo, phase_b_kickoff, ADRs
