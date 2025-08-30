import os
import asyncio
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from backend.api import router  # Fixed import
from backend.config import get_settings  # Fixed import
from backend.db.models import engine, Base  # Fixed import
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get settings instance
settings = get_settings()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log effective configuration (non-secret values only)
logger.info("Starting Suna Lite with configuration:")
logger.info(f"  HOST: {settings.HOST}")
logger.info(f"  PORT: {settings.PORT}")
logger.info(f"  DEBUG: {settings.DEBUG}")
logger.info(f"  DATABASE_URL: {settings.DATABASE_URL.split('@')[0]}@***" if '@' in settings.DATABASE_URL else "***")
logger.info(f"  COEXISTAI_BASE_URL: {settings.COEXISTAI_BASE_URL}")
logger.info(f"  RUNNER_BASE_URL: {settings.RUNNER_BASE_URL}")
logger.info(f"  MAX_ITERATIONS: {settings.MAX_ITERATIONS}")
logger.info(f"  TIMEOUT_SECONDS: {settings.TIMEOUT_SECONDS}")
logger.info(f"  CORS_ORIGINS: {settings.CORS_ORIGINS}")
logger.info(f"  OPENAI_API_KEY: {'***' if settings.OPENAI_API_KEY else 'Not set'}")
logger.info(f"  COEXISTAI_API_KEY: {'***' if settings.COEXISTAI_API_KEY else 'Not set'}")

app = FastAPI(
    title="Suna Lite",
    description="A minimal ReAct-style agent with streaming capabilities",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")

async def bootstrap_database():
    """Bootstrap database by running schema.sql if tables are missing"""
    try:
        # Check if tables exist by trying to query one of them
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
            ))
            tables_exist = result.scalar()
            
            if not tables_exist:
                print("Tables not found. Running schema.sql...")
                
                # Read and execute schema.sql
                schema_path = Path(__file__).parent / "db" / "schema.sql"
                if schema_path.exists():
                    with open(schema_path, 'r') as f:
                        schema_sql = f.read()
                    
                    # Split by semicolon and execute each statement
                    statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                    for statement in statements:
                        if statement:
                            conn.execute(text(statement))
                    
                    conn.commit()
                    print("Database schema created successfully.")
                else:
                    print("Warning: schema.sql not found. Creating tables with SQLAlchemy...")
                    Base.metadata.create_all(bind=engine)
            else:
                print("Database tables already exist.")
                
                 # Ensure 'result' column exists in 'runs' table
                result_column = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='runs' AND column_name='result'"
                )).fetchone()
                if not result_column:
                    conn.execute(text("ALTER TABLE runs ADD COLUMN result TEXT"))
                    conn.commit()
                    print("Added 'result' column to runs table.")
                    
                # Ensure timestamp columns exist on users table
                col_result = conn.execute(text(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'users'
                    """
                ))
                columns = {row[0] for row in col_result}

                alter_statements = []
                if 'created_at' not in columns:
                    alter_statements.append(
                        "ALTER TABLE users ADD COLUMN created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP"
                    )
                if 'updated_at' not in columns:
                    alter_statements.append(
                        "ALTER TABLE users ADD COLUMN updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP"
                    )

                for stmt in alter_statements:
                    conn.execute(text(stmt))

                if alter_statements:
                    conn.commit()
                    print("Added missing timestamp columns to users table.")

                # Ensure updated_at trigger exists for users table
                trigger_result = conn.execute(text(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM pg_trigger WHERE tgname = 'update_users_updated_at'
                    )
                    """
                ))
                trigger_exists = trigger_result.scalar()
                if not trigger_exists:
                    conn.execute(text(
                        """
                        CREATE TRIGGER update_users_updated_at
                        BEFORE UPDATE ON users
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
                        """
                    ))
                    conn.commit()
                    print("Created update_users_updated_at trigger for users table.")
                
    except Exception as e:
        print(f"Database bootstrap error: {e}")
        # Fallback to SQLAlchemy table creation
        try:
            Base.metadata.create_all(bind=engine)
            print("Fallback: Tables created with SQLAlchemy.")
        except Exception as fallback_error:
            print(f"Fallback failed: {fallback_error}")

@app.on_event("startup")
async def startup_event():
    """Run database bootstrap on startup"""
    await bootstrap_database()

@app.get("/")
async def root():
    return {"message": "Suna Lite Agent API", "version": "0.1.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
    