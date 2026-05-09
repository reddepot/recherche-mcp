# Phase B kickoff — γ-α dispatch auto (estim. 25-40 j-h)

**Statut** : Préparée. Démarrage conditionné à la collecte de logs usage Phase A sur ≥7 jours.

## Pré-requis avant démarrage

1. ✅ Phase A livrée et auditée (audits internes + externes)
2. ⏳ **Logs usage Phase A** : ≥10-20 invocations réelles du skill `/recherche`
   - Source : log usage permanent (path XDG via `platformdirs`, override `RECHERCHE_MCP_RUNS_DIR`)
   - Synthèse : `python scripts/usage_summary.py`
3. ⏳ Accès stable aux APIs externes ciblées
4. ⏳ Décision « GO Phase B » explicite

## Périmètre Phase B (γ-α dispatch auto API)

### Livrables principaux

1. **`DRFacade` interface générique + adapters par fournisseur**
   - `OpenAIDRAdapter` (`o3-deep-research`, `o4-mini-deep-research`)
   - `PerplexityDRAdapter` (`sonar-deep-research`, `sonar-pro`)
   - `AnthropicWebSearchAdapter` (`web_search` tool)
   - `xAIGrokAdapter` (Grok search API)
   - `MistralLocalAdapter` (Ollama fallback CNIL/UE)
   - Pattern Adapter qui découple le code métier du SDK fournisseur

2. **Policy engine côté MCP server (déplacement gating skill → serveur)**
   - Deny-by-default P0, OAuth scopes par outil
   - `request_classification` : auto-détection sujet médical → routage RedAPI obligatoire
   - Redaction PHI avant dispatch (intégration `safety.py`)
   - Hooks PreToolUse Claude Code = défense en profondeur SEULEMENT (pas logique métier)

3. **Isolation contextvars Python par requête**
   - Mitigation corruption d'état concurrentielle FastMCP × orchestrateur multi-étapes
   - Propagation `correlation_id` dans chaque appel LLM/API

4. **Tests de charge concurrence**
   - ≥10 requêtes parallèles avec sub-questions différentes
   - Vérifier zéro cross-talk entre runs

5. **Audit hash-chain WORM (light Phase B)**
   - Journal événementiel signé append-only
   - `correlation_id`/`tool_call_id`/`parent_id`
   - Version modèle + prompts + sources + décisions policy
   - **Pas encore Postgres checkpointer** (Phase C)

6. **Mode "express" bypass MAS**
   - Pour requêtes haute confiance (1 RAG + 1 modèle)
   - Bascule MAS si confidence < seuil
   - Réduit la latence sur les questions P1/P2 simples

7. **Fallback local Mistral/Ollama**
   - Résilience CNIL/localisation UE
   - Test de bascule auto si APIs US indisponibles

### Backlog résiduel à intégrer

La majorité du backlog d'origine a été absorbée Phase A (façade MCP réelle, axes par domaine, anti-PII étendu, fallback offline, DI explicite, etc.). Restent à traiter :

| # | Item | Sévérité | Effort |
|---|---|---|---|
| 1 | `safety.py` validator Pydantic intégré (warning si PII détectée dans `Question`) | P3 | 1-2h |
| 2 | `dispatch_matrix.yaml` user-override (`~/.config/recherche-mcp/`) | P2 | 1h |
| 3 | `test_server.py` FastMCP test client | P1 | 2-3h |
| 4 | `make_decomposer` registre dynamique (au lieu de match exhaustif) | P2 | 1h |
| 5 | `server.py` split `cli.py` (entrypoint séparé du module serveur) | P2 | 30min |

**Total backlog résiduel** : ~5-7h.

### Métriques cibles Phase B

| Métrique | Phase A baseline | Phase B cible |
|---|---|---|
| Quality overall | > 0.5 (5/5 cas) | **> 0.7 (avec LLM-driven decomposition)** |
| Quality orthogonalité | > 0.05 | **> 0.4** (cosine max ≤ 0.6) |
| Time-to-actionable mode express | N/A | **< 5s P2** |
| Time-to-actionable MAS | N/A | **médian -30% vs manuel actuel sur P1** |
| Tests | 106/106 | **+30 tests** (concurrence, adapters, gating, audit) |
| Couverture domaines API auto | 0 | Perplexity + OAI + Anthropic + xAI + Mistral local |

