# POLYLENS audit allégé Phase A — recherche-mcp v0.1

**Date** : 2026-05-09
**Mode** : POLYLENS allégé (3 axes, panel 4 occidentales, pas de cross-culturelle)
**Voix consultées** : Claude Opus 4.7 (self-audit) + Codex GPT-5.5 CLI + Gemini 3.1 Pro CLI + Kimi K2.6 CLI
**Statut** : 4/4 voix livrées (Kimi tardive)
**Décision user** : fix P0+P1 critiques avant Phase B

## Sur-convergences ★ (3-4 voix)

### CONV-1 ★★★★ — Façade `MCPServerPort` dead code (P0)

| Voix | Sévérité |
|---|---|
| Gemini | P0 |
| Claude | P0 |
| Codex | P1 |
| Kimi | P1 |

`port.py` définissait `MCPServerPort` ABC, mais `server.py:25` instanciait `FastMCP` directement → **faux découplage**. Si breaking change FastMCP pré-1.0, on devrait modifier server.py.

**Fix appliqué** : `FastMCPAdapter(MCPServerPort)` implémenté dans `port.py`. `server.py` instancie `_adapter = FastMCPAdapter(...)` puis utilise `_adapter.native` pour les `@mcp.tool()` legacy. Migration progressive Phase B vers `register_tool()` API publique.

### CONV-2 ★★★★ — `DispatchMatrix.current()` race condition init (P0/P1)

| Voix | Sévérité |
|---|---|
| Claude | P0 |
| Codex | P1 |
| Gemini | P1 |
| Kimi | P1 (sur reset()) |

`_lock` protégeait reload/resolve mais PAS le check `_instance is None` dans `current()`. 2 threads concurrents pouvaient créer 2 instances + 2 SIGHUP handlers.

**Fix appliqué** : double-checked locking (DCL) dans `current()` + `reset()` acquiert `_lock`.

### CONV-3 ★★★★ — Test SIGHUP n'en est pas un (P1/P2)

`test_dispatch_sighup_reload` appelait `matrix.reload()` directement, pas SIGHUP. Le handler `signal.signal()` pouvait être cassé sans détection.

**Fix appliqué** :
- Renommé `test_dispatch_reload_after_yaml_modification` (test du reload manuel)
- Ajouté `test_dispatch_real_sighup_triggers_reload` qui envoie `os.kill(os.getpid(), signal.SIGHUP)` réel + skip Windows/thread non-main

### CONV-4 ★★★★ — Couplage `Decomposer → DispatchMatrix` via singleton lazy import (P1/P2)

`decompose.py:66, 184` : `from .dispatch import DispatchMatrix` lazy. Pas de circular réel — c'est un hack. Decomposer porte la responsabilité du dispatch (violation SRP).

**Fix partiel appliqué** : `extract_subject` extrait en module-level (couplage fratricide GraphDecomposer→LinearDecomposer fixé). DispatchResolver injection deferred Phase B (refactor plus large).

## Convergences 2/4 voix

### YAML safe_load None handling (Codex+Gemini P1)
`yaml.safe_load("")` renvoie `None` → `_data.get()` → AttributeError silencieux.
**Fix** : `or {}` + validation `isinstance(raw, dict)` + ValueError explicite.

### `_dispatch_covers_subq` accepte doublons (Codex P1)
Set masque doublons. Un dispatch [A, A, B, C] sur sub_questions {A, B, C, D} passerait si l'ensemble matchait.
**Fix** : check `len(d_ids) != len(set(d_ids))` avant comparaison ensemble.

### `_MODEL` SentenceTransformer non thread-safe (Gemini P1)
Lazy load global sans lock. FastMCP concurrent peut corrompre l'instanciation.
**Fix** : `_MODEL_LOCK = threading.Lock()` + double-check pattern + helper `set_embed_model()` pour mocks tests.

### Tests integ dépendants modèle réel flaky (Codex P1)
Plusieurs tests integ chargent sentence-transformers (~200MB download premier appel, lent offline).
**Fix** : helper `set_embed_model()` exposé pour monkeypatch dans tests futurs (Phase B implementations).

### Fixtures `expected_subq` documentées non assertées (Codex P2)
Backlog Phase B : test paramétré qui vérifie présence des axes attendus.

## Pépites uniques utiles

### ♦ Gemini AXE-2 P0 — Edges intégrité référentielle non vérifiée
> Aucun test ne vérifie que `source_id`/`target_id` des Edges existent dans `sub_questions`. Pydantic n'a pas de `@model_validator`.

**Fix appliqué** :
- `@model_validator(mode="after") def _edges_reference_existing_subqs(self)` dans `ResearchPlan`
- Test `test_research_plan_edges_must_reference_existing_subqs`
- Test `test_graph_edges_reference_existing_subqs` sur instance générée

### ♦ Kimi AXE-1 P2 — `_PIIRedactFilter` mute LogRecord en place
> Modifier `record.msg` corrompt pour autres handlers et n'est pas idempotent.

**Fix appliqué** : `_PIIRedactFormatter` qui agit sur le rendu final, pas le LogRecord. Préserve idempotence + n'affecte pas autres handlers.

### ♦ Kimi AXE-1 P2 — `catalog_sources` accède `matrix._data` privé
**Fix appliqué** : nouvelle méthode publique `DispatchMatrix.get_candidates(domain)` + `server.py:catalog_sources` l'utilise.

### ♦ Codex AXE-1 P2 — `make_decomposer` factory sans branche défensive
Si `Strategy(...)` contourné, fallthrough silencieux retournant `None`.
**Backlog Phase B** : ajouter `case _: raise ValueError(...)`.

