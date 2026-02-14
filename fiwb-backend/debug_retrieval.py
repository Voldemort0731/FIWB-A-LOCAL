import asyncio
from app.supermemory.client import SupermemoryClient
from app.config import settings

async def debug_retrieval():
    course_id = "843626074076" # Known course ID from previous logs
    user_email = "siddhantwagh724@gmail.com"
    
    print(f"DEBUG: Testing retrieval for User: {user_email}, Course: {course_id}")
    
    sm = SupermemoryClient()
    
    # 1. Try with the filters we use in the app
    filters = {
        "AND": [
            {"key": "course_id", "value": course_id},
            {"key": "user_id", "value": user_email}
        ]
    }
    
    print("\n--- Test 1: Query=' ' (Single Space) ---")
    res1 = await sm.search(query=" ", filters=filters, limit=10)
    print(f"Result Count: {len(res1.get('chunks', []))}")
    
    print("\n--- Test 2: Query='*' (Wildcard) ---")
    res2 = await sm.search(query="*", filters=filters, limit=10)
    print(f"Result Count: {len(res2.get('chunks', []))}")

    print("\n--- Test 3: No Query, Just Filters ---")
    # Some vector DBs behave differently with empty/null query
    res3 = await sm.search(query="", filters=filters, limit=10) 
    print(f"Result Count: {len(res3.get('chunks', []))}")

    print("\n--- Test 4: Looser Filters (Just User) ---")
    user_filter = {"AND": [{"key": "user_id", "value": user_email}]}
    res4 = await sm.search(query="*", filters=user_filter, limit=10)
    print(f"Result Count: {len(res4.get('chunks', []))}")
    if res4.get('chunks'):
        print("Sample metadata from Test 4:")
        print(res4['chunks'][0].get('metadata'))

if __name__ == "__main__":
    asyncio.run(debug_retrieval())