## Plan d'attaque suggéré (5 sprints)

### Sprint B1 — Backlog quick wins (1-2 j-h)
Items 4, 5 du backlog résiduel (registre dynamique factory, split `cli.py`).

### Sprint B2 — DRFacade + adapters (8-12 j-h)
- Interface `DRFacade` abstraite
- 5 adapters concrets (Perplexity, OpenAI, Anthropic, xAI, Mistral local)
- Tests par adapter avec mocks API + 1 smoke test API réel optionnel
- Item 1 : `safety.py` validator Pydantic intégré

### Sprint B3 — Policy engine + concurrence (10-15 j-h)
- Policy engine côté MCP server (deny-by-default P0)
- Auto-détection sujet médical → routage gateway sécurisé
- Redaction PHI avant dispatch
- Isolation contextvars + propagation `correlation_id`
- Tests charge ≥10 requêtes parallèles
- Item 2 : `dispatch_matrix.yaml` user-override
- Item 3 : `test_server.py`

### Sprint B4 — Audit + mode express + fallback (8-12 j-h)
- Audit hash-chain WORM light (JSONL signé + idempotency keys)
- Mode express : skip MAS si confidence > seuil sur RAG-only
- Fallback Mistral local opérationnel

### Sprint B5 — Validation + capitalize (3-5 j-h)
- Re-passe d'audit allégé (4-5 axes : sécurité, qualité, tests, archi, opposabilité)
- Smoke test sur 5-10 cas réels avec logs usage Phase A en input
- Capitalisation des leçons + ADR Phase B closure

**Total Phase B estimé : 30-46 j-h.**

## Comment décider du démarrage Phase B

### Conditions de GO

1. ✅ Phase A livrée
2. ⏳ **≥10-20 invocations réelles** du skill sur ≥7 jours
3. ⏳ **Synthèse usage avec signal clair** : volumétrie suffisante par domaine, latence acceptable, qualité baseline confirmée ou patterns d'échec identifiables
4. ⏳ **Pas de bugs P0/P1 émergents** non couverts par les audits Phase A
5. ⏳ Décision explicite « GO Phase B »

### Conditions de NO-GO ou pivot

- < 5 invocations en 7 jours → skill peu utilisé, repenser cas d'usage avant Phase B
- Dégradation qualité massive (<0.3 systématique) → reformuler heuristique avant LLM call
- Bugs réguliers identifiés → fix Phase A v0.3 avant Phase B
- Latence p95 > 10s → optimiser Phase A avant complexifier MAS

## Comment lire les logs usage pour décider

```bash
cd ~/Developer/projects/recherche-mcp
source .venv/bin/activate
python scripts/usage_summary.py            # synthèse globale
python scripts/usage_summary.py 2026-05    # mois spécifique
python scripts/usage_summary.py --json     # output JSON brut pour analyse externe
```

Indicateurs clés :
- `total_events` : volumétrie usage
- `domain_distribution` : répartition par domaine (équilibré ou biais ?)
- `quality_by_domain` : quels domaines sous-performent
- `latency_ms.p95` : performance utilisateur perçue
- `anomalies.n_errors` : robustesse
- `recent_questions` : nature des questions réelles posées

## Prochaine étape opérationnelle (ordre)

1. ⏸️ User teste skill `/recherche` en conditions réelles (5-20 invocations sur 7 jours)
2. ⏳ Logs `usage_*.jsonl` accumulent automatiquement
3. ⏳ Push Gitea (post-NAS reboot)
4. ⏳ Synthèse `python scripts/usage_summary.py` → GO/NO-GO Phase B
5. ⏳ Si GO : kickoff Phase B avec routine remote Opus 4.7 sur prompt structuré (modèle Phase A)
