import asyncio
from app.supermemory.client import SupermemoryClient
import json

async def check_structure():
    sm = SupermemoryClient()
    user_email = "siddhantwagh724@gmail.com"
    filters = {"AND": [{"key": "user_id", "value": user_email}]}
    
    print("Searching for everything for user...")
    res = await sm.search(query="*", filters=filters, limit=5)
    print("\n--- RESPONSE STRUCTURE ---")
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    asyncio.run(check_structure())
