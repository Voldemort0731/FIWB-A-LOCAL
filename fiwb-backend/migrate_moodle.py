import sqlite3
import os

db_path = "fiwb.db"

if not os.path.exists(db_path):
    print(f"Database {db_path} not found.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Adding moodle_url column...")
        cursor.execute("ALTER TABLE users ADD COLUMN moodle_url TEXT")
    except sqlite3.OperationalError:
        print("moodle_url already exists or table doesn't exist.")
        
    try:
        print("Adding moodle_token column...")
        cursor.execute("ALTER TABLE users ADD COLUMN moodle_token TEXT")
    except sqlite3.OperationalError:
        print("moodle_token already exists.")

    try:
        print("Adding watched_drive_folders column...")
        cursor.execute("ALTER TABLE users ADD COLUMN watched_drive_folders TEXT")
    except sqlite3.OperationalError:
        print("watched_drive_folders already exists.")

    try:
        print("Adding registration_id column...")
        cursor.execute("ALTER TABLE users ADD COLUMN registration_id TEXT")
    except sqlite3.OperationalError:
        print("registration_id already exists.")

    try:
        print("Adding last_synced to users...")
        cursor.execute("ALTER TABLE users ADD COLUMN last_synced DATETIME")
    except sqlite3.OperationalError: pass

    try:
        print("Adding last_synced to courses...")
        cursor.execute("ALTER TABLE courses ADD COLUMN last_synced DATETIME")
    except sqlite3.OperationalError: pass
        
    conn.commit()
    conn.close()
    print("Migration complete.")
