"""
Comprehensive test to verify Memory Agent writeback to Supermemory
"""
import asyncio
from app.intelligence.memory_agent import MemoryAgent
from app.supermemory.client import SupermemoryClient

async def test_memory_writeback():
    print("\n" + "="*80)
    print("TESTING MEMORY AGENT WRITEBACK TO SUPERMEMORY")
    print("="*80)
    
    # Simulate a learning interaction
    user_email = "siddhantwagh724@gmail.com"
    query = "Can you explain how recursion works in Python? I'm having trouble understanding the base case."
    response = """Recursion is when a function calls itself to solve a problem. The base case is crucial - it's the condition that stops the recursion. Without it, the function would call itself infinitely and cause a stack overflow.

Think of it like Russian nesting dolls - you keep opening dolls until you reach the smallest one (the base case), then you work your way back out.

Here's a simple example:
```python
def countdown(n):
    if n == 0:  # Base case
        print("Done!")
    else:
        print(n)
        countdown(n - 1)  # Recursive call
```

Does this help clarify the concept?"""
    
    print(f"\nUser: {user_email}")
    print(f"Query: {query[:80]}...")
    print(f"Response: {response[:80]}...")
    print("\n" + "-"*80)
    print("Triggering Memory Agent synthesis...")
    print("-"*80 + "\n")
    
    # Call the synthesis function
    await MemoryAgent.synthesize_and_save(
        user_email=user_email,
        query=query,
        response=response,
        additional_context={
            "thread_id": "test-memory-writeback-001",
            "query_type": "academic_question"
        },
        conversation_history=[]
    )
    
    print("\n" + "-"*80)
    print("Verifying documents were saved to Supermemory...")
    print("-"*80 + "\n")
    
    # Search for the saved memory
    sm_client = SupermemoryClient()
    
    # Search for enhanced memories
    memory_filters = {
        "AND": [
            {"key": "user_id", "value": user_email, "negate": False},
            {"key": "type", "value": "enhanced_memory", "negate": False}
        ]
    }
    
    memory_results = await sm_client.search(
        query="recursion base case",
        filters=memory_filters,
        limit=5
    )
    
    print(f"\n📚 Enhanced Memories Found: {len(memory_results.get('results', []))}")
    
    # Search for user profile
    profile_filters = {
        "AND": [
            {"key": "user_id", "value": user_email, "negate": False},
            {"key": "type", "value": "user_profile", "negate": False}
        ]
    }
    
    profile_results = await sm_client.search(
        query="learning profile",
        filters=profile_filters,
        limit=3
    )
    
    print(f"👤 User Profiles Found: {len(profile_results.get('results', []))}")
    
    print("\n" + "="*80)
    print("WRITEBACK TEST COMPLETE")
    print("="*80)
    
    if len(memory_results.get('results', [])) > 0:
        print("\n✅ SUCCESS: Memory synthesis is working!")
        print("   Enhanced memories are being saved to Supermemory")
    else:
        print("\n⚠️  WARNING: No enhanced memories found")
        print("   Check the logs above for errors")
    
    if len(profile_results.get('results', [])) > 0:
        print("\n✅ SUCCESS: User profile updates are working!")
        print("   Learning profiles are being saved to Supermemory")
    else:
        print("\n⚠️  INFO: No user profiles found yet")
        print("   Profiles are created when strengths/gaps are identified")

if __name__ == "__main__":
    asyncio.run(test_memory_writeback())
