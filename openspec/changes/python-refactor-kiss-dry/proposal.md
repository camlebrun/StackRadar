## Why

Le codebase contient plusieurs violations DRY et KISS accumulées au fil des features : un bloc try/except LLM dupliqué 5 fois, des headers GitHub définis dans deux modules différents, un `_GCP_VALID_TAGS` littéralement copié-collé deux fois dans le même fichier, et une logique de routing Telegram de 50 lignes enfouie dans `run_pipeline`. Ces dettes augmentent le risque de régression à chaque évolution et ralentissent la compréhension du code.

## What Changes

- **Suppression du doublon `_GCP_VALID_TAGS`** dans `pipeline.py` (la deuxième définition identique écrase silencieusement la première)
- **Ajout de `_advisory_cursor_key()`** dans `store.py` (la clé `meta/advisory-cursor/{owner}/{repo}.json` est inlinée deux fois sans helper)
- **Unification des helpers de headers GitHub** dans `fetcher.py` (`_headers_base` et `_headers` fusionnés en un seul `_github_headers`)
- **Suppression du wrapper vide `call_llm()`** dans `analyser.py` (simple redirection sans valeur ajoutée, remplacé par appel direct)
- **Extraction de `_analyse_with_model()`** dans `analyser.py` : les 5 fonctions `analyse_*` partagent le même pattern try/except/log/validate — factorisé en un helper générique
- **Extraction de `_route_telegram()`** dans `pipeline.py` : 50 lignes de routing inline extraites dans une fonction dédiée
- **`TelegramConfig` TypedDict** partagé entre `main.py` et `pipeline.py` (remplace le dict non typé traversant 3 couches)
- **Centralisation du chargement `repos.json`** : `load_repos()` dans `pipeline.py` et `_load_repo_overrides()` dans `digest.py` lisent le même fichier avec une logique divergente — unifié en une seule fonction
- **Déplacement de `filter_trivial_changes()`** de `fetcher.py` vers `analyser.py` pour couper la dépendance `analyser → fetcher`

## Capabilities

### New Capabilities

- `llm-analysis-helper`: Helper générique `_analyse_with_model` qui encapsule le pattern commun d'appel LLM + validation Pydantic + gestion d'erreur
- `telegram-routing`: Fonction dédiée `_route_telegram` isolant la logique de dispatch par canal des responsabilités de `run_pipeline`
- `repos-loader`: Chargement canonique de `repos.json` partagé entre pipeline et digest

### Modified Capabilities

_(aucun changement de comportement observable — refacto interne uniquement)_

## Impact

- **`src/pipeline.py`** : suppression doublon `_GCP_VALID_TAGS`, extraction `_route_telegram`, `TelegramConfig` TypedDict, centralisation `load_repos`
- **`src/analyser.py`** : extraction `_analyse_with_model`, déplacement `filter_trivial_changes` depuis `fetcher`, suppression `call_llm` wrapper
- **`src/fetcher.py`** : fusion `_headers_base`/`_headers` → `_github_headers`, retrait de `filter_trivial_changes`
- **`src/store.py`** : ajout `_advisory_cursor_key()` helper
- **`src/main.py`** : adoption `TelegramConfig` TypedDict
- **Tests** : aucun test à modifier — les APIs publiques restent identiques
