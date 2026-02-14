import asyncio
from app.supermemory.client import SupermemoryClient
import json

async def reproduce():
    sm = SupermemoryClient()
    print("Attempting to add document with LIST in metadata...")
    
    metadata = {
        "test_key": "test_value",
        "complex_list": [{"a": 1}, {"b": 2}]
    }
    
    try:
        res = await sm.add_document("Test content with complex metadata", metadata, title="Complex Meta Test")
        print(f"Success! Result: {res}")
    except Exception as e:
        print(f"Failed as expected? Error: {e}")

if __name__ == "__main__":
    asyncio.run(reproduce())
