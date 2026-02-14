from openai import AsyncOpenAI
from app.config import settings
from app.supermemory.client import SupermemoryClient
from app.intelligence.usage import UsageTracker
from app.utils.email import standardize_email
import datetime
import json
import hashlib

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
sm_client = SupermemoryClient()

ENHANCED_MEMORY_PROMPT = """
You are an Advanced Memory Synthesis Engine for a personalized academic AI assistant.
Your goal is to create a RICH, MULTI-DIMENSIONAL memory that builds a comprehensive digital twin of the user.

Analyze the user-AI interaction and extract:

**OUTPUT FORMAT (JSON):**
{
    "title": "Concise topic (e.g., 'Recursion in Python')",
    "summary": "2-3 sentence summary of the interaction",
    
    "learning_insights": {
        "understanding_level": "beginner|intermediate|advanced",
        "knowledge_gaps": ["Specific gaps identified"],
        "strengths": ["What the user demonstrated mastery of"],
        "misconceptions": ["Any incorrect assumptions corrected"]
    },
    
    "user_profile": {
        "learning_style": "visual|auditory|kinesthetic|reading|mixed",
        "communication_preference": "concise|detailed|step-by-step|conceptual",
        "engagement_signals": ["Questions asked", "Follow-ups", "Confusion points"],
        "emotional_context": "curious|frustrated|confident|struggling|excited"
    },
    
    "academic_context": {
        "topics": ["Primary", "Topics", "Covered"],
        "difficulty_level": "easy|medium|hard",
        "related_courses": ["Potential course connections"],
        "prerequisites": ["Concepts this builds on"]
    },
    
    "actionable_insights": {
        "follow_up_suggestions": ["What to study next"],
        "practice_recommendations": ["Exercises or resources"],
        "review_needed": ["Topics to revisit"]
    },
    
    "metadata": {
        "interaction_type": "question|explanation|debugging|brainstorming|review",
        "session_context": "assignment|exam_prep|concept_learning|project|general",
        "confidence_score": 0.0-1.0  // How confident the user seemed
    }
}

**IMPORTANT:**
- Be specific and actionable
- Focus on long-term learning patterns
- Identify both explicit and implicit signals
- If a field doesn't apply, use null or empty array
- Extract insights that help personalize future interactions
"""

