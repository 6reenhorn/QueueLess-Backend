# QueueLess API Endpoints and Load Profile

This document summarizes the mock queue API exposed by the backend and the expected load characteristics of each endpoint. The load notes are relative, not benchmark numbers. Actual throughput depends on database size, concurrent users, network latency, and deployment tier.

## Base Paths

- Mock institution API: `/api/institutions/`
- Queue API: `/api/queue/`

The mock routes are controlled by `ENABLE_MOCK_API`. If that flag is disabled, these routes are not exposed.
The institution records in this backend are simulated data until a real institutions provider is connected.

## Endpoints

| Method | Path | Access | Purpose | Load Profile |
| --- | --- | --- | --- | --- |
| GET | `/api/institutions/` | Public | Lists institutions with queue summary fields. | Low to medium. One query with annotations; scales well for small and medium institution counts. |
| GET | `/api/institutions/{id}/` | Public | Returns one institution with queue summary fields. | Low. Single-row lookup with annotations. |
| POST | `/api/queue/join/` | Public | Creates a queue entry for an institution. | Low per request, but write-heavy under spikes. Uses row locking and retry logic to stay safe under concurrency. |
| GET | `/api/queue/entries/{session_id}/status/` | Public | Returns the status of one queue entry. | Low. Single lookup by session ID. |
| GET | `/api/queue/institutions/{institution_id}/entries/` | Admin only | Lists queue entries for one institution. | Medium to high depending on queue size. This can return many rows, so it is the most likely endpoint to grow expensive. |
| POST | `/api/queue/institutions/{institution_id}/simulate-tick/` | Admin only | Advances the queue and generates notifications. | Medium. Uses bulk updates and bulk inserts, so it stays efficient even when several entries move at once. |

## Load Notes By Endpoint

### `GET /api/institutions/`

This endpoint is optimized for frontend dashboards and public browsing. The queryset is annotated at the database level, so it avoids N+1 query patterns. For typical usage, the load is light. It becomes more expensive only if the institutions table grows very large.

### `GET /api/institutions/{id}/`

This is a single-record read with queue summary annotations. It is one of the cheapest routes in the API.

### `POST /api/queue/join/`

This endpoint does a write and also handles concurrency safely. Under normal traffic it is light. Under burst traffic, it can create contention because multiple users may try to claim the next queue number at the same time. The implementation mitigates this with transaction locking and retry handling, but the database is still the limiting factor.

### `GET /api/queue/entries/{session_id}/status/`

This is a simple status lookup. It is low load and should remain cheap even with frequent polling.

### `GET /api/queue/institutions/{institution_id}/entries/`

This endpoint can become expensive if an institution has a long queue history or many active entries, because it returns the full entry list for that institution. It is still acceptable for admin use, but it is not the route to expose to high-frequency frontend polling without pagination.

### `POST /api/queue/institutions/{institution_id}/simulate-tick/`

This endpoint is designed to stay efficient even when multiple entries need updates. Served and near-turn entries are handled with bulk operations, so the database cost is closer to a small fixed number of queries rather than one query per entry. The load is moderate, mainly because it still has to scan the institution's active queue state.

## Practical Capacity Guidance

- Best for light to moderate frontend traffic: institution listing, single institution detail, and queue status lookup.
- Best for occasional writes: queue join requests.
- Best for admin-only operational use: institution queue inspection and queue simulation.
- Not yet optimized for large-scale public polling of full queue lists without pagination.

## Operational Recommendations

- Keep `ENABLE_MOCK_API=False` in production unless these routes are intentionally needed.
- Add pagination before exposing institution queue lists to heavy traffic.
- Use the status endpoint for frontend polling instead of repeatedly fetching full queue lists.
- Keep CORS restricted to known frontend origins only.

## Notes

These endpoints are intentionally mock-friendly and test-friendly. They are suitable for frontend integration, demo flows, and queue simulation, but they are not a substitute for measured production capacity testing.
Institution names, statuses, and queue states are simulated and should not be treated as authoritative live data.
