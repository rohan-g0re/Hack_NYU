#!/usr/bin/env python3
"""
Database migration script: Add llm_provider column to sessions table.

WHAT: Adds the llm_provider column to existing databases
WHY: Support per-session LLM provider selection
HOW: ALTER TABLE with default value

Usage:
    python migrate_add_provider.py
"""

import sqlite3
import sys
from pathlib import Path

# Database path (relative to backend directory)
DB_PATH = Path(__file__).parent / "data" / "marketplace.db"


def migrate():
    """Add llm_provider column to sessions table if it doesn't exist."""
    
    if not DB_PATH.exists():
        print(f"[OK] Database does not exist yet at {DB_PATH}")
        print("   No migration needed - the column will be created automatically.")
        return
    
    print(f"[*] Migrating database: {DB_PATH}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'llm_provider' in columns:
            print("[OK] Column 'llm_provider' already exists in sessions table.")
            print("   No migration needed.")
            conn.close()
            return
        
        # Add the column with default value
        print("[+] Adding 'llm_provider' column to sessions table...")
        cursor.execute("""
            ALTER TABLE sessions 
            ADD COLUMN llm_provider VARCHAR(20) NOT NULL DEFAULT 'lm_studio'
        """)
        
        conn.commit()
        print("[OK] Migration completed successfully!")
        print(f"   Added 'llm_provider' column to sessions table")
        
        # Verify the change
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'llm_provider' in columns:
            print("[OK] Verified: Column exists in database")
        else:
            print("[!] Warning: Column was not added successfully")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"[ERROR] Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("Database Migration: Add LLM Provider Column")
    print("=" * 60)
    migrate()
    print("=" * 60)
    print("\n[SUCCESS] Migration script completed!")
    print("\nNext steps:")
    print("  1. Start the backend: python -m app.main")
    print("  2. Use the frontend to select LM Studio or OpenRouter")
    print("  3. Each session will remember its provider choice")

