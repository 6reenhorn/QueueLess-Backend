import sys
import os
import django
from rest_framework.test import APIClient
from rest_framework import status

# Setup Django
sys.path.append(os.path.join(os.getcwd(), 'queueless_backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'queueless_backend.settings')
django.setup()

from mock_api.models import Institution

def test_join_throttle():
    client = APIClient()
    institution = Institution.objects.first()
    if not institution:
        print("No institution found to test.")
        return

    print(f"Testing Join Queue throttle for institution {institution.id}...")
    
    # We set 5/min in settings
    for i in range(1, 8):
        response = client.post('/api/queue/join/', {
            "institution_id": institution.id,
            "queue_number": 1000 + i
        })
        print(f"Request {i}: Status {response.status_code}")
        if response.status_code == 429:
            print(">>> SUCCESS: Rate limit triggered at request", i)
            return
    
    print(">>> FAILURE: Rate limit NOT triggered after 7 requests.")

if __name__ == "__main__":
    test_join_throttle()
