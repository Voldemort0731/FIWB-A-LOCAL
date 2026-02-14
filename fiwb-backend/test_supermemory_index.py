"""
Test document indexing to Supermemory
"""
import asyncio
from app.supermemory.client import SupermemoryClient

async def test_indexing():
    client = SupermemoryClient()
    
    print("\n" + "="*80)
    print("TESTING SUPERMEMORY DOCUMENT INDEXING")
    print("="*80)
    
    # Test document
    test_doc = {
        "content": "This is a test document about recursion in Python. Recursion is when a function calls itself.",
        "metadata": {
            "user_id": "siddhantwagh724@gmail.com",
            "type": "test_document",
            "source": "manual_test"
        },
        "title": "Test: Recursion Concept",
        "description": "Testing document indexing functionality"
    }
    
    print("\nIndexing test document...")
    result = await client.add_document(**test_doc)
    
    if result:
        print(f"✅ SUCCESS! Document indexed")
        print(f"   Document ID: {result.get('documentId') or result.get('id') or result.get('uuid')}")
        print(f"   Full response: {result}")
    else:
        print(f"❌ FAILED to index document")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_indexing())
