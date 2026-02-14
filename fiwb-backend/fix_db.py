import sqlite3
import os

db_path = "/Users/owaissayyed/Github Repos/FIWB-A-LOCAL-main/fiwb-backend/fiwb.db"

def fix_db():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Checking materials table schema...")
    cursor.execute("PRAGMA table_info(materials)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'user_id' not in columns:
        print("Adding user_id column to materials table...")
        try:
            cursor.execute("ALTER TABLE materials ADD COLUMN user_id INTEGER REFERENCES users(id)")
            conn.commit()
            print("Successfully added user_id column.")
        except Exception as e:
            print(f"Error adding column: {e}")
    else:
        print("user_id column already exists.")

    conn.close()

if __name__ == "__main__":
    fix_db()
