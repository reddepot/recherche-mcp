# AUDIT EXTERNE V2 — modèle-agnostic (post-fixes V1)

> Pour tout modèle DR : **ChatGPT DR / Perplexity DR / Kimi Swarm / Qwen Max DR / DeepSeek / Grok Heavy / Claude.ai Research**.
> Coller ce fichier directement comme prompt.
> Une **version Gemini-spécifique** existe en parallèle : `docs/audit_gemini_v2.md` (Vertex AI / multimodalité / Google Search). Ne pas dupliquer ses angles ici.

---

## Contexte

Tu auditeur invité à examiner la **version 0.3** d'un projet Python livré par un développeur avancé (médecin du travail français). Le projet :
- **Skill Claude Code** `/recherche` (front-end conversationnel passif)
- **Serveur MCP Python** (FastMCP 3.0+) qui expose 3 outils : `decompose_question`, `generate_subprompts`, `catalog_sources`. Décomposition orthogonale 4-6 sous-prompts experts par domaine + matrice dispatch vers modèles candidats (Perplexity DR, OpenAI o3-DR, Anthropic web_search, Gemini DR Apps, ChatGPT DR, Kimi Swarm, Qwen Max DR, Codex/Gemini/Kimi CLI).

**Phase A v0.3** = formalisation méthode (heuristique pure, sans LLM call). Phase B (35-50 j-h estimé) automatisera l'appel aux APIs DR.

## URL repo public à auditer

**https://github.com/reddepot/recherche-mcp** (15 commits, branche `main`, public).

Fichiers prioritaires :
- `README.md` + `pyproject.toml`
- `src/recherche_mcp/` (port, models, decompose, dispatch, quality, server, safety, usage, prompts/)
- `src/recherche_mcp/data/` (axes_by_domain.yaml, quality_weights.yaml, dispatch_matrix.yaml)
- `tests/` (106 tests pytest verts)
- `docs/decisions/0001-dspy-out-phase-a.md` + `0002-quality-weights.md`
- `docs/polylens_audit_phaseA_20260509.md` (audit interne 4 voix)
- `docs/audit_external_prompt.md` (prompt audit V1 — déjà passé par 4 modèles)

## Audits déjà effectués (NE PAS RÉPÉTER)

### Audit interne POLYLENS (2026-05-09)
4 voix occidentales (Claude self + Codex + Gemini + Kimi) sur 3 axes (qualité code, tests, archi). 4 P0 + 6 P1 fixés (commits `1e3ca97`, `757be8e`).

### Audit externe V1 (2026-05-09)
4 modèles : ChatGPT, DeepSeek, Kimi Agent Swarm, Grok. **18 findings fixés** dans 6 commits (`2934bd4` → `4222874`) :

| # | Sujet déjà couvert | Commit fix |
|---|---|---|
| 1 | Façade MCP réelle (suppression `.native`, `register_tool` partout) | `4629c2c` |
| 2 | `runs/*.jsonl` retiré du repo + `.gitignore` étendu | `2934bd4` |
| 3 | Anti-PII étendu médical (NIR Corse + INIR neutre 3-4 + RPPS + ADELI + FINESS + IPP + SIRET + IBAN + noms+titres) | `d14a77d` |
| 4 | Axes par domaine via `axes_by_domain.yaml` (5 domaines × 7 axes) | `e773c3a` |
| 5 | `quality.overall` pondéré par domaine + ADR-0002 | `e773c3a` |
| 6 | DispatchResolver DI explicit (resolver injectable) | `4222874` |
| 7 | Sentence-transformers offline graceful degradation (fallback Jaccard) | `961c09e` |
| 8 | `make_decomposer case _: raise` factory défensive | `2934bd4` |
| 9 | README seuils alignés (0.5 baseline, 0.7 cible Phase B) | `2934bd4` |
| 10 | LICENSE Proprietary explicite | `2934bd4` |
| 11 | CI GitHub Actions `.github/workflows/tests.yml` | `4222874` |
| 12 | `StrEnum` Python 3.13 idiomatique | `2934bd4` |
| 13 | `autoescape` Jinja2 sélectif HTML/XML | `2934bd4` |
| 14 | XDG paths via `platformdirs` cross-platform | `961c09e` |
| 15 | Exception handling typé `(ValueError, RuntimeError)` | `4629c2c` |
| 16 | `cases.yaml expected_subq` test paramétrique (15 nouveaux tests) | `4222874` |
| 17 | `_PIIRedactFilter` racine + Formatter combinés | `4629c2c` |
| 18 | `scikit-learn` retiré dependencies inutilisées | `2934bd4` |

