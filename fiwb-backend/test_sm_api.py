import requests
import json

token = "sm_4CQib4emAF9QNT1pXRHpvM_GkZNlTkkTxYCLIGJdCUQGwqNXPDnSjRBZwCwRcupgpxYMXaDOZJrSLJdUlvKGWAx"
base_url = "https://api.supermemory.ai/v3"

def test_add_document():
    url = f"{base_url}/documents"
    payload = {
        "content": "This is a test document with a null metadata value.",
        "metadata": {
            "source": "verification_script",
            "due_date": None
        }
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

def test_search():
    url = f"{base_url}/search"
    payload = {
        "q": "test document",
        "limit": 5
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"\nTesting POST {url}")
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

def test_memory():
    url = f"{base_url}/memories"
    payload = {
        "user_id": "test_user",
        "interaction": {"text": "Hello"},
        "inferred_context": {"mood": "neutral"}
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"\nTesting POST {url}")
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_add_document()
    test_search()
    test_memory()
