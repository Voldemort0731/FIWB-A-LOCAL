import asyncio
from app.supermemory.client import SupermemoryClient
from app.config import settings

async def test_add():
    sm = SupermemoryClient()
    print(f"Adding test document...")
    res = await sm.add_document("This is a test document content.", {"user_id": "siddhantwagh724@gmail.com", "test": True}, title="Test Doc")
    print(f"Result: {res}")

if __name__ == "__main__":
    asyncio.run(test_add())
