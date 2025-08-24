"""Web Search Tool using CoexistAI or fallback"""

import os
import json
import logging
import httpx
from typing import Dict, Any, List, Optional

from . import BaseTool, ToolResult
from config import get_settings

logger = logging.getLogger(__name__)

class WebSearchTool(BaseTool):
    """Tool for performing web searches via CoexistAI or fallback"""
    
    def __init__(self):
        self.settings = get_settings()
        super().__init__()
        
    def _get_description(self) -> str:
        """Return tool description"""
        return "Search the web for current information on any topic"
    
    def _get_schema(self) -> Dict[str, Any]:
        """Return OpenAI function/tool schema"""
        return {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": self._get_description(),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    
    async def __call__(self, **kwargs) -> ToolResult:
        """Execute web search"""
        query = kwargs.get("query", "")
        top_k = kwargs.get("top_k", 5)
        
        if not query:
            return ToolResult(
                name=self.name,
                ok=False,
                data={"error": "Query parameter is required"}
            )
        
        # Try CoexistAI if available
        if self.settings.COEXISTAI_BASE_URL:
            try:
                result = await self._search_with_coexistai(query, top_k)
                return ToolResult(
                    name=self.name,
                    ok=True,
                    data=result
                )
            except Exception as e:
                logger.warning(f"CoexistAI search failed: {e}, falling back to stub")
        
        # Fallback to stub
        return self._get_stub_result(query)
    
    async def _search_with_coexistai(self, query: str, top_k: int) -> Dict[str, Any]:
        """Search using CoexistAI web-search endpoint"""
        base_url = self.settings.COEXISTAI_BASE_URL.rstrip('/')
        url = f"{base_url}/web-search"
        
        payload = {
            "query": query,
            "top_k": top_k
        }
        
        headers = {"Content-Type": "application/json"}
        if self.settings.COEXISTAI_API_KEY:
            headers["Authorization"] = f"Bearer {self.settings.COEXISTAI_API_KEY}"
        
        logger.info(f"Calling CoexistAI web search: {url} with query: {query}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            
            data = response.json()
            logger.info(f"CoexistAI search response received for query: {query}")
            
            # Handle different response shapes gracefully
            if "answer" in data:
                return {
                    "query": query,
                    "answer": data["answer"],
                    "source": "coexistai"
                }
            elif "summary" in data:
                return {
                    "query": query,
                    "summary": data["summary"],
                    "source": "coexistai"
                }
            elif "results" in data and isinstance(data["results"], list):
                # Return top 3 items with title/url/snippet
                results = data["results"][:3]
                formatted_results = []
                for result in results:
                    formatted_result = {
                        "title": result.get("title", "No title"),
                        "url": result.get("url", ""),
                        "snippet": result.get("snippet", result.get("content", ""))
                    }
                    formatted_results.append(formatted_result)
                
                return {
                    "query": query,
                    "results": formatted_results,
                    "source": "coexistai"
                }
            else:
                # Return raw JSON under data
                return {
                    "query": query,
                    "data": data,
                    "source": "coexistai"
                }
    
    def _get_stub_result(self, query: str) -> ToolResult:
        """Return stub result when CoexistAI is not available"""
        logger.info(f"Using stub web search result for query: {query}")
        
        return ToolResult(
            name=self.name,
            ok=True,
            data={
                "query": query,
                "results": [
                    {
                        "title": "stub result",
                        "url": "http://example.com",
                        "snippet": "no search available"
                    }
                ],
                "source": "stub"
            }
        )
    
    # Legacy method for backward compatibility
    async def execute(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Legacy execute method for backward compatibility"""
        result = await self.__call__(query=query, top_k=max_results)
        return result.data if result.ok else {"error": "Search failed", "results": []}