## 1. Config

- [x] 1.1 Add `DIGEST_DOMAINS` (domain → groups) and `DIGEST_DOMAIN_LIMITS` (`scaleway`: 300) to `src/config.py`

## 2. Digest writing

- [x] 2.1 Add a pure helper that splits records into domains by group and applies the caps, with a warning for unmapped groups
- [x] 2.2 Extend `write_digest_json` to write `digest-<domain>-<ts>.json` files and add `digests` to `manifest.json`, keeping `digest`
- [x] 2.3 Write the `security` digest from advisories only

## 3. Cleanup

- [x] 3.1 In `_build_and_clean_digest`, delete only digest files absent from the new manifest

## 4. Tests

- [x] 4.1 Test domain routing and unmapped group handling
- [x] 4.2 Test the Scaleway cap does not remove dbt-adapter records (27 adapters + 338 scaleway fixture)
- [x] 4.3 Test manifest shape and cleanup keep-set
- [x] 4.4 Run `pytest`, `ruff check`, `black --check`, `mypy --strict src`

## 5. Verify

- [ ] 5.1 After deploy, read `manifest.json` and confirm `digests.dbt` lists all stored dbt-adapter releases
