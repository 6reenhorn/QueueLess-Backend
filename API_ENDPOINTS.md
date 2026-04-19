# QueueLess API Endpoints, Contracts, and Load Profile

This document defines the mock API contracts used by the frontend:

- endpoint paths and methods
- request parameters and body fields
- response body shapes
- common error responses
- relative load profile

Load notes are qualitative, not benchmark numbers. Actual capacity depends on deployment size, database performance, and traffic patterns.

## Scope and Base Paths

- Institution API base: `/api/institutions/`
- Queue API base: `/api/queue/`

Institution data is simulated and should not be treated as authoritative live data until a real provider is integrated.
Mock routes are controlled by `ENABLE_MOCK_API`.
If disabled, these routes are not exposed.

## Summary Table

| Method | Path | Access | Purpose | Load |
| --- | --- | --- | --- | --- |
| GET | `/api/institutions/` | Public | List institutions with queue summary fields | Low to medium |
| GET | `/api/institutions/{id}/` | Public | Get one institution with queue summary fields | Low |
| POST | `/api/queue/join/` | Public | Join queue for an institution | Low per call, write-heavy in spikes |
| GET | `/api/queue/entries/{session_id}/status/` | Public | Get status for one queue session | Low |
| GET | `/api/queue/entries/{session_id}/notifications/` | Public | List notifications for one queue session | Low |
| PATCH | `/api/queue/entries/{session_id}/notifications/{notification_id}/ack/` | Public | Update notification delivery state | Low |
| GET | `/api/queue/institutions/{institution_id}/entries/` | Admin only | List queue entries for one institution | Medium to high |
| POST | `/api/queue/institutions/{institution_id}/simulate-tick/` | Admin only | Advance queue state and generate notifications | Medium |

## Data Types and Enums

### Queue status values

- `waiting`
- `notified`
- `served`
- `expired`
- `cancelled`

### Boolean query parser behavior

For query params that accept boolean values (for example `active_only`, `randomize`):

- truthy: `1`, `true`, `t`, `yes`, `y`, `on`
- falsy: `0`, `false`, `f`, `no`, `n`, `off`

- any other value falls back silently to the parameter's default value; the backend does not return `400 Bad Request` for unrecognized boolean-like input
- defaults are endpoint-specific; for example, `active_only` and `randomize` currently fall back to `true`

## Endpoint Contracts

## GET /api/institutions/

### Access

Public

### Query params

None

### Success response

Status: `200 OK`

```json
[
  {
    "id": 1,
    "name": "Civil Service Commission",
    "institution_type": "government",
    "address": "Quezon City",
    "api_endpoint": "",
    "status": "open",
    "is_active": true,
    "is_available_for_queue": true,
    "queue_waiting_count": 14,
    "current_serving_number": 23,
    "next_queue_number": 38
  }
]
```

### Load note

Low to medium. Queryset uses database annotations to avoid N+1 behavior.

## GET /api/institutions/{id}/

### Access

Public

### Path params

- `id` (integer)

### Success response

Status: `200 OK`

```json
{
  "id": 1,
  "name": "Civil Service Commission",
  "institution_type": "government",
  "address": "Quezon City",
  "api_endpoint": "",
  "status": "open",
  "is_active": true,
  "is_available_for_queue": true,
  "queue_waiting_count": 14,
  "current_serving_number": 23,
  "next_queue_number": 38
}
```

### Common errors

- `404 Not Found` when institution does not exist.

### Load note

Low. Single-record fetch with queue summary annotations.

## POST /api/queue/join/

### Access

Public

### Request body

```json
{
  "institution_id": 1,
  "phone_number": "09171234567",
  "browser_push_opt_in": true,
  "near_turn_threshold": 3
}
```

### Body fields

- `institution_id` (integer, required, min 1)
- `phone_number` (string, optional, max 20)
- `browser_push_opt_in` (boolean, optional, default `false`)
- `near_turn_threshold` (integer, optional, min 1, max 10, default `3`)

### Success response

Status: `201 Created`

