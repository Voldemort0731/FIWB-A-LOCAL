from typing import List, Dict
import json

class PromptArchitect:
    @staticmethod
    def build_prompt(
        user_query: str,
        retrieved_chunks: List[Dict],
        assistant_knowledge: List[Dict] = None,
        chat_assets: List[Dict] = None,
        memories: List[Dict] = None,
        profile: List[Dict] = None,
        history: List[Dict] = None,
        attachment_text: str = None,
        base64_image: str = None,
        query_type: str = "academic_question",
        rewritten_query: str = None
    ) -> List[Dict]:
        """
        Builds a high-fidelity, multi-message conversation for the Socratic Institutional Mentor.
        """
        
        # 1. ORCHESTRATE ACADEMIC CONTEXT
        context_blocks = []
        for c in retrieved_chunks:
            meta = c.get('metadata', {})
            course = meta.get('course_name', 'University Workspace')
            category = meta.get('type', 'Institutional Material').upper()
            author = meta.get('professor', 'Academic Faculty')
            title = meta.get('title') or meta.get('file_name') or "Institutional Document"
            content = c.get('content', '')
            context_blocks.append(f"[{category} | {course}]\nDOCUMENT: {title}\nFACULTY: {author}\nCONTENT: {content}")
        
        knowledge_base = "\n\n---\n\n".join(context_blocks) if context_blocks else "General academic intelligence."

        # 2. ORCHESTRATE ASSISTANT KNOWLEDGE (GMAIL/WORKSPACE/ASSETS)
        assistant_blocks = []
        if assistant_knowledge:
            for ak in assistant_knowledge:
                meta = ak.get('metadata', {})
                label = meta.get('category', 'INTEL').upper()
                sender = meta.get('sender', 'Neural Link')
                title = meta.get('subject') or meta.get('title') or "Workspace Item"
                assistant_blocks.append(f"[{label} | SENDER: {sender} | TITLE: {title}]\nCONTEXT: {ak.get('content')}")
        
        if chat_assets:
            for asset in chat_assets:
                meta = asset.get('metadata', {})
                fname = meta.get('file_name', 'Previous Asset')
                assistant_blocks.append(f"[PAST ASSET | {fname}]\nCONTENT: {asset.get('content')}")

        assistant_workspace = "\n\n".join(assistant_blocks) if assistant_blocks else "No proprietary workspace context detected."

        # 3. ORCHESTRATE LONG-TERM COGNITION
        memory_vault = "\n".join([f"• {m['content']}" for m in memories]) if memories else "No prior history detected."
        
        # 4. ORCHESTRATE USER IDENTITY
        identity_logic = "\n".join([f"• {p['content']}" for p in profile]) if profile else "Establish student learning style."

        # 5. DEFINE CORE INSTRUCTION
        if query_type == "general_chat":
            SYSTEM_PROMPT = f"""
# IDENTITY: FIWB Digital Companion
You are the student's supportive, witty, and deeply empathetic Digital Twin. 
You act as a personal assistant and friend, using a warm and relatable tone.

# PROPRIETARY WORKSPACE:
{assistant_workspace}

# ACADEMIC / DRIVE CONTEXT:
{knowledge_base}

# COGNITIVE CONTEXT:
- Learned Identity: {identity_logic}
- Past Insights: {memory_vault}

# DIRECTIVE:
1. Use double-spacing between modules for "Oxygen."
2. **Bold** critical insights.
3. Be empathetic and supportive. Reference their tasks or events from the workspace if relevant.
"""
        else:
            SYSTEM_PROMPT = f"""
# IDENTITY: FIWB Institutional Intelligence (FIWB-II)
You are an elite academic mentor and Socratic tutor.

# ACADEMIC VAULT:
{knowledge_base}

# ASSISTANT WORKSPACE (Life/Context):
{assistant_workspace}

# PERSONALIZED INTELLIGENCE (Digital Twin Profile):
- Learned Identity & Preferences: {identity_logic}
- Past Memories & Patterns: {memory_vault}

# DIRECTIVE:
1. PRIORITIZE the Academic Vault. Quote materials directly.
2. SOCRATIC METHOD: Guide the student. Explain, then probe with clarifying questions.
3. PERSONALIZED MENTORING: Use the 'Personalized Intelligence' above to adapt your tone and examples to the student's learning style.
4. TAGGING (START): You MUST start your response with exactly: [PERSONAL_REASONING: insight1, insight2]. Example: [PERSONAL_REASONING: Visual Preference, Prior Knowledge].
5. TAGGING (END): You MUST conclude your response with exactly: [DOCUMENTS_REFERENCED: doc1, doc2]. List the exact titles of materials used from the Academic Vault.
6. CONTINUITY: If you use the Assistant Workspace (Gmail/Chat), include those in the [DOCUMENTS_REFERENCED: ...] list as 'Email: Subject' or 'Asset: Name'.

# VISUAL EXCELLENCE:
- Use # H1 and ## H2 for hierarchy.
- Bold **core terminology**.
"""
        messages = [{"role": "system", "content": SYSTEM_PROMPT.strip()}]

        # 6. INTEGRATE CONVERSATION HISTORY
        if history:
            for msg in history[-10:]:
                role = "user" if msg.get("role") == "user" else "assistant"
                messages.append({"role": role, "content": msg.get("content")})

        # 7. ATTACH THE LATEST QUERY WITH ASSETS
        final_query_content = []
        if attachment_text:
            final_query_content.append({"type": "text", "text": f"[ATTACHED ASSET CONTENT]:\n{attachment_text}"})
        
        if base64_image:
            final_query_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            })
            
        final_query_content.append({"type": "text", "text": user_query})
        
        messages.append({"role": "user", "content": final_query_content})

        return messages
