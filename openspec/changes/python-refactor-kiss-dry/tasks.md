## 1. Groupe A — Corrections immédiates

- [x] 1.1 Supprimer la deuxième définition dupliquée de `_GCP_VALID_TAGS` dans `src/pipeline.py` (lignes ~126–144)
- [x] 1.2 Ajouter le helper `_advisory_cursor_key(owner, repo)` dans `src/store.py` et l'utiliser dans `get_advisory_cursor` et `set_advisory_cursor`
- [x] 1.3 Fusionner `_headers_base` et `_headers` en `_github_headers(token, *, accept)` dans `src/fetcher.py` et mettre à jour tous les appels internes
- [x] 1.4 Supprimer le wrapper `call_llm()` dans `src/analyser.py` et mettre à jour `src/security_advisories.py` pour appeler `_call_mistral` directement (import depuis `analyser`)

## 2. Groupe B — Factorisation LLM dans analyser.py

- [x] 2.1 Déplacer `filter_trivial_changes` de `src/fetcher.py` vers `src/analyser.py`
- [x] 2.2 Mettre à jour les imports dans `src/fetcher.py` (retirer la définition) et `src/analyser.py` (retirer l'import depuis fetcher)
- [x] 2.3 Implémenter `_analyse_with_model(prompt, api_key, model_cls, context)` dans `src/analyser.py`
- [x] 2.4 Refactorer `analyse_release` pour utiliser `_analyse_with_model`
- [x] 2.5 Refactorer `analyse_fusion_release` pour utiliser `_analyse_with_model`
- [x] 2.6 Refactorer `analyse_bigquery_release` pour utiliser `_analyse_with_model`
- [x] 2.7 Refactorer `analyse_lakehouse_release` pour utiliser `_analyse_with_model`
- [x] 2.8 Refactorer `analyse_fusion_historical` pour utiliser `_analyse_with_model`
- [x] 2.9 Refactorer `analyse_dbt_package_release` pour utiliser `_analyse_with_model` (cas LLM uniquement)

## 3. Groupe C — Pipeline et configuration Telegram

- [x] 3.1 Définir `TelegramConfig` comme `TypedDict` dans `src/config.py`
- [x] 3.2 Mettre à jour `src/main.py` pour construire et typer `TelegramConfig`
- [x] 3.3 Mettre à jour la signature de `run_pipeline` dans `src/pipeline.py` pour accepter `TelegramConfig | None`
- [x] 3.4 Extraire `_route_telegram(repos, new_records, new_advisories, failed_repos, config)` dans `src/pipeline.py`
- [x] 3.5 Remplacer le bloc inline (lignes ~537–581) par un appel à `_route_telegram` dans `run_pipeline`

## 4. Groupe D — Chargement repos.json

- [x] 4.1 Vérifier que `load_repos()` dans `src/pipeline.py` préserve tous les champs nécessaires à `digest.py` (deprecated, notice, group, type, etc.)
- [x] 4.2 Supprimer `_load_repo_overrides()` dans `src/digest.py`
- [x] 4.3 Dans `src/digest.py`, importer `load_repos` depuis `src.pipeline` et construire le `deprecated_map` à partir du résultat
- [x] 4.4 Importer `_github_headers` depuis `src.fetcher` dans `src/security_advisories.py` et supprimer la construction inline des headers

## 5. Validation finale

- [x] 5.1 Lancer `pytest` et vérifier que tous les tests passent
- [x] 5.2 Lancer `mypy` (ou `pyright`) et vérifier l'absence de nouvelles erreurs de typage
- [x] 5.3 Lancer `ruff check src/` et vérifier l'absence de nouveaux warnings
