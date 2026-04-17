# QueueLess Backend

The QueueLess Backend handles queue management and real-time updates for the QueueLess platform. It provides APIs that allow the frontend to show current queue status, customer positions, and notifications.

## Overview

QueueLess Backend is built to support smooth queue operations for businesses and customers. It keeps queue information accurate and up to date so users can monitor progress remotely.

## Features

- Manage queues in real time
- Track customer positions
- Send notifications when it is a customer's turn
- Provide APIs for frontend integration

## Purpose

Supports the frontend by keeping queue data accurate and updated, helping businesses manage queues efficiently and customers track their turn remotely.

## Tech Stack

- Django
- Django REST Framework
- django-cors-headers
- Channels

## Prerequisites

- Python 3.10+
- pip

## Quick Start

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies.
4. Create local environment variables.
5. Run migrations.
6. Start the development server.

### 1) Create Virtual Environment

```powershell
python -m venv venv
```

### 2) Activate Virtual Environment

Windows PowerShell:

```powershell
venv\Scripts\activate
```

Windows Command Prompt:

```bat
venv\Scripts\activate.bat
```

macOS/Linux:

```bash
source venv/bin/activate
```

### 3) Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4) Create Local Environment Variables

Copy the example environment file and customize values as needed.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Minimum variables for local development are documented in `.env.example`.

### Mock API Toggle

Mock institution and queue simulation routes are controlled by `ENABLE_MOCK_API`.

- `ENABLE_MOCK_API=True` enables `/api/` and `/api/queue/` mock routes.
- `ENABLE_MOCK_API=False` disables these mock routes.

If not set, `ENABLE_MOCK_API` defaults to the value of `DEBUG`.
For deployed environments, set `ENABLE_MOCK_API=False` unless mock endpoints are
explicitly required.

### 5) Run Migrations

```powershell
cd queueless_backend
python manage.py makemigrations
python manage.py migrate
```

### 6) Start Development Server

```powershell
python manage.py runserver
```

The API will be available at:

```text
http://127.0.0.1:8000/
```

## Automation

### GitHub Actions

- `ci.yml` runs Django system checks and tests on pushes and pull requests.
- `pre-commit.yml` runs formatting and lint checks on pull requests.

### Pre-commit

This project uses `pre-commit` as the Python-native alternative to Husky.

```powershell
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

### Testing and Linting

- `pytest` runs the automated test suite.
- `black` formats Python code.
- `isort` sorts imports.
- `flake8` checks for lint issues.

Run them locally with:

```powershell
pytest
black .
isort .
flake8
```

`pytest` works out of the box in this repository because
`DJANGO_SETTINGS_MODULE` is already configured in `pyproject.toml`.

If you run tests with a non-standard runner or custom shell setup, use this
fallback:

Windows PowerShell:

```powershell
$env:DJANGO_SETTINGS_MODULE = "queueless_backend.settings"
pytest
```

Windows Command Prompt:

```bat
set DJANGO_SETTINGS_MODULE=queueless_backend.settings
pytest
```

macOS/Linux:

```bash
export DJANGO_SETTINGS_MODULE=queueless_backend.settings
pytest
```

## Project Structure

```text
QueueLess-Backend/
	queueless_backend/
		manage.py
		mock_api/
		notifications/
		queue_tracker/
		queueless_backend/
```

## Notes

- If you add new apps (like `queue_tracker`), register them in `INSTALLED_APPS` in `queueless_backend/settings.py`.
- Configure `CORS_ALLOWED_ORIGINS` when connecting a frontend.
- Add Channels routing and ASGI configuration when you introduce WebSocket consumers.
