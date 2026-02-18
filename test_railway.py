import requests
import time

url = "https://passionate-patience-production-a232.up.railway.app/"
print(f"Testing {url}...")
try:
    start = time.time()
    resp = requests.get(url, timeout=10)
    end = time.time()
    print(f"Status: {resp.status_code}")
    print(f"Time: {end - start:.2f}s")
    print(f"Body: {resp.text[:100]}")
except Exception as e:
    print(f"Error: {e}")
