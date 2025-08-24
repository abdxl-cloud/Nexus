"""Agent Tools Package"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Union
from pydantic import BaseModel

from .web_search import WebSearchTool
from .browser import BrowserTool

logger = logging.getLogger(__name__)

# Pydantic Models
class ToolCall(BaseModel):
    """Represents a tool call with name and arguments"""
    name: str
    args: Dict[str, Any]

class ToolResult(BaseModel):
    """Represents the result of a tool execution"""
    name: str
    ok: bool
    data: Union[Dict[str, Any], str]

# Base Tool Class
class BaseTool(ABC):
    """Base class for all tools"""
    
    def __init__(self):
        self.name: str = self.__class__.__name__.lower().replace('tool', '')
        self.description: str = self._get_description()
        self.schema: Dict[str, Any] = self._get_schema()
    
    @abstractmethod
    def _get_description(self) -> str:
        """Return tool description"""
        pass
    
    @abstractmethod
    def _get_schema(self) -> Dict[str, Any]:
        """Return OpenAI function/tool schema"""
        pass
    
    @abstractmethod
    async def __call__(self, **kwargs) -> ToolResult:
        """Execute the tool with given arguments"""
        pass
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Get tool information for registration"""
        return {
            "name": self.name,
            "description": self.description,
            "schema": self.schema
        }

def get_default_tools() -> List[BaseTool]:
    """Get list of default tools"""
    return [
        WebSearchTool(),
        BrowserTool()
    ]

__all__ = [
    "ToolCall",
    "ToolResult", 
    "BaseTool",
    "WebSearchTool", 
    "BrowserTool",
    "get_default_tools"
]