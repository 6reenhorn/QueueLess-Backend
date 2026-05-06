# Seed Data Management

This document provides instructions on how to use the custom management commands to seed and manage mock data for the QueueLess Backend.

## 1. Seeding Mock Data
The `seed_mock_data` command is used to populate the database with mock institutions and queue entries for simulation.

### Basic Seeding
Populate the database with default institutions and a random number of queue entries:
```bash
python manage.py seed_mock_data
```

### Resetting to a Clean State
If you want to clear all existing data (institutions and queues) and start fresh from Ticket #1:
```bash
python manage.py seed_mock_data --flush
```

### Simulating Closed Institutions
To randomly set a specific number of institutions to `CLOSED` status for testing "Unavailable" states:
```bash
python manage.py seed_mock_data --close-count 3
```

## 2. Advanced Options

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--flush` | flag | N/A | Deletes ALL institutions and queue entries before seeding. |
| `--close-count` | int | 0 | Number of institutions to randomly set as CLOSED. |
| `--min-queue` | int | 5 | Minimum random queue entries per institution. |
| `--max-queue` | int | 12 | Maximum random queue entries per institution. |
| `--skip-queues` | flag | N/A | Create institutions only, skip generating queue entries. |
| `--reset-queues`| flag | N/A | Deletes queue entries for seeded institutions only (keeps non-seeded ones). |

## 3. Example Scenarios

**Scenario A: High Traffic Simulation**
```bash
python manage.py seed_mock_data --min-queue 50 --max-queue 100
```

**Scenario B: Limited Availability Test**
```bash
python manage.py seed_mock_data --flush --close-count 5
```

**Scenario C: Empty Institutions Only**
```bash
python manage.py seed_mock_data --flush --skip-queues
```
