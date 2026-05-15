# Example Architecture Review Excerpt

This excerpt is adapted from `C:\10.CODE\CalSyncReturns\ARCHITECTURE_DRIFT_REVIEW.md`. Use it as a style and specificity reference, not as reusable findings for other repositories.

## Summary Table Excerpt

| Rank | Drift | Docs asked | Code shows |
|---|---|---|---|
| Substantial diversion | Yandex/CalDAV authoritative deletion detection is not implemented end-to-end. | Architecture requires deletion only when authoritative scans prove absence, and Yandex docs require live resource plus live VEVENT inventories: `docs/ARCHITECTURE.md:306`, `docs/YANDEX_CALDAV.md:51`, `docs/YANDEX_CALDAV.md:168`. | Code stores scan scopes and has a helper to detect missing hrefs, but ingestion only upserts seen events and reconciliation deletes only cancelled/deleted/tombstone-like source rows: `src/ingestion/ingest.ts:278`, `src/providers/yandex/normalize.ts:30`, `src/reconciliation/reconcile.ts:1018`. |
| Substantial diversion | Source-wins conflict policy does not detect manual target-clone edits. | Docs say source wins for managed clones, and manual target edits should be logged before overwrite: `docs/APPROACH.md:268`. | Reconciler noops when `last_projection_hash` matches the current source projection, without reading target clone state or comparing an observed target hash. Outbox sets `last_target_hash = last_projection_hash`, not an observed target hash: `src/reconciliation/reconcile.ts:390`, `src/outbox/process.ts:287`. |
| Moderate drift | Dual ingestion exists as pieces, but no orchestrator runs both change feed and active-window lanes for a calendar lifecycle. | Dual ingestion is an ADR and ingestion lifecycle expects change feed plus active-window scan: `docs/DECISIONS.md:16`, `docs/ARCHITECTURE.md:168`. | `ingestCalendar` runs one passed strategy; `runChangeFeedCycle` runs change feed then reconciliation, but no active-window pass: `src/ingestion/ingest.ts:210`, `src/sync/runChangeFeedCycle.ts:34`. |

## Detailed Issue Excerpt

## Issue 1. Yandex/CalDAV Authoritative Deletion Detection Is Not End-to-End

Rank: Substantial diversion

### Architecture references

- `docs/ARCHITECTURE.md:289` defines deletion as lifecycle state, not a simple boolean.
- `docs/ARCHITECTURE.md:306` says target clones should be deleted only when a source has an active `sync_link` and is explicitly deleted, cancelled, declined, or absent from an authoritative scan.
- `docs/SCHEMA.md:165` defines `scan_scopes` so deletion logic can distinguish authoritative scans from narrow scans.
- `docs/PROVIDER_NOTES.md:180` says Yandex/CalDAV deletion detection must use href inventory plus event-key history.
- `docs/YANDEX_CALDAV.md:51` requires both live resource href inventory and live event key inventory.

### Implementation evidence

- `src/providers/yandex/normalize.ts:30` exposes `findMissingYandexResourceHrefs`, but this is only a helper and is not wired into ingestion/reconciliation.
- `src/ingestion/ingest.ts:278` upserts current snapshots for normalized events that were seen, but does not mark previously linked events as `missing_from_authoritative_scan`.
- `src/reconciliation/reconcile.ts:1018` treats `cancelled`, `deleted_by_provider`, `cancelled_instance`, and `provider_tombstone` as deleted sources.
- `src/reconciliation/reconcile.ts:1018` does not treat `missing_from_authoritative_scan` as a deleted source, even though that lifecycle state exists in the schema.

### Why this matters

The clone manager architecture deliberately avoids deleting target events from weak evidence. That is good. But the opposite failure is now present: when a Yandex resource or one VEVENT inside a multi-VEVENT resource disappears, the system has no end-to-end path to convert that absence into lifecycle state and then into a delete outbox operation for linked clones.

This creates stale clones in the target calendar after real Yandex deletions or recurrence-exception removals.

### What needs to be done

Implement an authoritative deletion sweep for Yandex/CalDAV inventory runs.

At a high level:

- During authoritative Yandex inventory scans, collect live resource hrefs and live provider event keys.
- Compare live resource hrefs and event keys against prior `provider_event_current` rows and active `sync_links`.
- Mark missing linked source events as `missing_from_authoritative_scan` only when the scan scope is authoritative for those event keys.
- Distinguish missing because outside the current window from missing because the authoritative inventory proved absence.
- Make reconciliation treat `missing_from_authoritative_scan` as deletion-eligible only for linked clones.

### Completion checklist

- [ ] Add Yandex inventory comparison logic that computes live resource hrefs and live event keys from a completed authoritative scan.
- [ ] Update previous linked Yandex source events under missing resource hrefs to `missing_from_authoritative_scan` or another documented deletion lifecycle state.
- [ ] Update previous linked Yandex source events for missing VEVENT keys inside still-present resources.
- [ ] Ensure narrowed active-window absence is not treated as deletion.
- [ ] Update reconciliation logic so `missing_from_authoritative_scan` creates delete decisions only when a link exists.
- [ ] Add DB tests proving missing Yandex resource href enqueues target delete for active links.
