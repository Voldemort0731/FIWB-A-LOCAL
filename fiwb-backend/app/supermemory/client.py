import httpx
from app.config import settings
import json

class SupermemoryClient:
    def __init__(self, client: httpx.AsyncClient = None):
        self.base_url = settings.SUPERMEMORY_URL
        headers = {}
        if settings.SUPERMEMORY_API_KEY:
            headers["Authorization"] = f"Bearer {settings.SUPERMEMORY_API_KEY}"
        
        # Add stealth/modern headers
        headers["User-Agent"] = "FIWB-AI/1.0 (Institutional Academic Hub)"
        
        # Use shared client if provided, otherwise create one
        self.client = client if client else httpx.AsyncClient(headers=headers)
    
    async def add_document(self, content: str, metadata: dict, title: str = None, description: str = None):
        """Add a document to Supermemory with robust error handling and retries."""
        import asyncio
        import random
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                safe_content = content
                if len(content) > 60000:
                    safe_content = content[:60000] + "\n\n[TRUNCATED]"

                clean_metadata = {k: v for k, v in metadata.items() if v is not None}
                payload = {"content": safe_content, "metadata": clean_metadata}
                if title: payload["title"] = title
                if description: payload["description"] = description
                
                response = await self.client.post(f"{self.base_url}/v3/documents", json=payload)
                
                if response.status_code == 429:
                    wait = (2 ** attempt) + random.random()
                    print(f"⚠️ SM Rate Limit (429). Retrying in {wait:.2f}s...")
                    await asyncio.sleep(wait)
                    continue

                if response.status_code == 400:
                    print(f"❌ Supermemory 400 Error: {response.text}")
                    return None

                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    continue
                print(f"❌ Supermemory HTTP Error {e.response.status_code}")
                return None
            except Exception as e:
                print(f"❌ Supermemory Unexpected Error: {e}")
                return None
        return None
    
    async def search(self, query: str, filters: dict = None, limit: int = 5):
        """Search Supermemory."""
        try:
            # filters should now be in the format: {"AND": [...]} or {"OR": [...]}
            # where each item is {"key": "...", "value": "...", "negate": False}
            final_query = query.strip() if query and query.strip() else "*"
            payload = {"q": final_query, "limit": limit}
            if filters:
                payload["filters"] = filters
            
            print(f"🔍 [SUPERMEMORY SEARCH] Initiating search")
            print(f"   - Query: {final_query[:100]}")
            print(f"   - Filters: {filters}")
            print(f"   - Limit: {limit}")
            print(f"   - Full Payload: {json.dumps(payload, indent=2)}")
                
            response = await self.client.post(
                f"{self.base_url}/v3/search",
                json=payload
            )
            
            print(f"   - Response Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ [SUPERMEMORY SEARCH] Error: {response.status_code}")
                print(f"   - Response Body: {response.text}")
                print(f"   - Headers: {dict(response.headers)}")
            else:
                result = response.json()
                result_count = len(result.get('results', []))
                print(f"✅ [SUPERMEMORY SEARCH] Success - Found {result_count} results")
                
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"❌ [SUPERMEMORY SEARCH] HTTP Error: {e.response.status_code}")
            print(f"   - Response: {e.response.text}")
            return {"results": []}
        except Exception as e:
            print(f"❌ [SUPERMEMORY SEARCH] Exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return {"results": []}
    
    async def add_memory(self, user_id: str, interaction: dict, context: dict, title: str = None, description: str = None):
        """Writeback interaction to digital twin (via documents endpoint in V3)."""
        try:
            query = interaction.get('query', '')
            response = interaction.get('response', '')
            content = f"Interaction:\nUser: {query}\nAssistant: {response}\nContext: {json.dumps(context)}"
            
            payload = {
                "content": content,
                "metadata": {
                    "user_id": user_id,
                    "type": "memory_interaction"
                }
            }
            if title:
                payload["title"] = title
            if description:
                payload["description"] = description
                
            response_obj = await self.client.post(
                f"{self.base_url}/v3/documents",
                json=payload
            )
            response_obj.raise_for_status()
            return response_obj.json()
        except Exception as e:
            print(f"DEBUG SM: Error adding memory: {e}")
            return None

    async def delete_document(self, document_id: str):
        """Delete a document from Supermemory."""
        try:
            response = await self.client.delete(
                f"{self.base_url}/v3/documents/{document_id}"
            )
            response.raise_for_status()
            print(f"✅ DEBUG SM: Deleted document {document_id}")
            return True
        except Exception as e:
            print(f"❌ DEBUG SM: Error deleting document {document_id}: {e}")
            return False