```json
{
  "session_id": "0e78ab8f-1f05-4741-8d73-e2d3778e9a35",
  "institution_id": 1,
  "queue_number": 42,
  "current_serving_number": 23,
  "status": "waiting",
  "near_turn_threshold": 3,
  "near_turn_notified": false,
  "issued_at": "2026-04-19T09:45:23.123456Z",
  "updated_at": "2026-04-19T09:45:23.123456Z",
  "people_ahead": 18
}
```

### Common errors

- `400 Bad Request`

```json
{
  "detail": "Institution is not currently available for queueing."
}
```

- `404 Not Found`

```json
{
  "detail": "Institution not found."
}
```

- `409 Conflict` (high concurrent join contention)

```json
{
  "detail": "Could not allocate a queue number due to concurrent requests. Please retry."
}
```

### Load note

Low per request but write-heavy under bursts. Uses transaction locking and retry logic for safe queue number allocation.

## GET /api/queue/entries/{session_id}/status/

### Access

Public

### Path params

- `session_id` (UUID)

### Success response

Status: `200 OK`

```json
{
  "session_id": "0e78ab8f-1f05-4741-8d73-e2d3778e9a35",
  "institution_id": 1,
  "queue_number": 42,
  "current_serving_number": 24,
  "status": "notified",
  "near_turn_threshold": 3,
  "near_turn_notified": true,
  "issued_at": "2026-04-19T09:45:23.123456Z",
  "updated_at": "2026-04-19T09:50:12.987654Z",
  "people_ahead": 2
}
```

### Common errors

- `404 Not Found`

```json
{
  "detail": "Queue entry not found."
}
```

### Load note

Low. Single lookup by session ID.

## GET /api/queue/entries/{session_id}/notifications/

### Access

Public

### Path params

- `session_id` (UUID)

### Query params

- `delivered` (optional boolean, filters notifications by delivery state; this parameter is parsed strictly, and invalid boolean-like values return `400 Bad Request` rather than silently falling back)
- `event_type` (optional string, one of `near_turn`, `turn_called`, `session_expired`, `generic`)
- `limit` (optional integer, defaults to `50`, maximum `100`)

### Success response

Status: `200 OK`

```json
{
  "session_id": "0e78ab8f-1f05-4741-8d73-e2d3778e9a35",
  "institution_id": 1,
  "queue_number": 42,
  "count": 2,
  "results": [
    {
      "id": 15,
      "session_id": "0e78ab8f-1f05-4741-8d73-e2d3778e9a35",
      "institution_id": 1,
      "queue_number": 42,
      "channel": "system",
      "event_type": "near_turn",
      "message": "Queue #42: please prepare, 2 ahead of you.",
      "delivered": false,
      "external_reference": "",
      "error_detail": "",
      "sent_at": "2026-04-19T09:49:12.000000Z",
      "updated_at": "2026-04-19T09:49:12.000000Z"
    }
  ]
}
```

### Common errors

- `400 Bad Request` for invalid `limit`, invalid `event_type`, or invalid `delivered`
- `404 Not Found` if the queue session does not exist

### Load note

Low. This is a session-scoped lookup with optional filtering and a capped result size.

## PATCH /api/queue/entries/{session_id}/notifications/{notification_id}/ack/

### Access

Public

### Path params

- `session_id` (UUID)
- `notification_id` (integer)

### Request body

```json
{
  "delivered": true,
  "external_reference": "push-abc-123",
  "error_detail": ""
}
```

### Body fields

- `delivered` (boolean, required)
- `external_reference` (string, optional, max 120)
- `error_detail` (string, optional)

### Success response

Status: `200 OK`

```json
{
  "id": 15,
  "session_id": "0e78ab8f-1f05-4741-8d73-e2d3778e9a35",
  "institution_id": 1,
  "queue_number": 42,
  "channel": "system",
  "event_type": "near_turn",
  "message": "Queue #42: please prepare, 2 ahead of you.",
  "delivered": true,
  "external_reference": "push-abc-123",
  "error_detail": "",
  "sent_at": "2026-04-19T09:49:12.000000Z",
  "updated_at": "2026-04-19T09:55:00.000000Z"
}
```

