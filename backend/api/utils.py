"""Utility functions for API routes"""

import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.models import User, Thread, Message, Run

# Type definitions
RunEvent = Dict[str, Any]
RunData = Dict[str, Any]

class RunManager:
    """Manages active runs and their events"""
    
    def __init__(self):
        self.active_runs: Dict[str, RunData] = {}
    
    def create_run_data(self, run_id: str, thread_id: str, user_message: str) -> RunData:
        """Create initial run data structure"""
        run_data = {
            "status": "running",
            "events": [],
            "thread_id": thread_id,
            "user_message": user_message,
            "created_at": datetime.utcnow().isoformat()
        }
        self.active_runs[run_id] = run_data
        return run_data
    
    def add_event(self, run_id: str, event_type: str, data: Any) -> None:
        """Add an event to a run"""
        if run_id in self.active_runs:
            event = {
                "event": event_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.active_runs[run_id]["events"].append(event)
    
    def update_status(self, run_id: str, status: str) -> None:
        """Update run status"""
        if run_id in self.active_runs:
            self.active_runs[run_id]["status"] = status
            self.active_runs[run_id]["updated_at"] = datetime.utcnow().isoformat()
    
    def get_run_data(self, run_id: str) -> Optional[RunData]:
        """Get run data by ID"""
        return self.active_runs.get(run_id)
    
    def cleanup_run(self, run_id: str) -> None:
        """Remove run data from memory"""
        if run_id in self.active_runs:
            del self.active_runs[run_id]
    
    def get_events_since(self, run_id: str, last_index: int) -> List[RunEvent]:
        """Get events since a specific index"""
        if run_id in self.active_runs:
            events = self.active_runs[run_id]["events"]
            return events[last_index:]
        return []

# Global run manager instance
run_manager = RunManager()

def generate_uuid() -> str:
    """Generate a new UUID string"""
    return str(uuid.uuid4())

def validate_role(role: str) -> bool:
    """Validate message role"""
    return role in ["user", "assistant", "system"]

def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()

def get_thread_by_id(db: Session, thread_id: str) -> Optional[Thread]:
    """Get thread by ID"""
    return db.query(Thread).filter(Thread.id == thread_id).first()

def get_run_by_id(db: Session, run_id: str) -> Optional[Run]:
    """Get run by ID"""
    return db.query(Run).filter(Run.id == run_id).first()

def get_thread_messages(db: Session, thread_id: str, limit: int = 50) -> List[Message]:
    """Get messages for a thread"""
    return (
        db.query(Message)
        .filter(Message.thread_id == thread_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
        .all()
    )

def get_user_threads(db: Session, user_id: str, limit: int = 20) -> List[Thread]:
    """Get threads for a user"""
    return (
        db.query(Thread)
        .filter(Thread.user_id == user_id)
        .order_by(desc(Thread.updated_at))
        .limit(limit)
        .all()
    )

def create_user_with_defaults(db: Session, user_id: Optional[str] = None) -> User:
    """Create a new user with default values"""
    user_id = user_id or generate_uuid()
    
    user = User(
        id=user_id,
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        name=f"User {uuid.uuid4().hex[:8]}",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_thread_with_defaults(db: Session, user_id: str, title: Optional[str] = None) -> Thread:
    """Create a new thread with default values"""
    thread = Thread(
        id=generate_uuid(),
        user_id=user_id,
        title=title or "New Conversation",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread

def create_message_with_defaults(db: Session, thread_id: str, role: str, content: str) -> Message:
    """Create a new message with default values"""
    message = Message(
        id=generate_uuid(),
        thread_id=thread_id,
        role=role,
        content=content,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

def create_run_with_defaults(db: Session, thread_id: str, status: str = "queued") -> Run:
    """Create a new run with default values"""
    run = Run(
        id=generate_uuid(),
        thread_id=thread_id,
        status=status,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(run)
    db.commit()
    db.refresh(run)
    return run

def update_run_in_db(db: Session, run_id: str, status: str, result: Optional[str] = None) -> bool:
    """Update run status and result in database"""
    run = get_run_by_id(db, run_id)
    if run:
        run.status = status
        if result is not None:
            run.result = result
        run.updated_at = datetime.utcnow()
        db.commit()
        return True
    return False

def format_message_for_api(message: Message) -> Dict[str, Any]:
    """Format message for API response"""
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "updated_at": message.updated_at.isoformat() if message.updated_at else None
    }

def format_thread_for_api(thread: Thread) -> Dict[str, Any]:
    """Format thread for API response"""
    return {
        "id": thread.id,
        "user_id": thread.user_id,
        "title": thread.title,
        "created_at": thread.created_at.isoformat() if thread.created_at else None,
        "updated_at": thread.updated_at.isoformat() if thread.updated_at else None
    }

def format_run_for_api(run: Run) -> Dict[str, Any]:
    """Format run for API response"""
    return {
        "id": run.id,
        "thread_id": run.thread_id,
        "status": run.status,
        "result": run.result,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None
    }

async def wait_for_run_completion(run_id: str, timeout: int = 300) -> bool:
    """Wait for a run to complete with timeout"""
    start_time = asyncio.get_event_loop().time()
    
    while True:
        run_data = run_manager.get_run_data(run_id)
        if not run_data:
            return False
        
        if run_data["status"] in ["completed", "failed"]:
            return True
        
        # Check timeout
        if asyncio.get_event_loop().time() - start_time > timeout:
            return False
        
        await asyncio.sleep(0.1)

def sanitize_content(content: str, max_length: int = 10000) -> str:
    """Sanitize and truncate content"""
    if not content:
        return ""
    
    # Remove any potentially harmful characters
    sanitized = content.strip()
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    return sanitized

def validate_uuid(uuid_string: str) -> bool:
    """Validate UUID format"""
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False