**Conséquence** : si tu identifies un de ces 18 findings, marque-le « **DÉJÀ FIXÉ commit X** » brièvement et passe au suivant. **Concentre-toi sur ce qui est encore manquant.**

## Ce qui t'est demandé : audit ORTHOGONAL V2

Apporte des perspectives que les **4 voix V1 ET la Gemini V2** ont laissées de côté. Concentre-toi sur 5 axes spécifiques qui n'ont pas été couverts.

### Axe 1 — Validation des fixes V1 (méta-audit)

Pour chacun des 18 fixes V1 listés ci-dessus, **vérifie la qualité réelle du fix** :
- Est-ce un fix substantiel ou du theatrum (changement cosmétique sans effet réel) ?
- Y a-t-il des **régressions** introduites par le fix ?
- Le fix est-il **complet** ou laisse-t-il des trous (ex : façade MCP réelle, mais autres usages bypassent encore) ?
- La couverture de tests pour le fix est-elle **suffisante** ?

Exemples de questions critiques :
- Le pattern NIR étendu accepte-t-il vraiment INIR neutre 3-4, ou la regex casse sur certains formats ?
- `DispatchResolver` est-il vraiment injectable ou le default singleton est encore le seul utilisé ?
- L'`autoescape` Jinja2 sélectif protège-t-il vraiment, ou les templates `.j2` actuels (qui font du markdown) sont-ils déjà à risque XSS ?

**Cible : ≥3 findings de regression / fix incomplet.**

### Axe 2 — Robustesse production / sécurité adversariale

Le code Phase A tourne en local stdio mais Phase B passera en HTTP (Sprint 5). Anticipe les attaques :

- **Prompt injection MCP** : un client malveillant peut-il faire que `decompose_question(text="...injection...")` produise des sous-prompts qui ensuite poussent un LLM aval à exfiltrer des données ?
- **DoS via cases YAML** : le YAML `dispatch_matrix.yaml` rechargé par SIGHUP sur fichier malformé produit-il un crash ?
- **Adversarial inputs** : question en boucle infinie, tokens récursifs, bombes regex sur `safety.py` patterns
- **Model name spoofing** : la matrice dispatch annonce des modèles. Si user copie-colle vers un modèle compromis nommé `perplexity-deep-research-fake`, le pipeline le détecte-t-il ?
- **Race conditions DispatchMatrix RLock** : tests verts en mono-thread, mais en production multi-client MCP simultané ?
- **Sentence-transformers fallback Jaccard** : si attaquant force le code en mode offline (ex : DNS rebinding), est-ce qu'il peut exploiter la dégradation Jaccard pour faire passer des sous-questions non-orthogonales ?

**Cible : ≥3 findings vecteurs d'attaque concrets.**

### Axe 3 — Observabilité / debuggability post-mortem

Le `usage.py` log des events JSONL et `scripts/usage_summary.py` synthétise. Mais :
- En cas d'incident production (sous-question incorrecte qui mène à un avis MdT erroné), comment **rejoue-t-on l'événement** précisément ?
- Le log JSONL contient-il **tout ce nécessaire** pour reconstruire la décomposition (pas seulement les scores) ?
- Comment détecter le **drift** d'une matrice dispatch obsolète (modèles cités dépréciés en 2027) ?
- Comment **tester** que le filtre PII racine (`_PIIRedactFilter`) attrape vraiment tout, en conditions réelles avec sentence-transformers logs HF Hub ?
- L'audit POLYLENS interne mentionne LangGraph checkpointer pour Phase C. Y a-t-il un equivalent **Phase A** plus modeste qui éviterait perte d'état complet en cas de crash ?
- Le repo n'a pas de `CHANGELOG.md` malgré 15 commits — comment un futur auditeur ou collaborateur **comprendra-t-il l'évolution** des décisions ?

**Cible : ≥3 findings observabilité / debuggability.**

### Axe 4 — Cas limites usage médecin du travail réels (scénarios d'échec)

Le projet est conçu pour un médecin du travail français. Dans la pratique réelle :

