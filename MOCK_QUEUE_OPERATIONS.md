# Mock Queue Operations Guide

This guide explains how to use the mock institution and queue data in the QueueLess Backend.

## What The Mock Data Does

- The institution list is simulated because there is no real institutions API connected yet.
- Queue entries are stored in the database so the frontend can query stable state.
- Queue movement does not happen automatically in the background.
- Queue progression happens when an admin calls the simulation endpoint.

## How To Use It

### 1. Enable The Mock Routes

Make sure `ENABLE_MOCK_API=True` in your `.env` file.

### 2. Seed The Mock Data

Run the management command from the backend project directory:

```powershell
python manage.py seed_mock_data
```

This creates mock institutions and sample queue entries.

### 3. Start The Backend

```powershell
python manage.py runserver
```

### 4. Join A Queue From The Frontend

Use the public join endpoint:

- `POST /api/queue/join/`

This creates a queue entry for the selected institution and returns the session-based status payload.

### 5. Check Queue Status

Use the public status endpoint:

- `GET /api/queue/entries/{session_id}/status/`

This is the endpoint the frontend can poll to show the user their current position and state.

### 6. Advance The Queue Manually

Use the admin-only simulation endpoint:

- `POST /api/queue/institutions/{institution_id}/simulate-tick/`

This is what moves the queue forward, marks entries as served, and sends near-turn notifications.

## Does The Queue Auto-Update?

No, not by itself.

The queue only advances when:

- a user joins the queue, which creates a new entry, or
- an admin triggers the simulation endpoint to simulate a queue tick.

If the frontend wants live-looking updates, it should poll the status endpoint on an interval or refresh after a simulate tick is triggered.

## Admin Behavior

- `GET /api/queue/institutions/{institution_id}/entries/` is admin only and shows queue entries for one institution.
- `POST /api/queue/institutions/{institution_id}/simulate-tick/` is admin only and is the only route that advances the queue state.

## Practical Workflow

1. Seed the mock data.
2. Open the frontend and join a queue.
3. Poll the status endpoint to watch the user move from waiting to notified to served.
4. Use the simulation endpoint whenever you want to advance the queue for testing.

## Notes

- The data is intentionally mock-only until a real institutions provider is available.
- The queue is suitable for frontend demos, testing, and walkthroughs.
- For production-style behavior, replace the simulation flow with a real queue source and real operational triggers.
