import requests
import json

token = "sm_4CQib4emAF9QNT1pXRHpvM_GkZNlTkkTxYCLIGJdCUQGwqNXPDnSjRBZwCwRcupgpxYMXaDOZJrSLJdUlvKGWAx"
base_url = "https://api.supermemory.ai/v3"

def test_add_doc():
    url = f"{base_url}/documents"
    payload = {
        "content": "Test content for FIWB sync",
        "metadata": {"test": "true", "user_id": "sidwagh724@gmail.com"}
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"Testing POST {url}")
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_add_doc()
