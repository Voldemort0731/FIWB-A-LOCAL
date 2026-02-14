import sqlite3

def migrate():
    conn = sqlite3.connect('fiwb.db')
    cursor = conn.cursor()
    
    columns = [
        ("openai_tokens_used", "INTEGER DEFAULT 0"),
        ("supermemory_docs_indexed", "INTEGER DEFAULT 0"),
        ("supermemory_requests_count", "INTEGER DEFAULT 0"),
        ("lms_api_requests_count", "INTEGER DEFAULT 0"),
        ("estimated_cost_usd", "TEXT DEFAULT '0.00'")
    ]
    
    for col_name, col_type in columns:
        try:
            print(f"Adding {col_name} to users...")
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            print(f"{col_name} already exists.")
            
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
