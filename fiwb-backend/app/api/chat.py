from fastapi import APIRouter, Depends, File, UploadFile, Form, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from openai import AsyncOpenAI
import base64
import pypdf
import io
import uuid
import json
import asyncio
import logging
from datetime import datetime

from app.database import get_db, SessionLocal
from app.models import User, ChatThread, ChatMessage
from app.intelligence.triage_agent import classify_query
from app.intelligence.retrieval import RetrievalOrchestrator
from app.intelligence.prompt_architect import PromptArchitect
from app.intelligence.memory_agent import MemoryAgent
from app.intelligence.usage import UsageTracker
from app.config import settings
from app.utils.email import standardize_email

router = APIRouter()
logger = logging.getLogger("uvicorn.error")
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def extract_text_from_file(file: UploadFile) -> str:
    """Extract text from PDF or TXT files."""
    content = await file.read()
    if file.filename.endswith(".pdf"):
        pdf_reader = pypdf.PdfReader(io.BytesIO(content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    elif file.filename.endswith(".txt"):
        return content.decode("utf-8")
    return ""

@router.get("/threads")
async def list_threads(user_email: str, db: Session = Depends(get_db)):
    # Standardize email for consistency with sync services
    actual_email = standardize_email(user_email)
    user = db.query(User).filter(User.email == actual_email).first()
    if not user: return []
    threads = db.query(ChatThread).filter(ChatThread.user_id == user.id).order_by(ChatThread.updated_at.desc()).all()
    return [{
        "id": t.id,
        "title": t.title,
        "updated_at": t.updated_at
    } for t in threads]

@router.get("/threads/{thread_id}/messages")
async def get_thread_messages(thread_id: str, user_email: str, db: Session = Depends(get_db)):
    # Standardize email
    actual_email = standardize_email(user_email)
    user = db.query(User).filter(User.email == actual_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    thread = db.query(ChatThread).filter(ChatThread.id == thread_id, ChatThread.user_id == user.id).first()
    if not thread:
        raise HTTPException(status_code=403, detail="Not authorized to view this thread")

    messages = db.query(ChatMessage).filter(ChatMessage.thread_id == thread_id).order_by(ChatMessage.created_at.asc()).all()
    return [{
        "role": m.role,
        "content": m.content,
        "file_name": m.file_name,
        "attachment_type": m.attachment_type,
        "attachment": m.attachment
    } for m in messages]

@router.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str, user_email: str, db: Session = Depends(get_db)):
    actual_email = standardize_email(user_email)
    user = db.query(User).filter(User.email == actual_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    thread = db.query(ChatThread).filter(ChatThread.id == thread_id, ChatThread.user_id == user.id).first()
    if not thread:
        raise HTTPException(status_code=403, detail="Not authorized to delete this thread")

    db.query(ChatMessage).filter(ChatMessage.thread_id == thread_id).delete()
    db.delete(thread)
    db.commit()
    return {"status": "deleted"}

@router.post("/stream")
async def chat_stream(
    background_tasks: BackgroundTasks,
    message: str = Form(...),
    user_email: str = Form(...),
    thread_id: str = Form("new"), 
    history: str = Form(None), 
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """Chat endpoint supporting multi-threading and DB persistence."""
    logger.info(f"🚀 [CHAT] Request from {user_email} (Thread: {thread_id})")
    
    # Identify or create thread
    actual_email = standardize_email(user_email)
    user = db.query(User).filter(User.email == actual_email).first()
    if not user:
        return {"error": "User not found"}
        
    if thread_id == "new":
        thread_id = str(uuid.uuid4())
        thread = ChatThread(
            id=thread_id,
            user_id=user.id,
            title=message[:40] + ("..." if len(message) > 40 else "")
        )
        db.add(thread)
        db.commit()
    else:
        thread = db.query(ChatThread).filter(ChatThread.id == thread_id).first()
        if not thread:
            # Fallback if invalid ID
            thread_id = str(uuid.uuid4())
            thread = ChatThread(id=thread_id, user_id=user.id, title=message[:40])
            db.add(thread)
            db.commit()

    attachment_text = None
    base64_image = None
    attachment_base64 = None
    
    # Process attachment
    if file:
        file_content = await file.read()
        if file.content_type.startswith("image/"):
            base64_image = base64.b64encode(file_content).decode("utf-8")
            attachment_base64 = f"data:{file.content_type};base64,{base64_image}"
        else:
            # Re-read for text extraction
            file.file.seek(0)
            attachment_text = await extract_text_from_file(file)
            attachment_base64 = base64.b64encode(file_content).decode("utf-8")
            
            # Index to Supermemory for Perpetual Context
            from app.supermemory.client import SupermemoryClient
            sm_client = SupermemoryClient()
            background_tasks.add_task(
                sm_client.add_document,
                content=attachment_text,
                title=f"Chat Asset: {file.filename}",
                description=f"File uploaded in chat thread {thread_id}",
                metadata={
                    "user_id": actual_email,
                    "type": "chat_attachment",
                    "thread_id": thread_id,
                    "file_name": file.filename,
                    "source": "chat"
                }
            )
    
    # Save User Message to DB
    user_msg_db = ChatMessage(
        thread_id=thread_id,
        role="user",
        content=message,
        attachment=attachment_base64,
        attachment_type=file.content_type if file else None,
        file_name=file.filename if file else None
    )
    db.add(user_msg_db)
    thread.updated_at = datetime.utcnow()
    db.commit()

    # Classification & Retrieval
    # Log usage for triage (SLM usage)
    UsageTracker.log_usage(user_email, UsageTracker.count_tokens(message), is_input=True, category="slm")
    
    retriever = RetrievalOrchestrator(user_email)
    
    # Parse history for standard context
    short_term_history = []
    if history:
        try: short_term_history = json.loads(history)
        except: pass

    async def save_ai_response(resp_content: str, thread_id: str, u_email: str, q_msg: str, h_history: list, q_type: str, input_tokens: int):
        """Task to persist the AI response, track usage, and trigger learning."""
        from app.database import SessionLocal
        from app.models import ChatMessage
        import logging
        logger = logging.getLogger("uvicorn.error")
        
        logger.info(f"💾 [Persistence] Starting save for thread {thread_id}")
        gen_db = SessionLocal()
        try:
            # 1. Save Response
            ai_msg_db = ChatMessage(
                thread_id=thread_id,
                role="assistant",
                content=resp_content
            )
            gen_db.add(ai_msg_db)
            gen_db.commit()
            
            # 2. Track Usage (Main LLM usage)
            out_tokens = UsageTracker.count_tokens(resp_content)
            UsageTracker.log_usage(u_email, input_tokens, is_input=True, category="llm")
            UsageTracker.log_usage(u_email, out_tokens, is_input=False, category="llm")
            
            # 3. Global learning for Digital Twin
            from app.intelligence.memory_agent import MemoryAgent
            await MemoryAgent.synthesize_and_save(
                user_email=u_email, 
                query=q_msg, 
                response=resp_content,
                additional_context={"thread_id": thread_id, "query_type": q_type},
                conversation_history=h_history
            )
        except Exception as e:
            logger.error(f"Error in save_ai_response task: {e}")
        finally:
            gen_db.close()

    async def generate():
        full_response = ""
        q_type = "general_chat"
        c_data = {}
        
        try:
            # 🚀 Signal Thread ID
            yield f"data: THREAD_ID:{thread_id}\n\n"
            
            # 🧠 Start Thinking Events
            logger.info(f"🧠 [CHAT] Starting analysis for: {message[:100]}...")
            yield f"data: EVENT:THINKING:Analyzing neural patterns and history...\n\n"
            
            # Create tasks explicitly to avoid coroutine reuse issues
            t1 = asyncio.create_task(classify_query(message, base64_image))
            t2 = asyncio.create_task(retriever.retrieve_context(message, "academic_question", history=short_term_history))
            
            # Combine into one future for the effective gathering
            main_future = asyncio.gather(t1, t2, return_exceptions=True)
            
            # Monitoring loop with keep-alive pings
            while not main_future.done():
                try:
                    await asyncio.wait_for(asyncio.shield(main_future), timeout=1.5)
                    break
                except asyncio.TimeoutError:
                     yield f"data: EVENT:THINKING:Querying neural database...\n\n"
                except Exception as e:
                    logger.error(f"Error in gather loop: {e}")
                    break
            
            # Retrieve results safely
            results = await main_future
            
            # Task 1: Classification
            if isinstance(results[0], Exception):
                logger.error(f"Classification failed: {results[0]}")
                q_type = "general_chat"
            else:
                q_type = results[0]
                
            # Task 2: Retrieval
            if isinstance(results[1], Exception):
                logger.error(f"Retrieval failed: {results[1]}")
                c_data = {}
            else:
                c_data = results[1]
            
            # Extract and broadcast sources with metadata for linkability
            sources_metadata = []
            categories = {
                "course_context": "📚 ",
                "assistant_knowledge": "📧 ",
                "chat_assets": "📎 ",
                "memories": "🧠 Personal: ",
                "profile": "👤 Insight: "
            }
            
            seen_titles = set()
            for cat, prefix in categories.items():
                for item in c_data.get(cat, []):
                    meta = item.get("metadata", {})
                    
                    # Match unique title logic from PromptArchitect
                    course_name = meta.get('course_name') or meta.get('course_id') or "General Workspace"
                    base_title = meta.get('title') or meta.get('file_name') or "Institutional Document"
                    unique_title = f"{base_title} [{course_name}]"
                    
                    if cat == "assistant_knowledge":
                        unique_title = f"Email: {meta.get('subject') or meta.get('title') or 'Workspace Item'}"
                    elif cat == "chat_assets":
                        unique_title = f"Asset: {meta.get('file_name', 'Previous Asset')}"

                    link = meta.get("source_link") or meta.get("url")
                    
                    if unique_title and unique_title not in seen_titles:
                        seen_titles.add(unique_title)
                        sources_metadata.append({
                            "title": unique_title,
                            "display": f"{prefix}{unique_title}",
                            "link": link
                        })
            
            if sources_metadata:
                yield f"data: EVENT:SOURCES:{json.dumps(sources_metadata[:15])}\n\n"
                yield f"data: EVENT:THINKING:Synthesizing personalized response...\n\n"
                await asyncio.sleep(0.5)
            else:
                yield f"data: EVENT:THINKING:No specific documents found, using general intelligence...\n\n"
                await asyncio.sleep(0.3)

            yield f"data: EVENT:THINKING:Synthesizing response...\n\n"

            # 2. Build Final Prompt
            try:
                prompt_messages = PromptArchitect.build_prompt(
                    user_query=message,
                    retrieved_chunks=c_data.get("course_context", []),
                    assistant_knowledge=c_data.get("assistant_knowledge", []),
                    chat_assets=c_data.get("chat_assets", []),
                    memories=c_data.get("memories", []),
                    profile=c_data.get("profile", []),
                    history=short_term_history,
                    attachment_text=attachment_text,
                    base64_image=base64_image,
                    query_type=q_type,
                    rewritten_query=c_data.get("rewritten_query")
                )
            except Exception as e:
                logger.error(f"Prompt Building Failed: {e}")
                prompt_messages = [{"role": "user", "content": message}]

            input_tokens = UsageTracker.count_tokens(json.dumps(prompt_messages))
            
            if not settings.OPENAI_API_KEY:
                mock_resp = "Neural Link established. Please configure OpenAI API key in settings."
                for word in mock_resp.split():
                    yield f"data: {json.dumps({'token': word + ' '})}\n\n"
                    await asyncio.sleep(0.05)
                full_response = mock_resp
            else:
                try:
                    response = await client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=prompt_messages,
                        stream=True
                    )
                    
                    async for chunk in response:
                        if chunk.choices and chunk.choices[0].delta.content:
                            token = chunk.choices[0].delta.content
                            full_response += token
                            chunk_data = json.dumps({"token": token})
                            yield f"data: {chunk_data}\n\n"
                except Exception as openai_err:
                    logger.error(f"OpenAI Generation Error: {openai_err}")
                    error_msg = f"\n\n[Neural Link Warning]: Primary intelligence processing failed ({str(openai_err)}). Please try again or check your API quota."
                    full_response += error_msg
                    yield f"data: {json.dumps({'token': error_msg})}\n\n"
            
            # Enqueue background tasks
            try:
                background_tasks.add_task(save_ai_response, full_response, thread_id, actual_email, message, short_term_history, q_type, input_tokens)
            except Exception as e:
                logger.error(f"Failed to enqueue background task: {e}")
                
        except Exception as e:
            logger.error(f"Critical Stream Error: {str(e)}")
            import traceback
            traceback.print_exc()
            error_data = json.dumps({"token": f"Neural Link Error: {str(e)}"})
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