class MemoryAgent:
    @staticmethod
    async def synthesize_and_save(
        user_email: str, 
        query: str, 
        response: str, 
        additional_context: dict = None,
        conversation_history: list = None
    ):
        """Synthesize memory for user."""
        user_email = standardize_email(user_email)
        try:
            if not settings.OPENAI_API_KEY:
                return

            # Build context for LLM
            context_str = f"USER: {query}\n\nAI: {response}"
            if conversation_history:
                recent_history = "\n".join([
                    f"{msg['role'].upper()}: {msg['content'][:200]}"
                    for msg in conversation_history[-3:]  # Last 3 exchanges
                ])
                context_str = f"RECENT CONTEXT:\n{recent_history}\n\n---\nCURRENT:\n{context_str}"

            # 1. Synthesize with Enhanced LLM
            # Log input tokens (SLM)
            UsageTracker.log_usage(user_email, UsageTracker.count_tokens(ENHANCED_MEMORY_PROMPT + context_str), is_input=True, category="slm")

            completion = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": ENHANCED_MEMORY_PROMPT},
                    {"role": "user", "content": context_str}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result_json = completion.choices[0].message.content
            # Log output tokens (SLM)
            UsageTracker.log_usage(user_email, UsageTracker.count_tokens(result_json), is_input=False, category="slm")
            memory_data = json.loads(result_json)
            
            # 2. Generate unique interaction ID
            interaction_id = hashlib.md5(
                f"{user_email}_{datetime.datetime.utcnow().isoformat()}_{query[:50]}".encode()
            ).hexdigest()[:12]
            
            # 3. Format Rich Content Block
            title = f"💭 {memory_data.get('title', 'Learning Interaction')}"
            
            learning = memory_data.get('learning_insights', {})
            profile = memory_data.get('user_profile', {})
            academic = memory_data.get('academic_context', {})
            actionable = memory_data.get('actionable_insights', {})
            meta = memory_data.get('metadata', {})
            
            content_block = f"""
## {memory_data.get('title')}

**Summary**: {memory_data.get('summary')}

### 🎓 Learning Insights
- **Understanding Level**: {learning.get('understanding_level', 'N/A')}
- **Knowledge Gaps**: {', '.join(learning.get('knowledge_gaps', [])) or 'None identified'}
- **Strengths**: {', '.join(learning.get('strengths', [])) or 'None identified'}
- **Misconceptions Corrected**: {', '.join(learning.get('misconceptions', [])) or 'None'}

### 👤 User Profile Signals
- **Learning Style**: {profile.get('learning_style', 'Unknown')}
- **Communication Preference**: {profile.get('communication_preference', 'Unknown')}
- **Emotional Context**: {profile.get('emotional_context', 'Neutral')}
- **Engagement**: {', '.join(profile.get('engagement_signals', [])) or 'Standard'}

### 📚 Academic Context
- **Topics**: {', '.join(academic.get('topics', []))}
- **Difficulty**: {academic.get('difficulty_level', 'Medium')}
- **Related Courses**: {', '.join(academic.get('related_courses', [])) or 'General'}
- **Prerequisites**: {', '.join(academic.get('prerequisites', [])) or 'None'}

### 🎯 Actionable Insights
- **Follow-up Suggestions**: {', '.join(actionable.get('follow_up_suggestions', [])) or 'None'}
- **Practice Recommendations**: {', '.join(actionable.get('practice_recommendations', [])) or 'None'}
- **Review Needed**: {', '.join(actionable.get('review_needed', [])) or 'None'}

### 📊 Interaction Metadata
- **Type**: {meta.get('interaction_type', 'general')}
- **Context**: {meta.get('session_context', 'general')}
- **Confidence Score**: {meta.get('confidence_score', 0.5)}

---
### 💬 Raw Interaction
**User**: {query}

**AI**: {response[:500]}{'...' if len(response) > 500 else ''}
"""

            # 4. Build Rich Metadata
            metadata = {
                "user_id": user_email,
                "type": "enhanced_memory",
                "interaction_id": interaction_id,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                
                # Learning Analytics
                "understanding_level": learning.get('understanding_level'),
                "difficulty": academic.get('difficulty_level'),
                "confidence_score": meta.get('confidence_score'),
                
                # Categorization
                "topics": academic.get('topics', []),
                "interaction_type": meta.get('interaction_type'),
                "session_context": meta.get('session_context'),
                
                # Personalization Signals
                "learning_style": profile.get('learning_style'),
                "communication_preference": profile.get('communication_preference'),
                "emotional_context": profile.get('emotional_context'),
                
                # Academic Tracking
                "knowledge_gaps": learning.get('knowledge_gaps', []),
                "strengths": learning.get('strengths', []),
                "related_courses": academic.get('related_courses', []),
                
                # Actionable
                "follow_ups": actionable.get('follow_up_suggestions', []),
                "review_needed": actionable.get('review_needed', []),
            }
            
            # Merge additional context
            if additional_context:
                metadata.update({
                    f"context_{k}": v for k, v in additional_context.items()
                })

            # 5. Save to Supermemory
            UsageTracker.log_sm_request(user_email)
            print(f"🧠 [MEMORY AGENT] Attempting to save enhanced memory: {title}")
            print(f"   - User: {user_email}")
            print(f"   - Content Length: {len(content_block)} chars")
            print(f"   - Metadata Keys: {list(metadata.keys())}")
            
            result = await sm_client.add_document(
                content=content_block,
                metadata=metadata,
                title=title,
                description=memory_data.get("summary")
            )
            
            if result:
                doc_id = result.get('documentId') or result.get('id') or result.get('uuid') or 'unknown'
                print(f"✅ [MEMORY AGENT] Enhanced memory saved successfully!")
                print(f"   - Title: {title}")
                print(f"   - Document ID: {doc_id}")
                print(f"   - Interaction ID: {interaction_id}")
            else:
                print(f"❌ [MEMORY AGENT] Failed to save memory to Supermemory: {title}")
                print(f"   - Check Supermemory logs for details")
            
            # 6. Update User Profile (if insights detected)
            if learning.get('strengths') or learning.get('knowledge_gaps'):
                await MemoryAgent._update_user_profile(
                    user_email=user_email,
                    strengths=learning.get('strengths', []),
                    gaps=learning.get('knowledge_gaps', []),
                    learning_style=profile.get('learning_style'),
                    preferences=profile.get('communication_preference')
                )
            
        except Exception as e:
            print(f"❌ Error in MemoryAgent: {e}")
            import traceback
            traceback.print_exc()
    
    @staticmethod
    async def _update_user_profile(
        user_email: str,
        strengths: list,
        gaps: list,
        learning_style: str,
        preferences: str
    ):
        """
        Update or create a persistent user profile document in Supermemory.
        This creates a living profile that evolves with each interaction.
        """
        try:
            profile_content = f"""
# User Learning Profile

**Last Updated**: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

## Identified Strengths
{chr(10).join(f'- {s}' for s in strengths) if strengths else '- Building...'}

## Knowledge Gaps to Address
{chr(10).join(f'- {g}' for g in gaps) if gaps else '- None identified yet'}

## Learning Preferences
- **Learning Style**: {learning_style or 'Observing...'}
- **Communication Preference**: {preferences or 'Adapting...'}

---
*This profile is automatically updated based on your interactions.*
"""
            
            metadata = {
                "user_id": user_email,
                "type": "user_profile",
                "profile_version": datetime.datetime.utcnow().isoformat(),
                "strengths": strengths,
                "knowledge_gaps": gaps,
                "learning_style": learning_style,
                "communication_preference": preferences
            }
            
            UsageTracker.log_sm_request(user_email)
            print(f"📊 [PROFILE UPDATE] Attempting to update user profile for {user_email}")
            print(f"   - Strengths: {len(strengths)} items")
            print(f"   - Gaps: {len(gaps)} items")
            print(f"   - Learning Style: {learning_style}")
            
            result = await sm_client.add_document(
                content=profile_content,
                metadata=metadata,
                title=f"🧠 Learning Profile: {user_email}",
                description="Evolving user learning profile and preferences"
            )
            
            if result:
                print(f"✅ [PROFILE UPDATE] User profile successfully updated for {user_email}")
            else:
                print(f"❌ [PROFILE UPDATE] Failed to update profile for {user_email}")
            
        except Exception as e:
            print(f"⚠️ Profile update failed: {e}")

