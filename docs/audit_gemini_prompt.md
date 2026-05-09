# AUDIT EXTERNE V2 — Gemini Deep Research Apps

> **Pour Gemini Pro DR Apps (modèle avec accès Google Search + Drive + NotebookLM).**
> Coller ce fichier directement comme prompt. URL repo à auditer fournie ci-dessous.

---

## Contexte

Tu es invité à auditer la **version 0.3** d'un projet Python livré par un développeur avancé (médecin du travail français). Le projet implémente :
- Un **skill Claude Code** (`/recherche`) front-end conversationnel passif
- Un **serveur MCP Python** (FastMCP 3.0+) qui expose 3 outils pour la **décomposition orthogonale** de questions de recherche complexes en 4-6 sous-prompts experts spécialisés par domaine, avec annonce d'une **matrice de dispatch** vers modèles candidats (Perplexity DR, OpenAI o3-DR, Anthropic web_search, Gemini DR Apps, ChatGPT DR, Kimi Swarm, Qwen Max DR, Codex/Gemini/Kimi CLI).

**Phase A v0.3** = formalisation de la méthode (heuristique pure, sans LLM call). Phase B (35-50 j-h) automatisera l'appel aux APIs DR.

## URL repo public à auditer

**https://github.com/reddepot/recherche-mcp** (15 commits, branche `main`, public).

Tu peux naviguer le repo via Google Search ou via les outils Drive/Web. Lis au minimum :
- `README.md` — vue d'ensemble
- `pyproject.toml` — dependencies
- `src/recherche_mcp/` — modules source (port, models, decompose, dispatch, quality, server, safety, usage, prompts/)
- `src/recherche_mcp/data/axes_by_domain.yaml` + `quality_weights.yaml` + `dispatch_matrix.yaml`
- `tests/` — 106 tests pytest (verts)
- `docs/adr/0001-dspy-out-phase-a.md` + `0002-quality-weights.md`
- `docs/polylens_audit_phaseA_20260509.md` — audit interne 4 voix
- `docs/phase_b_kickoff.md` — préparation Phase B

## Audits déjà effectués (NE PAS RÉPÉTER)

### POLYLENS interne (2026-05-09)
4 voix occidentales (Claude Opus 4.7 self + Codex GPT-5.5 + Gemini 3.1 Pro + Kimi K2.6) sur 3 axes (qualité code, tests, architecture). 4 P0 + 6 P1 fixés en commits `1e3ca97` + `757be8e`.

### Audit externe v1 (2026-05-09 plus tard)
4 voix : ChatGPT (rapport identique à Perplexity Computer), DeepSeek, Kimi Agent Swarm, Grok. **18 findings fixés** dans 6 commits `2934bd4` à `4222874` :

| Sujet déjà couvert | Statut |
|---|---|
| Façade MCP réelle (suppression `.native`, `register_tool` partout) | ✅ FIXÉ |
| `runs/*.jsonl` committed → retiré + `.gitignore` étendu | ✅ FIXÉ |
| Anti-PII étendu (NIR Corse, INIR neutre 3-4, RPPS, ADELI, FINESS, IPP, SIRET, IBAN, noms+titres) | ✅ FIXÉ |
| Axes par domaine via `axes_by_domain.yaml` (5 domaines × 7 axes) | ✅ FIXÉ |
| `quality.overall` pondéré par domaine via `quality_weights.yaml` + ADR-0002 | ✅ FIXÉ |
| DispatchResolver DI explicit (paramètre injectable) | ✅ FIXÉ |
| Sentence-transformers offline graceful degradation (fallback Jaccard) | ✅ FIXÉ |
| `make_decomposer case _: raise` factory défensive | ✅ FIXÉ |
| README seuils alignés réalité (0.5 Phase A baseline, 0.7 cible Phase B) | ✅ FIXÉ |
| LICENSE Proprietary explicite | ✅ FIXÉ |
| CI GitHub Actions (`.github/workflows/tests.yml`) | ✅ FIXÉ |
| `StrEnum` Python 3.13 idiomatique | ✅ FIXÉ |
| `autoescape` Jinja2 sélectif HTML/XML | ✅ FIXÉ |
| XDG paths via `platformdirs` cross-platform | ✅ FIXÉ |
| Exception handling typé `(ValueError, RuntimeError)` | ✅ FIXÉ |
| `cases.yaml expected_subq` test paramétrique | ✅ FIXÉ |
| `_PIIRedactFilter` racine + Formatter combinés | ✅ FIXÉ |
| `scikit-learn` retiré dependencies inutilisées | ✅ FIXÉ |

**Conséquence** : si tu identifies un de ces 18 findings, c'est **déjà fixé**. Cite alors le commit qui le résout. Ne le compte pas comme un nouveau finding.

## Ce qui t'est demandé : audit ORTHOGONAL

Apporte des perspectives que les 4 voix précédentes (occidentales et chinoises) ont **manqué structurellement**. Concentre-toi sur :

### Axe 1 — Comparaison avec l'écosystème Google / Vertex AI Agents

Tu connais l'écosystème Google. Compare l'architecture du projet avec :
- **Vertex AI Agent Builder** : Reasoning Engine, ADK, Agent2Agent (A2A) protocol
- **Gemini Function Calling** vs MCP tool registration
- **NotebookLM** comme alternative pour la décomposition orthogonale
- **Google Search Grounding** vs FastMCP custom dispatch

