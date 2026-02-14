from app.database import engine, Base
from app.models import User, Course, Material

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully.")

from app.database import SessionLocal
db = SessionLocal()
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"Tables currently in DB: {tables}")
db.close()
