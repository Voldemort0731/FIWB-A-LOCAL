import asyncio
from app.supermemory.client import SupermemoryClient
from app.config import settings

async def check_sm_content(course_id="843626074076", user_email="siddhantwagh724@gmail.com"):
    print(f"Checking Supermemory for User: {user_email}, Course: {course_id}...")
    
    sm_client = SupermemoryClient()
    
    # Query exact match
    filters = {
        "AND": [
            {"key": "course_id", "value": course_id},
            {"key": "user_id", "value": user_email}
        ]
    }
    
    print(f"URL: {settings.SUPERMEMORY_URL}")
    print(f"API Key Present: {bool(settings.SUPERMEMORY_API_KEY)}")
    
    try:
        results = await sm_client.search(query="*", filters=filters, limit=10)
        chunks = results.get("chunks", [])
        print(f"Found {len(chunks)} chunks/documents.")
        
        for c in chunks:
            meta = c.get("metadata", {})
            print(f"- Title: {meta.get('title') or c.get('title')}")
            print(f"  Type: {meta.get('type')}")
            print(f"  Source ID: {meta.get('source_id')}")
            
    except Exception as e:
        print(f"Error querying Supermemory: {e}")

if __name__ == "__main__":
    asyncio.run(check_sm_content())
