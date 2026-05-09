# Phase B kickoff — γ-α dispatch auto (35-50 j-h)

**Statut** : Préparée 2026-05-09. Démarrage conditionné à la collecte de logs usage Phase A v0.2 sur 7+ jours.
**ADR référence** : `~/.claude/projects/-Users-radu/memory/decision_recherche_skill_devcode_20260508.md`

## Pré-requis avant démarrage

1. ✅ Phase A v0.2 livrée et auditée POLYLENS (61/61 tests)
2. ⏳ **Logs usage Phase A** : ≥10-20 invocations réelles du skill `/recherche`
   - Source : `~/Developer/projects/recherche-mcp/runs/usage_*.jsonl`
   - Synthèse : `python scripts/usage_summary.py`
3. ⏳ NAS rebooté + push Gitea + accès stable APIs externes
4. ⏳ Décision user "GO Phase B" explicite

## Périmètre Phase B (γ-α dispatch auto API)

Selon ADR Sprint 2 + 12 items backlog POLYLENS.

### Livrables principaux

1. **`DRFacade` interface générique + adapters par fournisseur**
   - `OpenAIDRAdapter` (`o3-deep-research`, `o4-mini-deep-research`)
   - `PerplexityDRAdapter` (`sonar-deep-research`, `sonar-pro`)
   - `AnthropicWebSearchAdapter` (`web_search` tool)
   - `xAIGrokAdapter` (Grok search API)
   - `MistralLocalAdapter` (Ollama fallback CNIL/UE)
   - Pattern Adapter convergent 3 voix challenge POLYLENS DEVCODE-Vote

2. **Policy engine côté MCP server (déplacement gating skill → serveur)**
   - Deny-by-default P0, OAuth scopes par outil
   - `request_classification` : auto-détection sujet médical → routage RedAPI obligatoire
   - Redaction PHI avant dispatch (intégration `safety.py`)
   - Hooks PreToolUse Claude Code = défense en profondeur SEULEMENT (pas logique métier)

3. **Isolation contextvars Python par requête**
   - Mitigation corruption d'état concurrentielle FastMCP × LangGraph (POLYLENS challenge GLM)
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
   - Réduit latence P1/P2 (mitigation POLYLENS Kimi P1 12-15s)

7. **Fallback local Mistral/Ollama**
   - Résilience CNIL/localisation UE
   - Test de bascule auto si APIs US indisponibles

### Backlog 12 items POLYLENS à intégrer

Source : `docs/polylens_audit_phaseA_20260509.md` section "Backlog Phase B/C"

| # | Item | Sévérité | Effort |
|---|---|---|---|
| 1 | `make_decomposer` factory `case _: raise` | P2 | <30min |
| 2 | `class Domain(str, Enum)` → `StrEnum` | P3 | <30min |
| 3 | `safety.py` NIR Corse (2A/2B) | P1 | <30min |
| 4 | `safety.py` validator Pydantic intégré | P3 | 1-2h |
| 5 | `dispatch_matrix.yaml` user-override `~/.config/recherche-mcp/` | P2 | 1h |
| 6 | `test_server.py` FastMCP test client | P1 | 2-3h |
| 7 | Decomposer DI explicite (DispatchResolver param) | P1 | 2-3h |
| 8 | `make_decomposer` registre dynamique | P2 | 1h |
| 9 | `quality.py` graceful degradation offline (fallback Jaccard) | P2 | 1-2h |
| 10 | `expected_subq` test paramétré sur fixtures | P2 | 1h |
| 11 | `server.py` split `cli.py` | P2 | 30min |
| 12 | Marker `@pytest.mark.unit/integ` audit complet | P3 | 30min |

**Total backlog** : ~10-15h.

### Métriques cibles Phase B

| Métrique | Phase A baseline | Phase B cible |
|---|---|---|
| Quality overall | > 0.5 (5/5 cas) | **> 0.7 (avec LLM-driven decomposition)** |
| Quality orthogonalité | > 0.05 | **> 0.4** (cosine max ≤ 0.6) |
| Time-to-actionable mode express | N/A | **< 5s P2** |
| Time-to-actionable MAS | N/A | **médian -30% vs manuel actuel sur P1** |
| Tests | 68/68 | **+30 tests** (concurrence, adapters, gating, audit) |
| Couverture domaines API auto | 0 | Perplexity + OAI + Anthropic + xAI + Mistral local |

## Plan d'attaque suggéré (5 sprints)

### Sprint B1 — Backlog POLYLENS quick wins (1-2 j-h)
Items 1, 2, 8, 11, 12 (Domain StrEnum, factory défensive, registre dynamique, split cli.py, audit markers).
Commit : `chore: phase-b backlog polylens quick wins`.

### Sprint B2 — DRFacade + adapters (8-12 j-h)
- Interface `DRFacade` abstraite
- 5 adapters concrets (Perplexity, OAI, Anthropic, xAI, Mistral local)
- Tests par adapter avec mocks API + 1 smoke test API réel optionnel
- Item 7 : Decomposer DI accepte `DispatchResolver`
- Items 3, 4 : safety.py NIR Corse + validator Pydantic
Commit : `feat(adapter): DRFacade + 5 adapters par fournisseur`.

### Sprint B3 — Policy engine + concurrence (10-15 j-h)
- Policy engine côté MCP server (deny-by-default P0)
- Auto-détection sujet médical → routage RedAPI
- Redaction PHI before dispatch
- Isolation contextvars + correlation_id propagation
- Tests charge ≥10 req parallèles
- Item 5 : dispatch_matrix.yaml user-override
- Item 6 : test_server.py
Commit : `feat(policy): server-side gating + contextvars isolation`.

### Sprint B4 — Audit + mode express + fallback (8-12 j-h)
- Audit hash-chain WORM light (JSONL signé + idempotency keys)
- Mode express : skip MAS si confidence > seuil sur RAG-only
- Fallback Mistral local
- Item 9 : quality.py graceful degradation offline
- Item 10 : expected_subq test paramétré
Commit : `feat(express): mode bypass + fallback Mistral + audit hash-chain`.

### Sprint B5 — Validation + capitalize (3-5 j-h)
- POLYLENS allégé Phase B (4-5 axes cette fois : sécurité, qualité, tests, archi, opposabilité)
- Smoke test sur 5-10 cas réels avec usage logs Phase A en input
- Capitalize → memory + ADR-0002 Phase B closure

**Total Phase B estimé : 30-46 j-h** (vs 35-50 budget initial).

## Comment décider du démarrage Phase B

### Conditions de GO

1. ✅ Phase A v0.2 livrée
2. ⏳ **≥10-20 invocations réelles** du skill par user sur 7+ jours
3. ⏳ **Synthèse usage signal clair** : volumétrie suffisante par domaine, latence acceptable, qualité baseline confirmée OU dégradée avec patterns identifiables
4. ⏳ **Pas de bugs P0/P1 émergents** non couverts par POLYLENS Phase A
5. ⏳ Décision user explicite "GO Phase B"

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
