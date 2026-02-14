from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

TRIAGE_SYSTEM_PROMPT = """
You are a query classifier for an academic AI assistant.

Classify the user's query into ONE of these categories:
- academic_question: Needs course content/concepts (e.g., "Explain AVL trees")
- deadline_lookup: Needs calendar/schedule data (e.g., "When is my assignment due?")
- general_chat: No retrieval needed (e.g., "Hello", "Thanks")

Respond ONLY with the category name, nothing else.
"""

async def classify_query(query: str, base64_image: str = None) -> str:
    """Use GPT-4 to classify query type, including visual context if available."""
    try:
        if not settings.OPENAI_API_KEY:
            return "general_chat"

        messages = [
            {"role": "system", "content": TRIAGE_SYSTEM_PROMPT}
        ]
        
        user_content = [{"type": "text", "text": query}]
        if base64_image:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            })
            
        messages.append({"role": "user", "content": user_content})

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,
            max_tokens=20
        )
        
        category = response.choices[0].message.content.strip()
        # Basic validation to ensure it returns a valid category
        valid_categories = ["academic_question", "deadline_lookup", "general_chat"]
        return category if category in valid_categories else "academic_question"
    except Exception as e:
        print(f"Triage Error: {e}")
        return "general_chat"
