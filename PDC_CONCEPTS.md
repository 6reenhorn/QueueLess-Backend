# PDC Concepts Applied: QueueLess System

This document outlines the Parallel and Distributed Computing (PDC) concepts integrated into the QueueLess backend architecture and explains their specific roles in ensuring system stability, scalability, and real-time responsiveness.

## 1. Client-Server Architecture
### Role in Design
The system follows a classic **Distributed Client-Server model**. The Django REST Framework (DRF) acts as the centralized server, while various clients (Web, Mobile, and the Institution Mock API) interact with it via stateless HTTP requests.

### Why it is Appropriate
*   **Decoupling:** Allows the frontend and backend to evolve independently.
*   **Scalability:** The server-side logic is centralized, making it easier to deploy to cloud environments.

### Code Pointer
*   **API Configuration:** See `queueless_backend/settings.py` (Lines 59-72) for the application definition and `queue_tracker/views.py` for endpoint logic.

## 2. Distributed Messaging (Real-time Synchronization)
### Role in Design
QueueLess utilizes **Django Channels** backed by a **Redis Channel Layer**. This implements a **Publish-Subscribe (Pub/Sub)** pattern where the server "publishes" queue updates, and specific "subscriber" clients receive them instantly via WebSockets.

### Why it is Appropriate
In a queueing system, latency is critical. Traditional polling is inefficient; distributed messaging allows the system to be **event-driven**, only sending data when something changes.

### Code Pointer
*   **Redis Channel Layer:** See `queueless_backend/settings.py` (Lines 255-270) where Redis is configured as the message broker for real-time notifications.

## 3. Concurrency Control & Synchronization
### Role in Design
To handle multiple simultaneous requests, the system uses **Pessimistic Locking** via `.select_for_update()`.

### Where it is Applied
*   **`QueueJoinView`:** When a user joins a queue, the system locks the specific `Institution` row to ensure the `current_serving_number` is read and validated accurately.
*   **Auto-Tick Logic:** Uses atomic transactions to ensure no ticket numbers are skipped or duplicated.

### Why it is Appropriate
In a high-traffic environment, hundreds of users might join at the same millisecond. Without these synchronization primitives, the system would suffer from **Race Conditions**.

### Code Pointer
*   **Row Locking:** See `queue_tracker/views.py` (Line 49) for the use of `select_for_update()` inside a transaction.

## 4. Distributed Traffic Management (Throttling)
### Role in Design
The system implements **Rate Limiting (Throttling)** using DRF's distributed throttling classes to manage resource allocation.

### Why it is Appropriate
Throttling ensures that no single "heavy" client can monopolize the distributed system's resources, maintaining "Liveness" for all other users.

### Code Pointer
*   **Global Rates:** See `queueless_backend/settings.py` (Lines 190-203).
*   **View Scoping:** See `queue_tracker/views.py` (Line 29) for `throttle_scope = "join"`.

## 5. Distributed System Simulation (Mock API)
### Role in Design
The `mock_api` app simulates a distributed environment where QueueLess interacts with external, third-party institution APIs.

### Why it is Appropriate
By architecting a separate `mock_api` that "talks" to the `queue_tracker`, we simulate the **inter-process communication (IPC)** and network latency found in truly distributed systems.

### Code Pointer
*   **Service Simulator:** See the entire `queueless_backend/mock_api/` directory.

## 6. Performance Verification (Stress Testing)
### Role in Design
To verify the system's ability to handle high concurrency and distributed load, a **Locust load-testing framework** was implemented.

### Observed PDC Behavior
*   **Scalability Testing:** The system was subjected to 100+ simultaneous virtual users.
*   **Self-Protection (Throttling):** Under extreme stress, the system correctly returned **HTTP 429 (Too Many Requests)** for the `join` endpoint. This demonstrates the "fail-safe" mechanism of distributed traffic management, preventing the database from crashing during a request spike.
*   **Concurrency Stability:** Despite the high load, the row-level locking ensured that no duplicate ticket numbers were issued (Data Consistency).

### Code Pointer
*   **Test Script:** See `locust_tests/locustfile.py` for the implementation of the simulated distributed user behavior.

