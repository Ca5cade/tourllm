import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def test_scheduler_endpoints():
    print("🧪 Testing Scheduler Endpoints...")
    
    # 1. Check Status
    try:
        response = requests.get(f"{BASE_URL}/learner/status")
        if response.status_code == 200:
            print("✅ /learner/status is reachable.")
            print(f"   Status: {response.json()}")
        else:
            print(f"❌ /learner/status failed: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Could not connect to {BASE_URL}. Is the server running? ({e})")
        return

    # 2. Add Topic
    try:
        response = requests.post(f"{BASE_URL}/learner/add-topic?topic=TestTopic123")
        if response.status_code == 200:
             print("✅ /learner/add-topic worked.")
        else:
             print(f"❌ /learner/add-topic failed: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Error adding topic: {e}")

    # 3. Stop
    try:
        response = requests.post(f"{BASE_URL}/learner/stop")
        if response.status_code == 200:
             print("✅ /learner/stop worked.")
        else:
             print(f"❌ /learner/stop failed: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Error stopping learner: {e}")

if __name__ == "__main__":
    test_scheduler_endpoints()