Quels patterns Google le projet aurait-il pu réutiliser ? Quelles erreurs de design Google a déjà résolues que ce projet répète ? À quels frameworks Google le projet **devrait-il s'aligner** Phase B (par exemple `Tool` schema Vertex au lieu de tool maison) ?

### Axe 2 — Multimodalité absente (cas user négligé)

Le projet décompose **uniquement du texte**. Pour un médecin du travail français, les questions arrivent souvent avec :
- Photos de postes de travail / EPI
- Captures d'écran de DUERP
- Audio dictées vocales
- PDFs de fiches de données de sécurité

La décomposition orthogonale ne traite **rien de ça**. Phase B traitera-t-il la multimodalité ? Quelles voix DR (Gemini DR avec image, ChatGPT DR avec vision) sont mal exploitées dans la matrice dispatch actuelle parce que le pipeline est text-only ?

Propose 3-5 cas multimodaux concrets que l'architecture actuelle est **incapable** de gérer, et le delta architectural pour Phase B/C.

### Axe 3 — Évaluation comparative avec benchmarks 2026 réels

Le repo cite "DRBench" et "AutoResearchBench" sans données chiffrées. Compare la baseline Phase A (overall 0.66, orthogonalité 0.05 sur 5 cas) avec les scores publics 2026 connus :
- GAIA Leaderboard 2026
- DRBench / Deep Research Bench (FutureSearch)
- BrowseComp / BrowseComp-Plus
- Humanity's Last Exam (HLE)
- DeepScholar-Bench (verifiability claim coverage)
- AutoResearchBench (constraint-based search)

Sur quels benchmarks la décomposition orthogonale heuristique pure pourrait-elle même participer ? Quels benchmarks faudrait-il créer pour mesurer **honnêtement** la valeur de l'approche MECE 4-6 sous-questions vs Perplexity DR direct ?

### Axe 4 — Réalité économique Phase B (TCO)

Le user envisage Phase B = automatisation API DR (Perplexity Sonar DR + OpenAI o3-DR + Anthropic web_search + xAI grok + Gemini Search Grounding + Mistral local fallback).

Calcule un TCO concret 2026 sur 5 scénarios d'usage :
- 5 recherches/mois (très light)
- 30 recherches/mois (cible README)
- 80 recherches/mois (seuil ROI réaliste mentionné)
- 200 recherches/mois (usage intensif MdT senior)
- 500 recherches/mois (équipe SPSTI)

Inclus prix réels 2026 par fournisseur (avec sources URLs vérifiables), pondéré par la matrice dispatch actuelle (Perplexity 1er pour clinique/juridique_fr, Codex CLI gratuit pour technique, etc.).

Conclusion : à partir de quel volume mensuel le projet est-il rentable vs alternatives (Perplexity Pro Sub à $20/mo, ChatGPT Pro à $200/mo, abonnements multi-DR) ?

### Axe 5 — Risque CNIL / EU AI Act spécifique 2026

Tu as accès aux décisions CNIL récentes (2024-2026) et au texte EU AI Act applicable depuis 2 août 2026.

- Le pipeline tel quel (heuristique pure, pas d'auto API) est-il déjà soumis à AIPD ?
- Le passage Phase B (auto API DR avec données médicales potentielles) bascule-t-il en système haut-risque ?
- Les patterns anti-PII regex actuels sont-ils suffisants pour exclure le système de la classification AI Act high-risk ?
- Quelles obligations doctrine récente a précisé sur l'usage par professionnel de santé d'outils LLM (CNIL mars 2026, ANS HDS, ordre des médecins) ?

Cite **3-5 décisions/textes précis** avec dates et URLs Légifrance/CNIL/EUR-Lex.

## Format de sortie attendu

Pour chaque finding orthogonal :

```
[AXE-N] [P0|P1|P2|P3] Titre court (≤ 80 chars)

Cite le fichier:ligne du repo si applicable, sinon référence externe.
Problème : 2-3 lignes max.
Mitigation proposée : 1-3 lignes max.
Référence externe obligatoire : URL Google docs / arXiv / Légifrance / CNIL / etc.
```

Sévérités identiques aux audits précédents (P0 bloquant → P3 nice-to-have).

## Règles dures

- **Audit ORTHOGONAL** : si tu vois un finding déjà couvert par les 4 voix V1, signale-le brièvement avec "déjà fixé commit X" et passe au suivant
- **≥3 findings substantiels par axe** (5 axes × 3 = 15 minimum nouveaux)
- **Citations URLs obligatoires** : toutes les références externes doivent être vérifiables (Vertex AI docs, EUR-Lex, CNIL, arXiv, GitHub releases, leaderboards publics)
- **Réponse en français concis ≤ 3000 mots**
- Termine par : (a) verdict synthétique 1 paragraphe positionnant le projet vs état de l'art Google 2026, (b) **3 actions prioritaires Phase B** spécifiques à ce que toi (Gemini) apportes que les autres voix ne pouvaient pas

## Sortie souhaitée

1. Tableau récap findings par axe + sévérité
2. Détails par finding avec URLs vérifiables
3. **Calcul TCO chiffré** (Axe 4) sous forme de tableau Markdown
4. Verdict synthétique
5. **3 actions prioritaires Phase B Gemini-spécifiques**
6. Sources externes (15-25 URLs)

Bon audit.
