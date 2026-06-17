import sqlite3
from app.config import settings

def migrate():
    db_path = settings.database.path
    print(f"Migrating database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if we need to migrate
    try:
        cursor.execute("PRAGMA foreign_keys=off;")
        cursor.execute("BEGIN TRANSACTION;")
        
        # Create new table with updated constraints
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback_reports_new (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL UNIQUE,
            resume_id TEXT NOT NULL,
            overall_score REAL CHECK(overall_score BETWEEN 0 AND 100),
            technical_score REAL CHECK(technical_score BETWEEN 0 AND 100),
            behavioral_score REAL CHECK(behavioral_score BETWEEN 0 AND 100),
            coding_score REAL CHECK(coding_score BETWEEN 0 AND 100),
            hiring_recommendation TEXT
                CHECK(hiring_recommendation IN ('strong_hire', 'hire', 'maybe', 'no_hire', 'PASS', 'FAIL', 'Pass', 'Fail')),
            strengths TEXT,           
            weaknesses TEXT,          
            improvement_roadmap TEXT, 
            detailed_feedback TEXT,   
            summary TEXT,             
            category_breakdown TEXT,  
            interviewer_notes TEXT,   
            report_version INTEGER DEFAULT 1,
            generated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
        );
        """)
        
        # Copy data
        cursor.execute("INSERT INTO feedback_reports_new SELECT * FROM feedback_reports;")
        
        # Drop old table
        cursor.execute("DROP TABLE feedback_reports;")
        
        # Rename new table
        cursor.execute("ALTER TABLE feedback_reports_new RENAME TO feedback_reports;")
        
        cursor.execute("COMMIT;")
        cursor.execute("PRAGMA foreign_keys=on;")
        print("Migration successful.")
        
    except Exception as e:
        cursor.execute("ROLLBACK;")
        cursor.execute("PRAGMA foreign_keys=on;")
        print(f"Migration failed or already applied: {e}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
