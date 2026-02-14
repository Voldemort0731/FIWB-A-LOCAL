import asyncio
import httpx
import json

async def test_chat():
    """Test the chat endpoint and observe logs"""
    url = "http://127.0.0.1:8001/api/chat/stream"
    
    form_data = {
        "user_email": "siddhantwagh724@gmail.com",
        "message": "What is recursion in programming?",
        "thread_id": "test-debug-thread-001"
    }
    
    print("=" * 80)
    print("TESTING CHAT ENDPOINT")
    print("=" * 80)
    print(f"URL: {url}")
    print(f"Form Data: {json.dumps(form_data, indent=2)}")
    print("=" * 80)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, data=form_data) as response:
                print(f"Response Status: {response.status_code}")
                print("=" * 80)
                print("STREAMING RESPONSE:")
                print("-" * 80)
                
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        print(chunk, end='', flush=True)
                
                print("\n" + "=" * 80)
                print("STREAM COMPLETE")
                print("=" * 80)
                
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_chat())
