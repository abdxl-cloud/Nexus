from sqlalchemy import create_engine, Column, String, Text, Integer, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
from typing import Optional, List, Dict, Any
from config import settings

Base = declarative_base()

# Database engine and session
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class User(Base):
    """User model"""
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    email = Column(Text)
    name = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    threads = relationship("Thread", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id})>"

class Thread(Base):
    """Thread model"""
    __tablename__ = 'threads'
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    title = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="threads")
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="thread", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="thread", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Thread(id={self.id}, user_id={self.user_id})>"

class Message(Base):
    """Message model"""
    __tablename__ = 'messages'
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    thread_id = Column(UUID(as_uuid=True), ForeignKey('threads.id', ondelete='CASCADE'), nullable=False)
    role = Column(Text, nullable=False)
    content = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Add check constraint for role
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'tool', 'system')", name='check_message_role'),
    )
    
    # Relationships
    thread = relationship("Thread", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role}')>"

class Run(Base):
    """Run model"""
    __tablename__ = 'runs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    thread_id = Column(UUID(as_uuid=True), ForeignKey('threads.id', ondelete='CASCADE'), nullable=False)
    status = Column(Text, nullable=False)
    tokens_used = Column(Integer, default=0)
    result = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Add check constraint for status
    __table_args__ = (
        CheckConstraint("status IN ('queued', 'running', 'completed', 'error')", name='check_run_status'),
    )
    
    # Relationships
    thread = relationship("Thread", back_populates="runs")
    
    def __repr__(self):
        return f"<Run(id={self.id}, status='{self.status}')>"

class Artifact(Base):
    """Artifact model"""
    __tablename__ = 'artifacts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    thread_id = Column(UUID(as_uuid=True), ForeignKey('threads.id', ondelete='CASCADE'), nullable=False)
    name = Column(Text, nullable=False)
    path = Column(Text)
    mime = Column(Text)
    meta = Column(JSONB, server_default='{}')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    thread = relationship("Thread", back_populates="artifacts")
    
    def __repr__(self):
        return f"<Artifact(id={self.id}, name='{self.name}')>"

# Create all tables
def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def drop_tables():
    """Drop all database tables"""
    Base.metadata.drop_all(bind=engine)

# Database utility functions
def get_or_create_user(db: SessionLocal, user_id: Optional[str] = None) -> User:
    """Get or create a user"""
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user
    
    user = User()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_thread(db: SessionLocal, user_id: str) -> Thread:
    """Create a new thread"""
    thread = Thread(user_id=user_id)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread

def add_message(db: SessionLocal, thread_id: str, role: str, content: Dict[str, Any]) -> Message:
    """Add a message to a thread"""
    message = Message(
        thread_id=thread_id,
        role=role,
        content=content
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

def get_thread_messages(db: SessionLocal, thread_id: str, limit: int = 50) -> List[Message]:
    """Get messages for a thread"""
    return db.query(Message).filter(
        Message.thread_id == thread_id
    ).order_by(Message.created_at.desc()).limit(limit).all()

def create_run(db: SessionLocal, thread_id: str, status: str = 'queued') -> Run:
    """Create a new run"""
    run = Run(
        thread_id=thread_id,
        status=status
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run

def create_artifact(db: SessionLocal, thread_id: str, name: str, path: Optional[str] = None, mime: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> Artifact:
    """Create a new artifact"""
    artifact = Artifact(
        thread_id=thread_id,
        name=name,
        path=path,
        mime=mime,
        meta=meta or {}
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact