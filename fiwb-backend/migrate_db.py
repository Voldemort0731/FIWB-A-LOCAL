"""
Database migration script to add token_expiry column to users table.
Run this once to update your existing database.
"""
import sqlite3
from datetime import datetime

def migrate_database():
    conn = sqlite3.connect('fiwb.db')
    cursor = conn.cursor()
    
    # Check if token_expiry column exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'token_expiry' not in columns:
        print("Adding token_expiry column to users table...")
        cursor.execute("ALTER TABLE users ADD COLUMN token_expiry DATETIME")
        conn.commit()
        print("✅ Migration complete!")
    else:
        print("✅ Database already up to date!")
    
    conn.close()

if __name__ == "__main__":
    migrate_database()
