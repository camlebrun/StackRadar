## Context

`_build_and_clean_digest` calls `get_digest(limit=500)`, which lists every stored release, sorts by `published_at` and truncates. With 665 stored releases and Scaleway producing most recent entries, older sources fall off: dbt-adapters 27 stored → 3 served, dbt-packages 130 → 46. The frontend has six pages that each fetch the whole 742 KB digest (uncompressed on the `r2.dev` URL) and filter client-side.

## Goals / Non-Goals

**Goals:**
- No source loses releases because of another source's volume.
- Each page can download only its domain.
- Ship without touching the deployed frontend.

**Non-Goals:**
- Changing the stored release records or their keys.
- Compression or a custom domain for R2 (separate decision, see Open Questions).
- Removing the combined digest (done in the frontend redesign change).

## Decisions

1. **Group by domain, not by repo.** Four domains match the frontend's navigation (dbt, GCP, Scaleway, Security). One file per repo would be 16 requests; one file for everything is today's problem. The `group` field already exists on every record, so routing needs no new data.
2. **Cap only Scaleway.** It is the only source whose volume is unbounded (RSS entries, 338 and growing). The other domains are bounded by `min_version`/`minor_only` filters, so a cap there could only reintroduce the bug. Alternative considered: a uniform cap per domain; rejected because any value either truncates dbt-packages or does nothing.
3. **Keep the combined digest and `manifest.digest` for now.** The deployed pages read `manifest.digest`. Writing both lets this change ship and be verified before the redesign switches over. It costs one extra 700 KB write per run, within R2's free tier.
4. **Domain files are immutable and timestamped**, like the combined digest (`Cache-Control: immutable`), with the manifest as the only mutable pointer. Same cache behaviour the frontend already relies on.
5. **Routing table lives in `src/config.py`** (`DIGEST_DOMAINS`, `DIGEST_DOMAIN_LIMITS`) so adding a source group is a one-line change.

## Risks / Trade-offs

- [Records with an unmapped `group` vanish from domain digests] → they stay in the combined digest, and a log warning names the group.
- [Cleanup deletes a file the manifest still references] → build the keep-set from the manifest payload before deleting; covered by a test.
- [Extra writes per run] → 4 small PUTs, negligible.

## Migration Plan

1. Deploy: the next scheduled run writes domain digests and the extended manifest. The old frontend ignores `digests`.
2. Verify `manifest.digests.dbt` contains all 27 adapter releases.
3. The frontend redesign switches to `manifest.digests`; a later cleanup change drops the combined digest.
Rollback: revert the commit; the next run rewrites a manifest without `digests`.

## Open Questions

- Serve R2 through a custom domain to get gzip/brotli (742 KB → ~100 KB)? Needs a DNS decision.
