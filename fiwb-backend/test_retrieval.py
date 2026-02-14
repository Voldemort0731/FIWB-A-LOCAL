import requests
import json

def test_chat_retrieval():
    url = "http://127.0.0.1:8001/api/chat/stream"
    # We ask about a specific assignment we know exists in the DB for this user
    params = {
        "message": "What is the 'Television' assignment in Grade 9 English Literature about?",
        "user_email": "sidwagh724@gmail.com"
    }
    
    print(f"Testing POST {url}")
    print(f"Query: {params['message']}")
    
    try:
        response = requests.post(url, params=params, stream=True)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("Stream content:")
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        print(decoded_line[6:], end="", flush=True)
            print("\n")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_chat_retrieval()
