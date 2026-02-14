"""
Direct test to verify Supermemory search is being called
"""
import asyncio
from app.supermemory.client import SupermemoryClient

async def test_search():
    client = SupermemoryClient()
    
    print("\n" + "="*80)
    print("TESTING SUPERMEMORY SEARCH DIRECTLY")
    print("="*80)
    
    # Test 1: Simple search
    print("\nTest 1: Simple wildcard search")
    result = await client.search(query="*", limit=5)
    print(f"Result: {result}")
    
    # Test 2: Search with filters
    print("\nTest 2: Search with user filter")
    filters = {
        "AND": [
            {"key": "user_id", "value": "siddhantwagh724@gmail.com", "negate": False}
        ]
    }
    result = await client.search(query="recursion", filters=filters, limit=5)
    print(f"Result: {result}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_search())
