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
4. Run migrations.
5. Start the development server.

### 1) Create Virtual Environment

```powershell
python -m venv venv
```

### 2) Activate Virtual Environment

```powershell
venv\Scripts\activate
```

### 3) Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4) Run Migrations

```powershell
cd queueless_backend
python manage.py makemigrations
python manage.py migrate
```

### 5) Start Development Server

```powershell
python manage.py runserver
```

The API will be available at:

```text
http://127.0.0.1:8000/
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