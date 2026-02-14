import httpx
import asyncio

async def search_v2():
    url = "https://api.supermemory.ai/v3/search"
    api_key = "sm_ukWVowSxAX8JUVXgoTDe28_HrEMpcPhyGHwkiylYNzouOfHcYBKbKCLFScqhvxJmeJgaKkTcuGghEbFGQxhokKk"
    
    headers = {"Authorization": f"Bearer {api_key}"}
    
    # Try the most basic search possible
    payload = {"q": "*", "limit": 5}
    
    print(f"Searching {url} with payload {payload}")
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text}")

if __name__ == "__main__":
    asyncio.run(search_v2())
