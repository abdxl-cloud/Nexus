import uuid
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from agent import AgentLoop
from db.models import get_db, User, Thread, Message, Run
from config import get_settings
from .utils import (
    run_manager,
    validate_role,
    get_thread_by_id,
    get_run_by_id,
    create_user_with_defaults,
    create_thread_with_defaults,
    create_message_with_defaults,
    create_run_with_defaults,
    update_run_in_db,
    sanitize_content
)

router = APIRouter()
settings = get_settings()

# Request/Response Models
class CreateThreadRequest(BaseModel):
    user_id: Optional[str] = None

class CreateThreadResponse(BaseModel):
    thread_id: str

class CreateMessageRequest(BaseModel):
    role: str
    content: str

class CreateMessageResponse(BaseModel):
    run_id: str

# Utility Functions
def get_or_create_user(db: Session, user_id: Optional[str] = None) -> User:
    """Get existing user or create a new one"""
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user
    
    # Create new user using utility function
    return create_user_with_defaults(db, user_id)

async def execute_agent_run(run_id: str, thread_id: str, user_message: str, db: Session):
    """Execute agent run in background"""
    try:
        # Update run status to running
        update_run_in_db(db, run_id, "running")
        
        # Store run data for SSE streaming using run manager
        run_manager.create_run_data(run_id, thread_id, sanitize_content(user_message))
        
        # Initialize agent loop
        agent_loop = AgentLoop()
        
        # Collect all agent responses
        agent_responses = []
        async for response in agent_loop.run(user_message):
            # Add token events
            if "content" in response:
                run_manager.add_event(run_id, "token", response["content"])
            
            # Add tool events
            if "tool_call" in response:
                run_manager.add_event(run_id, "tool", response["tool_call"])
            
            if "tool_result" in response:
                run_manager.add_event(run_id, "tool", response["tool_result"])
            
            agent_responses.append(response)
        
        # Get final response content
        final_content = ""
        for response in agent_responses:
            if "content" in response:
                final_content += response["content"]
        
        # Sanitize final content
        final_content = sanitize_content(final_content)
        
        # Create assistant message in database
        create_message_with_defaults(db, thread_id, "assistant", final_content)
        
        # Add final done event
        run_manager.add_event(run_id, "done", {
            "message": final_content,
            "status": "completed"
        })
        
        # Update run status to completed
        update_run_in_db(db, run_id, "completed", final_content)
        run_manager.update_status(run_id, "completed")
        
    except Exception as e:
        # Handle errors
        error_message = f"Error executing run: {str(e)}"
        run_manager.add_event(run_id, "error", {"error": error_message})
        run_manager.update_status(run_id, "failed")
        update_run_in_db(db, run_id, "failed", error_message)

# API Endpoints
@router.post("/threads", response_model=CreateThreadResponse)
async def create_thread(request: CreateThreadRequest, db: Session = Depends(get_db)):
    """Create a new thread"""
    try:
        # Get or create user
        user = get_or_create_user(db, request.user_id)
        
        # Create thread
        thread = create_thread_with_defaults(db, user.id)
        
        return CreateThreadResponse(thread_id=thread.id)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create thread: {str(e)}")

@router.post("/threads/{thread_id}/messages", response_model=CreateMessageResponse)
async def create_message(thread_id: str, request: CreateMessageRequest, db: Session = Depends(get_db)):
    """Create a message and start a run"""
    try:
        # Verify thread exists
        thread = get_thread_by_id(db, thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Validate role
        if not validate_role(request.role):
            raise HTTPException(status_code=400, detail="Role must be 'user', 'assistant', or 'system'")
        
        # Sanitize content
        sanitized_content = sanitize_content(request.content)
        
        # Create message record
        message = create_message_with_defaults(db, thread_id, request.role, sanitized_content)
        
        # If it's a user message, create and start a run
        if request.role == "user":
            # Create run record
            run = create_run_with_defaults(db, thread_id, "queued")
            
            # Start background task to execute the run
            asyncio.create_task(execute_agent_run(run.id, thread_id, sanitized_content, db))
            
            return CreateMessageResponse(run_id=run.id)
        else:
            # For assistant messages, create a dummy run (or handle differently)
            run = create_run_with_defaults(db, thread_id, "completed")
            return CreateMessageResponse(run_id=run.id)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create message: {str(e)}")

@router.get("/runs/{run_id}/events")
async def get_run_events(run_id: str, request: Request, db: Session = Depends(get_db)):
    """Stream run events via SSE with proper event formatting"""
    # Verify run exists
    run = get_run_by_id(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    async def event_stream():
        """Generate SSE events with proper formatting and heartbeat"""
        import time
        
        last_event_index = 0
        last_heartbeat = time.time()
        
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                
                # Check if run exists in active runs
                run_data = run_manager.get_run_data(run_id)
                if run_data:
                    # Get new events since last index
                    new_events = run_manager.get_events_since(run_id, last_event_index)
                    
                    # Send new events with proper type/data structure
                    for event in new_events:
                        event_type = event.get("event", "message")
                        event_data = {
                            "type": event_type,
                            "data": event["data"]
                        }
                        yield f"event: {event_type}\n"
                        yield f"data: {json.dumps(event_data)}\n\n"
                        last_event_index += 1
                    
                    # Check if run is completed
                    if run_data["status"] in ["completed", "failed"]:
                        final_data = {
                            "type": "run_completed",
                            "status": run_data["status"]
                        }
                        yield f"event: done\n"
                        yield f"data: {json.dumps(final_data)}\n\n"
                        break
                else:
                    # Run not in active runs, check database status
                    db.refresh(run)
                    if run.status in ["completed", "failed"]:
                        # Send final event if not already sent
                        final_data = {
                            "type": "run_completed",
                            "message": run.result or "Run completed",
                            "status": run.status
                        }
                        yield f"event: done\n"
                        yield f"data: {json.dumps(final_data)}\n\n"
                        break
                
                # Send heartbeat every 15 seconds
                current_time = time.time()
                if current_time - last_heartbeat >= 15:
                    heartbeat_data = {
                        "type": "heartbeat",
                        "timestamp": int(current_time)
                    }
                    yield f"event: heartbeat\n"
                    yield f"data: {json.dumps(heartbeat_data)}\n\n"
                    last_heartbeat = current_time
                
                # Wait before checking for new events
                await asyncio.sleep(0.1)
                
        except Exception as e:
            error_data = {
                "type": "error",
                "message": str(e)
            }
            yield f"event: error\n"
            yield f"data: {json.dumps(error_data)}\n\n"
        finally:
            # Clean up active run data
            run_manager.cleanup_run(run_id)
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0"
    }