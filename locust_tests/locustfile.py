import random
from locust import HttpUser, task, between

class QueueUser(HttpUser):
    # Simulates a user waiting between 1 and 5 seconds between actions
    wait_time = between(1, 5)
    
    def on_start(self):
        """Called when a virtual user starts."""
        self.session_id = None
        self.institution_id = None
        self.next_number = 1
        self.fetch_institutions()

    def fetch_institutions(self):
        """Fetches the list of institutions to pick one."""
        with self.client.get("/api/institutions/", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    # Pick a random institution from the seeded data
                    inst = random.choice(data)
                    self.institution_id = inst['id']
                    self.next_number = inst.get('next_queue_number', 1)
            else:
                response.failure(f"Failed to fetch institutions: {response.status_code}")

    @task(3)
    def check_status(self):
        """Simulates a user checking their queue status."""
        if self.session_id:
            with self.client.get(f"/api/queue/entries/{self.session_id}/status/", catch_response=True) as response:
                if response.status_code != 200:
                    response.failure(f"Status check failed: {response.status_code}")
        else:
            # If no active session, try to join a queue
            self.join_queue()

    @task(1)
    def join_queue(self):
        """Simulates a user joining a queue."""
        # Only join if we have an institution but no active session
        if self.institution_id and not self.session_id:
            payload = {
                "institution_id": self.institution_id,
                "queue_number": self.next_number + random.randint(0, 100), # Join ahead
                "phone_number": f"09{random.randint(100000000, 999999999)}",
                "browser_push_opt_in": random.choice([True, False])
            }
            
            with self.client.post("/api/queue/join/", json=payload, catch_response=True) as response:
                if response.status_code == 201:
                    data = response.json()
                    self.session_id = data.get('session_id')
                elif response.status_code == 400:
                    # This might happen if the number was already taken during the stress test
                    # We mark it as a success because it's a valid business logic error under stress
                    response.success()
                else:
                    response.failure(f"Join failed: {response.status_code}")

    @task(1)
    def browse_institutions(self):
        """Simulates a user just browsing the list."""
        self.fetch_institutions()