### Common errors

- `404 Not Found` if the queue session does not exist
- `404 Not Found` if the notification does not belong to the provided queue session

### Load note

Low. Single-row update on a notification record.

## GET /api/queue/institutions/{institution_id}/entries/

### Access

Admin only (`IsAdminUser`)

### Path params

- `institution_id` (integer)

### Query params

- `status` (optional, comma-separated queue statuses; when provided, this filter takes precedence and `active_only` is ignored)
- `active_only` (optional boolean, default `true` when `status` is not provided)

If both `status` and `active_only` are provided, the backend applies `status` filtering and does not combine it with `active_only`.

### Example requests

- `/api/queue/institutions/1/entries/`
- `/api/queue/institutions/1/entries/?active_only=false`
- `/api/queue/institutions/1/entries/?status=waiting,notified`

### Success response

Status: `200 OK`

```json
{
  "institution": {
    "id": 1,
    "name": "Civil Service Commission",
    "institution_type": "government",
    "status": "open",
    "is_active": true,
    "is_available_for_queue": true
  },
  "filters": {
    "status": "waiting,notified",
    "active_only": true
  },
  "count": 2,
  "results": [
    {
      "session_id": "d7fd3722-3fb3-413d-8874-294d2f539bc2",
      "queue_number": 41,
      "current_serving_number": 24,
      "status": "notified",
      "near_turn_notified": true,
      "near_turn_threshold": 3,
      "people_ahead": 1,
      "issued_at": "2026-04-19T09:40:10.000000Z",
      "updated_at": "2026-04-19T09:50:12.000000Z",
      "served_at": null,
      "expires_at": null
    }
  ]
}
```

### Common errors

- `400 Bad Request` for invalid `status` filter values

```json
{
  "detail": "Invalid status filter values provided.",
  "invalid_statuses": ["unknown_status"],
  "valid_statuses": ["cancelled", "expired", "notified", "served", "waiting"]
}
```

- `404 Not Found`

```json
{
  "detail": "Institution not found."
}
```

### Load note

Medium to high depending on queue size because this endpoint can return many rows.

## POST /api/queue/institutions/{institution_id}/simulate-tick/

### Access

Admin only (`IsAdminUser`)

### Path params

- `institution_id` (integer)

### Query params

- `randomize` (optional boolean, default `true`)

If `randomize=true`, increment is selected from `[0, 1, 1, 1, 2]`.
If `randomize=false`, increment is `1`.

### Success response

Status: `200 OK`

```json
{
  "institution_id": 1,
  "randomized": true,
  "increment": 1,
  "current_serving_number": 24,
  "served_count": 1,
  "notified_count": 2
}
```

### No active entries response

Status: `200 OK`

```json
{
  "institution_id": 1,
  "message": "No active queue entries to simulate."
}
```

### Common errors

- `404 Not Found`

```json
{
  "detail": "Institution not found."
}
```

### Load note

Medium. Uses bulk updates and bulk notification inserts to keep simulation efficient as entries grow.

### Notes

Notification creation in the current mock flow happens in the shared tick service, which is invoked by both this endpoint and the `queue_worker` management command. That shared logic marks served entries, promotes near-turn entries to `notified`, and creates the corresponding notification rows.

The response contract for this endpoint should follow the shared tick service output in all cases, including when there are no active entries to process. In particular, the "no active entries" response is not limited to a minimal `{ "institution_id": ..., "message": ... }` body; it includes the additional summary fields returned by the shared tick service as well.

## Operational Guidance

- Keep `ENABLE_MOCK_API=False` in production unless these routes are intentionally exposed.
- Use `/api/queue/entries/{session_id}/status/` for frontend polling instead of repeatedly fetching full institution queue lists.
- Add pagination before exposing institution-level queue lists to heavy polling.
- Keep CORS restricted to known frontend origins.

## Documentation Scope Note

This contract reflects the current backend implementation and serializer output fields.
If serializers or views change, update this document in the same pull request to keep frontend and backend aligned.
