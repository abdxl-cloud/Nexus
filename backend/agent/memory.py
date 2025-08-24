from typing import List, Dict, Any, Optional
from datetime import datetime
import json

class Memory:
    """Simple in-memory storage for agent conversations and context"""
    
    def __init__(self, max_messages: int = 100):
        self.messages: List[Dict[str, Any]] = []
        self.max_messages = max_messages
        self.session_id: Optional[str] = None
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a message to memory"""
        message = {
            "role": role,  # user, assistant, tool, system
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.messages.append(message)
        
        # Trim messages if we exceed max_messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def get_recent_messages(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent messages"""
        return self.messages[-count:] if self.messages else []
    
    def get_messages_by_role(self, role: str) -> List[Dict[str, Any]]:
        """Get all messages from a specific role"""
        return [msg for msg in self.messages if msg["role"] == role]
    
    def get_conversation_context(self) -> str:
        """Get a formatted string of the conversation context"""
        if not self.messages:
            return "No conversation history"
        
        context_lines = []
        for msg in self.messages[-10:]:  # Last 10 messages
            role = msg["role"].upper()
            content = msg["content"][:200]  # Truncate long messages
            context_lines.append(f"{role}: {content}")
        
        return "\n".join(context_lines)
    
    def clear(self) -> None:
        """Clear all messages from memory"""
        self.messages.clear()
    
    def set_session_id(self, session_id: str) -> None:
        """Set the session ID for this memory instance"""
        self.session_id = session_id
    
    def get_session_id(self) -> Optional[str]:
        """Get the current session ID"""
        return self.session_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary for serialization"""
        return {
            "messages": self.messages,
            "session_id": self.session_id,
            "max_messages": self.max_messages
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        """Create Memory instance from dictionary"""
        memory = cls(max_messages=data.get("max_messages", 100))
        memory.messages = data.get("messages", [])
        memory.session_id = data.get("session_id")
        return memory
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the current memory state"""
        role_counts = {}
        for msg in self.messages:
            role = msg["role"]
            role_counts[role] = role_counts.get(role, 0) + 1
        
        return {
            "total_messages": len(self.messages),
            "role_distribution": role_counts,
            "session_id": self.session_id,
            "oldest_message": self.messages[0]["timestamp"] if self.messages else None,
            "newest_message": self.messages[-1]["timestamp"] if self.messages else None
        }