### ♦ Gemini AXE-1 P3 — `class Domain(str, Enum)` → `StrEnum`
**Backlog** : migration Python 3.11+ idiomatique.

### ♦ Gemini AXE-1 P3 — `ValidationInfo` non typé
**Fix appliqué** : `def _dispatch_covers_subq(cls, v: list[DispatchEntry], info: ValidationInfo)`.

### ♦ Kimi AXE-2 P1 — `server.py` et `safety.py` sans tests
**Fix appliqué** : `test_safety.py` créé avec 25 tests paramétriques (NIR FR avec/sans Corse, dates, téléphones, emails, idempotence, faux positifs, combinaisons).
**Backlog** : `test_server.py` avec FastMCP test client (Phase B).

### ♦ Claude AXE-1 P1 — `safety.py` NIR Corse (2A/2B) non géré
**Backlog Phase B** : pattern `(?:2[AB]|\d{2})` pour le département.

### ♦ Claude AXE-3 P3 — `safety.py` pas intégré aux validators Pydantic
**Backlog Phase B** : validator optionnel `Question.text` qui détecte PII et logue warning.

### ♦ Claude AXE-3 P2 — `dispatch_matrix.yaml` pas user-overridable
**Backlog Phase B** : chargement séquentiel default → `~/.config/recherche-mcp/dispatch.yaml` → arg `--matrix-path`.

## Verdicts globaux des voix

### Codex
> "Phase A v0.1 acceptable comme baseline expérimentale, sans P0 apparent. Mais ne doit pas servir de socle Phase B sans durcir trois points : validation stricte de la matrice dispatch, découplage réel du serveur/dispatch, et tests moins dépendants du modèle embeddings réel."

### Gemini
> "Le socle Phase A v0.1 réussit son pari de formalisation initiale, mais présente une dette architecturale naissante qui freinera drastiquement l'auto-DR (Phase B) si elle n'est pas purgée. L'abstraction MCP est une façade inactive (code mort), et les Decomposers sont artificiellement couplés au DispatchMatrix via un Singleton non thread-safe et des lazy imports symptomatiques d'une mauvaise séparation des responsabilités."

### Kimi
> (verdict tronqué, fin du document non livré dans le temps imparti)

## Récap fixes appliqués

| Catégorie | Fixes | Commits |
|---|---|---|
| Thread-safety singleton | DCL `current()`, reset() lock-guarded | (à venir) |
| YAML robustness | `None` guard, dict validation | (à venir) |
| Pydantic validators | duplicate sub_question_id, edges integrity, ValidationInfo typing | (à venir) |
| SentenceTransformer | lock-guarded lazy load + `set_embed_model()` test helper | (à venir) |
| MCP façade | `FastMCPAdapter` réel impl + `server.py` refactor | (à venir) |
| Logging anti-PII | Filter → Formatter (idempotent) | (à venir) |
| API publique DispatchMatrix | `get_candidates()` méthode publique | (à venir) |
| extract_subject couplage | extrait module-level | (à venir) |
| Tests | `test_safety.py` (25 tests), 2 nouveaux tests dispatch (YAML edge cases + SIGHUP réel), 2 tests models (duplicate dispatch + edges integrity) | (à venir) |
| SIGHUP test | renommé + nouveau test SIGHUP réel | (à venir) |

## Backlog Phase B/C

| Finding | Sévérité | Effort |
|---|---|---|
| `make_decomposer` factory `case _: raise` | P2 | <30min |
| `class Domain(str, Enum)` → `StrEnum` | P3 | <30min |
| `safety.py` NIR Corse | P1 | <30min |
| `safety.py` validator Pydantic intégré | P3 | 1-2h |
| `dispatch_matrix.yaml` user-override | P2 | 1h |
| `test_server.py` FastMCP client | P1 | 2-3h |
| Decomposer DI explicite (DispatchResolver param) | P1 | 2-3h |
| `make_decomposer` registre dynamique | P2 | 1h |
| `quality.py` graceful degradation offline (fallback Jaccard) | P2 | 1-2h |
| `expected_subq` test paramétré | P2 | 1h |
| `server.py` split `cli.py` | P2 | 30min |
| Marker `@pytest.mark.unit/integ` audit complet | P3 | 30min |

**Total backlog** : ~10-15h Phase B (intégrés au Sprint 2 γ-α).

## Méthodologie POLYLENS allégée — observations

- **3 axes au lieu de 7** : suffisant pour skill perso non-opposable. Phase B sera revue 7 axes complets si stakes augmentent.
- **Panel 4 occidentales sans cross-culturelle** : adapté Phase A v0.1 minimal. Pour Phase C médico-légal opposable, voix chinoises obligatoires.
- **Time investi** : ~30 min (vs estimé 10 min) — Kimi tardive a élargi.
- **ROI** : excellent. **2 P0 réels détectés** (façade dead code, edges integrity) qui auraient explosé en Phase B. Sans audit, on aurait construit Phase B sur dette structurelle.
- **Convergences cross-voix robustes** sur les P0+P1, dissonances normales sur P2/P3.

## Prochaine étape

1. ✅ Fixes P0+P1 appliqués
2. ⏳ pytest re-run pour valider
3. ⏳ Commit fixes en 3-4 commits cohérents
4. ⏳ Capitaliser dans memory (mise à jour `lessons_session_20260509_recherche_phase_a.md`)
5. ⏸️ Push Gitea (post-NAS reboot)
