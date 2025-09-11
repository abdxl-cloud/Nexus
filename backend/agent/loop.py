"""Agent Loop Implementation with OpenAI Integration and Tool Execution"""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional, AsyncIterator, Tuple
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db import get_db
from backend.db.models import Thread, Message, Run
from backend.agent.tools import get_default_tools, ToolCall, ToolResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = "You are a helpful agent. Use tools when needed. Stop when done."

class AgentLoop:
    """Main agent loop for handling conversations and tool execution"""
    
    def __init__(self):
        self.settings = get_settings()
        self.tools = get_default_tools()
        self.tool_schemas = self._build_tool_schemas()
        self.max_iterations = 2  # MVP limit
    
    def _build_tool_schemas(self) -> List[Dict[str, Any]]:
        """Build OpenAI-compatible tool schemas"""
        schemas = []
        for tool in self.tools:
            schemas.append(tool.schema)
        return schemas
    
    async def run_agent(self, thread_id: uuid.UUID, last_user_message: str) -> Tuple[str, AsyncIterator[str]]:
        """Main agent execution function"""
        logger.info(f"Starting agent run for thread {thread_id}")
        
        # Load conversation history
        messages = self._load_conversation_history(thread_id)
        
        # Add the new user message
        messages.append({
            "role": "user",
            "content": last_user_message
        })
        
        # Execute agent loop with tool calls
        final_response, events = await self._execute_agent_loop(messages)
        
        # Save final assistant message to DB
        self._save_assistant_message(thread_id, final_response)
        
        return final_response, events
    
    def _load_conversation_history(self, thread_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Load last ~20 messages from database"""
        db = next(get_db())
        try:
            messages = db.query(Message).filter(
                Message.thread_id == thread_id
            ).order_by(Message.created_at.desc()).limit(20).all()
            
            # Convert to OpenAI format and reverse to chronological order
            openai_messages = [{
                "role": "system",
                "content": SYSTEM_PROMPT
            }]
            
            for msg in reversed(messages):
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            return openai_messages
        finally:
            db.close()
    
    def _save_assistant_message(self, thread_id: uuid.UUID, content: str) -> None:
        """Save assistant message to database"""
        db = next(get_db())
        try:
            message = Message(
                id=uuid.uuid4(),
                thread_id=thread_id,
                role="assistant",
                content=content,
                created_at=datetime.utcnow()
            )
            db.add(message)
            db.commit()
            logger.info(f"Saved assistant message for thread {thread_id}")
        except Exception as e:
            logger.error(f"Failed to save assistant message: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def _execute_agent_loop(self, messages: List[Dict[str, Any]]) -> Tuple[str, AsyncIterator[str]]:
        """Execute the main agent loop with tool calls"""
        current_messages = messages.copy()
        iteration = 0
        events = []
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"Agent iteration {iteration}")
            
            # Get model response
            if self.settings.OPENAI_API_KEY:
                response = await self._call_openai_api(current_messages)
            else:
                response = self._simulate_openai_response(current_messages)
            
            # Check if model wants to use tools
            tool_calls = response.get("tool_calls", [])
            
            if not tool_calls:
                # No tools requested, return final response
                final_content = response.get("content", "I'm ready to help!")
                events.append({"type": "message", "content": final_content})
                return final_content, self._create_event_stream(events)
            
            # Add assistant message with tool calls
            current_messages.append({
                "role": "assistant",
                "content": response.get("content", ""),
                "tool_calls": tool_calls
            })
            
            # Execute tool calls
            for tool_call in tool_calls:
                events.append({"type": "tool_call", "tool_call": tool_call})
                
                tool_result = await self._execute_tool_call(tool_call)
                events.append({"type": "tool_result", "result": tool_result.model_dump()})
                
                # Add tool result as message
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", str(uuid.uuid4())),
                    "content": json.dumps(tool_result.data) if hasattr(tool_result, 'data') else str(tool_result)
                })
        
        # If we've reached max iterations, return last response
        final_content = "I've completed the available iterations."
        events.append({"type": "message", "content": final_content})
        return final_content, self._create_event_stream(events)
    
    async def _call_openai_api(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Call OpenAI Chat Completions API"""
        headers = {
            "Authorization": f"Bearer {self.settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": messages,
            "tools": self.tool_schemas,
            "tool_choice": "auto"
        }
        
        logger.info("Calling OpenAI API")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                raise Exception(f"OpenAI API failed: {response.status_code}")
            
            data = response.json()
            choice = data["choices"][0]
            message = choice["message"]
            
            return {
                "content": message.get("content", ""),
                "tool_calls": message.get("tool_calls", [])
            }
    
    def _simulate_openai_response(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simulate OpenAI response when API key is not available"""
        logger.info("Simulating OpenAI response (no API key)")
        
        last_message = messages[-1] if messages else {}
        user_content = last_message.get("content", "")
        
        # Simple heuristic to decide if we should use web search
        if any(keyword in user_content.lower() for keyword in ["search", "find", "what is", "who is", "when", "where"]):
            return {
                "content": f"I will search for information about: {user_content}",
                "tool_calls": [{
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "arguments": json.dumps({"query": user_content})
                    }
                }]
            }
        
        return {
            "content": f"I understand you said: {user_content}. How can I help you further?",
            "tool_calls": []
        }
    
    async def _execute_tool_call(self, tool_call: Dict[str, Any]) -> ToolResult:
        """Execute a single tool call"""
        function_name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"])
        
        logger.info(f"Executing tool: {function_name} with args: {arguments}")
        
        # Find the tool
        tool = None
        for t in self.tools:
            if t.name == function_name:
                tool = t
                break
        
        if not tool:
            logger.error(f"Tool not found: {function_name}")
            return ToolResult(
                name=function_name,
                ok=False,
                data={"error": f"Tool '{function_name}' not found"}
            )
        
        try:
            result = await tool(**arguments)
            logger.info(f"Tool {function_name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool {function_name} execution failed: {e}")
            return ToolResult(
                name=function_name,
                ok=False,
                data={"error": str(e), "raw_exception": str(e)}
            )
    
    async def _create_event_stream(self, events: List[Dict[str, Any]]) -> AsyncIterator[str]:
        """Create async stream iterator for events"""
        for event in events:
            yield json.dumps(event)
        yield json.dumps({"type": "done"})


async def start_run(run_id: uuid.UUID) -> AsyncIterator[str]:
    """Start a run and yield events"""
    logger.info(f"Starting run {run_id}")
    
    # Update run status to running
    _update_run_status(run_id, "running")
    
    try:
        # Get run details
        db = next(get_db())
        try:
            run = db.query(Run).filter(Run.id == run_id).first()
            if not run:
                raise Exception(f"Run {run_id} not found")
            
            thread_id = run.thread_id
            
            # Get the last user message
            last_message = db.query(Message).filter(
                Message.thread_id == thread_id,
                Message.role == "user"
            ).order_by(Message.created_at.desc()).first()
            
            if not last_message:
                raise Exception(f"No user message found for thread {thread_id}")
            
            user_content = last_message.content
        finally:
            db.close()
        
        # Initialize agent loop
        agent = AgentLoop()
        
        # Run agent
        final_response, event_stream = await agent.run_agent(thread_id, user_content)
        
        # Yield events
        async for event in event_stream:
            yield event
        
        # Update run status to completed
        _update_run_status(run_id, "completed", tokens_used=100)  # Mock token count
        
        yield json.dumps({"type": "run_completed", "final_response": final_response})
        
    except Exception as e:
        logger.error(f"Run {run_id} failed: {e}")
        _update_run_status(run_id, "error", error_message=str(e))
        yield json.dumps({"type": "error", "message": str(e)})


def _update_run_status(run_id: uuid.UUID, status: str, tokens_used: Optional[int] = None, error_message: Optional[str] = None) -> None:
    """Update run status in database"""
    db = next(get_db())
    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        if run:
            run.status = status
            if tokens_used is not None:
                run.tokens_used = tokens_used
            if error_message:
                run.error_message = error_message
            run.updated_at = datetime.utcnow()
            db.commit()
            logger.info(f"Updated run {run_id} status to {status}")
    except Exception as e:
        logger.error(f"Failed to update run status: {e}")
        db.rollback()
    finally:
        db.close()