- **Question multidomaine forcée** : "Inaptitude RPS pour soudeur exposé Mn / Cr VI : cadre légal + biomarqueurs + recommandations" → la matrice dispatch tombe sur `domain="mixte"` (axes génériques) et perd la spécialisation. Pertinent ?
- **Question contenant terminologie HAS périmée** : la décomposition heuristique préserve-t-elle les termes obsolètes que le médecin emploie ?
- **Question opposable** (avis judiciaire) : Phase A produit la décomposition, mais le user n'a aucune indication "**ne pas utiliser comme élément opposable**" dans la sortie. Risque MdT : produit une décomposition + dispatch → user cite le rapport final comme "généré par AI" → litige.
- **Question avec controverse active** (ex : "VLE benzène à abaisser à 0.05 ppm en 2027 ?") : la décomposition sépare-t-elle bien position INRS vs ANSES vs syndicats employeurs ? Ou agrège silencieusement ?
- **Question multilingue (UE)** : "Comparaison Mn neurotoxicité OEL FR vs DE vs ES 2026" — domain="multilingue" mais terminologie médicale spécifique ?
- **Question sur cas individuel anonymisé** : "Salarié exposé Cr VI 25 ans soudure inox, fonction respiratoire altérée, demande aptitude poste équivalent" → relève RGPD strict même anonymisé. La décomposition produit-elle une trace AIPD-friendly ?

**Cible : ≥3 cas d'usage concrets que le pipeline gère mal + correction proposée.**

### Axe 5 — Benchmarking empirique gain v0.3 vs v0.2

Le projet a évolué v0.1 → v0.2 (POLYLENS) → v0.3 (audit V1). Mais :
- Y a-t-il un **benchmark empirique** mesurable que les axes par domaine v0.3 produisent meilleure orthogonalité que les axes uniformes v0.2 ?
- Le `quality.overall` pondéré v0.3 produit-il des scores **systématiquement plus élevés** ou pénalisants sur les 5 cas réels vs équipondération v0.2 ?
- L'A/B Linear vs Graph testé sur 5 cas est-il **statistiquement valide** (n=5 = puissance ridicule) ?
- Faut-il créer un **benchmark interne** sur 30-50 cas synthétiques (générés par LLM ou puisés dans logs Phase A après 7+ jours) avant de s'engager Phase B ?
- Comment mesurer que la **valeur ajoutée vs Perplexity Pro DR seul** justifie réellement les 35-50 j-h Phase B ?

**Cible : protocole de validation empirique chiffrée + critères Go/No-Go Phase B basés sur métriques (pas seulement intuitions).**

## Format de sortie attendu

Pour chaque finding orthogonal :

```
[AXE-N] [P0|P1|P2|P3] Titre court (≤ 80 chars)

Fichier:ligne (citation exacte ≤ 3 lignes) ou référence externe.
Problème : 2-3 lignes max.
Mitigation proposée : 1-3 lignes max, code patch idéalement.
Référence externe (si pertinent) : URL vérifiable.
```

Sévérités :
- **P0** = bloquant, à fixer avant Phase B
- **P1** = à fixer Phase B sprint 1
- **P2** = à fixer Phase B sprint 2-3
- **P3** = backlog Phase C

## Règles dures

- **Audit ORTHOGONAL** : si tu vois un finding déjà couvert par les 4 voix V1 (les 18 listés) ou par l'audit Gemini V2 (axes Vertex/multimodalité/Google Search), marque-le « DÉJÀ FIXÉ commit X » ou « TRAITÉ V2 Gemini » et passe au suivant
- **≥3 findings substantiels par axe** (5 axes × 3 = 15 minimum nouveaux)
- **Citations vérifiables** : code repo (fichier:ligne) ou URL externe
- **Réponse en français concis ≤ 2500 mots**
- Termine par : (a) verdict synthétique 1 paragraphe, (b) **3 actions prioritaires Phase B** spécifiques aux angles que tu as détectés mieux que Gemini ou les 4 voix V1, (c) **score de confiance** (sur 10) que Phase A v0.3 est prête pour Phase B

## Sortie souhaitée

1. Tableau récap findings par axe + sévérité
2. Détails par finding (format ci-dessus)
3. Verdict synthétique
4. **3 actions prioritaires Phase B**
5. **Score Phase B-readiness /10** avec justification
6. Sources externes citées (10-20 URLs)

Bon audit.
