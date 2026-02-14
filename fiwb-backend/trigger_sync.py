import requests
import time

def trigger():
    email = "siddhantwagh724@gmail.com"
    url = f"http://127.0.0.1:8001/api/admin/sync/{email}"
    print(f"Triggering sync for {email}...")
    try:
        res = requests.post(url)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")
    except Exception as e:
        print(f"Failed to trigger sync: {e}")

if __name__ == "__main__":
    trigger()
