import asyncio
import json
from app.intelligence.retrieval import RetrievalOrchestrator
from app.config import settings

async def test_search():
    print(f"Testing search for 'lower bound' for siddhantwagh724@gmail.com")
    orchestrator = RetrievalOrchestrator("siddhantwagh724@gmail.com")
    results = await orchestrator.retrieve_context("explain lower bound", "academic_question")
    
    print("\n--- COURSE CONTEXT ---")
    for chunk in results.get("course_context", []):
        print(f"Document: {chunk['metadata'].get('title')}")
        print(f"Content Snippet: {chunk['content'][:200]}...")
        print("-" * 20)
    
    print(f"\nRewritten Query: {results.get('rewritten_query')}")

if __name__ == "__main__":
    asyncio.run(test_search())
