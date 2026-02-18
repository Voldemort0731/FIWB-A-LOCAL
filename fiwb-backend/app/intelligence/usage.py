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
        """
        Update user's usage and estimated cost based on categorical pricing.
        Categories: 'slm', 'llm', 'supermemory'
        """
        user_email = standardize_email(user_email)
        local_db = False
        if db is None:
            try:
                db = SessionLocal()
                local_db = True
            except Exception as e:
                logger.error(f"❌ UsageTracker failed to get DB session: {e}")
                return
        try:
            user = db.query(User).filter(User.email == user_email).first()
            if not user: return

            # Calculate cost based on category
            if category == "slm":
                rate = SLM_INPUT_PRICE if is_input else SLM_OUTPUT_PRICE
            elif category == "llm":
                rate = LLM_INPUT_PRICE if is_input else LLM_OUTPUT_PRICE
            elif category == "supermemory":
                rate = SM_TOKEN_PRICE # Flat rate for SM tokens (indexing/search)
            else:
                rate = SLM_INPUT_PRICE # Fallback

            additional_cost = (tokens / 1_000_000.0) * rate
            
            # Update User stats
            if category != "supermemory":
                user.openai_tokens_used = (user.openai_tokens_used or 0) + tokens
            
            current_cost = float(user.estimated_cost_usd or "0.00")
            new_cost = current_cost + additional_cost
            user.estimated_cost_usd = f"{new_cost:.6f}"
            
            db.commit()
            if tokens > 5: # Only log non-trivial usage
                logger.info(f"💰 [{category.upper()}] {tokens} tokens for {user_email}. Cost: +${additional_cost:.6f} | Total: ${user.estimated_cost_usd}")
        except Exception as e:
            logger.error(f"Error logging usage for {user_email}: {e}")
        finally:
            if local_db:
                db.close()

    @staticmethod
    def log_sm_request(user_email: str, estimated_tokens: int = 500):
        """Log a Supermemory request with estimated token overhead."""
        user_email = standardize_email(user_email)
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == user_email).first()
            if user:
                user.supermemory_requests_count = (user.supermemory_requests_count or 0) + 1
                db.commit()
            
            # Use same session for cost logging
            UsageTracker.log_usage(user_email, estimated_tokens, is_input=True, category="supermemory", db=db)
        except Exception as e:
            logger.error(f"Error logging SM request for {user_email}: {e}")
        finally:
            db.close()

    @staticmethod
    def log_index_event(user_email: str, content: str = "", count: int = 1):
        """Log a document indexing event with actual token count."""
        user_email = standardize_email(user_email)
        tokens = UsageTracker.count_tokens(content) if content else 100
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == user_email).first()
            if user:
                user.supermemory_docs_indexed = (user.supermemory_docs_indexed or 0) + count
                db.commit()
            
            # Use same session for cost logging
            UsageTracker.log_usage(user_email, tokens, is_input=True, category="supermemory", db=db)
        except Exception as e:
            logger.error(f"Error logging index event for {user_email}: {e}")
        finally:
            db.close()

    @staticmethod
    def log_lms_request(user_email: str, count: int = 1, db: Session = None):
        """Log LMS API requests (Google, Moodle, etc)."""
        user_email = standardize_email(user_email)
        local_db = False
        if db is None:
            db = SessionLocal()
            local_db = True
        try:
            user = db.query(User).filter(User.email == user_email).first()
            if not user: return
            user.lms_api_requests_count = (user.lms_api_requests_count or 0) + count
            db.commit()
            if count > 0:
                logger.info(f"🌐 [LMS] {count} API calls for {user_email}")
        except: pass
        finally: 
            if local_db:
                db.close()
