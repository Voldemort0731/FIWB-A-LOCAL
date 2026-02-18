import logging
import tiktoken
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User
from app.utils.email import standardize_email

logger = logging.getLogger("uvicorn.error")

# --- PRICING CONFIGURATION (USD PER 1M TOKENS) ---

# SLM (e.g., GPT-4o-mini) - Used for Triage, Query Rewriting
SLM_INPUT_PRICE = 0.15 
SLM_OUTPUT_PRICE = 0.60

# LLM (e.g., GPT-4o) - Used for Main Response Generation
LLM_INPUT_PRICE = 5.00
LLM_OUTPUT_PRICE = 15.00

# SUPERMEMORY - Vector Search & Indexing overhead per token
# Includes embedding costs and vector DB compute approximations
SM_TOKEN_PRICE = 0.05 

class UsageTracker:
    @staticmethod
    def count_tokens(text: str, model: str = "gpt-4o") -> int:
        """Count tokens in a string."""
        if not text: return 0
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except:
            # Fallback to rough estimation if tiktoken fails
            return len(text) // 4

    @staticmethod
    def log_usage(user_email: str, tokens: int, is_input: bool = True, category: str = "slm", db: Session = None):
        user_email = standardize_email(user_email)
        local_db = False
        if db is None:
            db = SessionLocal()
            local_db = True
        try:
            # We use a sub-session or ensure we don't close the shared one
            user = db.query(User).filter(User.email == user_email).first()
            if not user: return

            if category == "slm":
                rate = SLM_INPUT_PRICE if is_input else SLM_OUTPUT_PRICE
            elif category == "llm":
                rate = LLM_INPUT_PRICE if is_input else LLM_OUTPUT_PRICE
            elif category == "supermemory":
                rate = SM_TOKEN_PRICE 
            else:
                rate = SLM_INPUT_PRICE 

            additional_cost = (tokens / 1_000_000.0) * rate
            
            if category != "supermemory":
                user.openai_tokens_used = (user.openai_tokens_used or 0) + tokens
            
            current_cost = float(user.estimated_cost_usd or "0.00")
            user.estimated_cost_usd = f"{(current_cost + additional_cost):.6f}"
            
            # Commit only if it's the final update or we are in charge of the session
            # For scale, we commit here but ideally would batch.
            db.commit()
        except:
            db.rollback()
        finally:
            if local_db:
                db.close()

    @staticmethod
    def log_sm_request(user_email: str, estimated_tokens: int = 500):
        user_email = standardize_email(user_email)
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == user_email).first()
            if user:
                user.supermemory_requests_count = (user.supermemory_requests_count or 0) + 1
                # Skip double commit inside log_usage by passing the session
                UsageTracker.log_usage(user_email, estimated_tokens, is_input=True, category="supermemory", db=db)
            db.commit()
        finally:
            db.close()

    @staticmethod
    def log_index_event(user_email: str, content: str = "", count: int = 1):
        user_email = standardize_email(user_email)
        tokens = UsageTracker.count_tokens(content) if content else 100
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == user_email).first()
            if user:
                user.supermemory_docs_indexed = (user.supermemory_docs_indexed or 0) + count
                UsageTracker.log_usage(user_email, tokens, is_input=True, category="supermemory", db=db)
            db.commit()
        finally:
            db.close()

    @staticmethod
    def log_lms_request(user_email: str, count: int = 1, db: Session = None):
        user_email = standardize_email(user_email)
        local_db = False
        if db is None:
            db = SessionLocal()
            local_db = True
        try:
            user = db.query(User).filter(User.email == user_email).first()
            if user:
                user.lms_api_requests_count = (user.lms_api_requests_count or 0) + count
                db.commit()
        except: pass
        finally: 
            if local_db:
                db.close()
