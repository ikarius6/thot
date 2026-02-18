from sqlalchemy import create_engine, text
from database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        try:
            # Check if column exists
            result = conn.execute(text("PRAGMA table_info(images)"))
            columns = [row[1] for row in result.fetchall()]
            
            if "is_active" not in columns:
                print("Adding is_active column to images table...")
                conn.execute(text("ALTER TABLE images ADD COLUMN is_active BOOLEAN DEFAULT 1"))
                conn.commit()
                print("Migration successful: is_active column added.")
            else:
                print("Column is_active already exists.")
                
        except Exception as e:
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
