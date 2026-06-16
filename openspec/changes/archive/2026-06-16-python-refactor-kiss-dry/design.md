## Context

Le pipeline `git-release` est une Cloud Run Job Python qui orchestre : fetch GitHub/GCP Docs/Changelog → analyse LLM (Mistral) → stockage R2 → notifications Telegram. Le code est réparti en ~10 modules. La dette a été introduite incrementalement via des features successives (Telegram, GCP Docs, dbt-fusion) sans consolidation.

État actuel des dépendances inter-modules :
```
analyser.py → fetcher.py  (pour filter_trivial_changes, heuristic_dbt_analysis)
security_advisories.py → analyser.py  (lazy import)
digest.py → store.py
pipeline.py → tout le reste
```

## Goals / Non-Goals

**Goals:**
- Supprimer toutes les duplications identifiées sans changer le comportement observable
- Réduire la complexité de `pipeline.py` (585 loc) en extrayant des responsabilités clairement délimitées
- Couper la dépendance `analyser → fetcher` (risque de cycle)
- Typer `telegram_config` pour éliminer les `.get()` défensifs en cascade
- Passer les tests existants sans modification

**Non-Goals:**
- Refonte de l'architecture (pas de nouveaux modules, pas de changement d'interface publique)
- Optimisation des performances
- Ajout de tests supplémentaires (les tests existants servent de filet de sécurité)
- Modifier le comportement de `heuristic_dbt_analysis` (reste dans `fetcher.py`)

## Decisions

### D1 — Extraire `_analyse_with_model` dans `analyser.py`

**Problème** : 5 fonctions `analyse_*` répètent le même pattern :
```python
try:
    data = json.loads(_call_mistral(prompt, api_key))
    result = SomeModel(**data)
    return result.model_dump(), None
except ValidationError as e:
    logger.error("...", ...)
    return None, str(e)
except Exception as e:
    logger.error("...", ...)
    return None, str(e)
```

**Décision** : helper interne générique avec signature :
```python
def _analyse_with_model(
    prompt: str,
    api_key: str,
    model_cls: type[BaseModel],
    context: str,  # pour les logs, ex: "dbt-labs/dbt-core@v1.9.0"
) -> tuple[dict[str, object] | None, str | None]:
```

**Alternatif écarté** : decorator — plus complexe, n'apporte rien ici car les 5 fonctions ont déjà des signatures différentes.

### D2 — `TelegramConfig` comme `TypedDict`

**Problème** : `main.py` construit `{"bot_token": ..., "channels": {...}}` et `pipeline.py` le dépackage avec `.get()` — aucun contrat de type.

**Décision** : `TypedDict` dans `src/config.py` (déjà le module des constantes) :
```python
class TelegramConfig(TypedDict):
    bot_token: str
    channels: dict[str, str]
```

**Alternatif écarté** : `dataclass` — TypedDict est plus léger et compatible JSON-like sans overhead, cohérent avec le style du projet.

### D3 — Centraliser `load_repos()` dans `pipeline.py`, utilisé par `digest.py`

**Problème** : `pipeline.py::load_repos()` et `digest.py::_load_repo_overrides()` lisent le même `repos.json` avec une logique divergente.

**Décision** : `load_repos()` dans `pipeline.py` retourne déjà `list[dict[str, str]]`. `digest.py` l'importe directement au lieu de relire le fichier. Pas de nouveau module.

**Alternatif écarté** : déplacer dans `config.py` — trop couplé à la logique métier (normalisation str→dict) pour être une constante.

### D4 — Déplacer `filter_trivial_changes` dans `analyser.py`

**Problème** : `analyser.py` importe `fetcher.py` uniquement pour `filter_trivial_changes` et `heuristic_dbt_analysis`. `filter_trivial_changes` est conceptuellement du post-traitement LLM, pas du fetching.

**Décision** : déplacer `filter_trivial_changes` dans `analyser.py`. `heuristic_dbt_analysis` reste dans `fetcher.py` (elle utilise `parse_semver` et les patterns de fetching — son déplacement sortirait du scope).

**Impact** : `fetcher.py` n'aura plus d'import depuis `analyser.py`. La dépendance circulaire latente disparaît.

### D5 — `_github_headers()` unique dans `fetcher.py`

**Décision** : fusionner `_headers_base` et `_headers` en :
```python
def _github_headers(token: str | None, *, accept: str = "application/vnd.github+json") -> dict[str, str]:
```
`security_advisories.py` importe `_github_headers` depuis `fetcher` au lieu de reconstruire inline.

**Note** : `_github_headers` reste une fonction "privée" (underscore), l'import cross-module est acceptable car `security_advisories` est dans le même package `src/`.

## Risks / Trade-offs

- **[Risque] Import `_github_headers` depuis `security_advisories`** → `fetcher` devient une dépendance de `security_advisories`. Acceptable car ils sont dans le même domaine (GitHub API). Mitigation : la fonction est simple, sans effets de bord.

- **[Risque] `digest.py` importe `load_repos` depuis `pipeline`** → crée une dépendance `digest → pipeline`. Mitigation : `load_repos` est une fonction pure (lecture fichier + normalisation) qui pourrait être extraite dans un module `repos.py` si la dépendance devient problématique — hors scope pour l'instant.

- **[Trade-off] `heuristic_dbt_analysis` reste dans `fetcher.py`** → la dépendance `analyser → fetcher` n'est pas totalement coupée (l'import de `heuristic_dbt_analysis` demeure dans `analyse_dbt_package_release`). Acceptable : déplacer `heuristic_dbt_analysis` nécessiterait de déplacer aussi les patterns `_TRIVIAL_CHANGE_PATTERNS` et `_PROD_BREAKING_BUG_PATTERNS`, ce qui grossit le scope sans gain net.

## Migration Plan

Pas de migration de données. Les changements sont purement internes au code Python :
1. Tous les changements se font sur la branche `chore/python-refactor-kiss-dry`
2. Ordre d'implémentation : A (quick fixes) → B (analyser) → C (pipeline) → D (fetcher/digest)
3. `pytest` après chaque groupe pour vérifier l'absence de régression
4. Merge vers `feat/scaffold` via PR normale
