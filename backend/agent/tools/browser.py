"""Browser Tool for web page content extraction via Runner or fallback"""

import os
import logging
import httpx
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from . import BaseTool, ToolResult
from backend.config import get_settings

logger = logging.getLogger(__name__)

class BrowserTool(BaseTool):
    """Tool for extracting content from web pages via Runner or fallback"""
    
    def __init__(self):
        self.settings = get_settings()
        super().__init__()
        
    def _get_description(self) -> str:
        """Return tool description"""
        return "Extract and read content from web pages by URL"
    
    def _get_schema(self) -> Dict[str, Any]:
        """Return OpenAI function/tool schema"""
        return {
            "type": "function",
            "function": {
                "name": "browser",
                "description": self._get_description(),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL of the web page to extract content from"
                        }
                    },
                    "required": ["url"]
                }
            }
        }
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    async def __call__(self, **kwargs) -> ToolResult:
        """Extract content from a web page"""
        url = kwargs.get("url", "")
        
        if not url:
            return ToolResult(
                name=self.name,
                ok=False,
                data={"error": "URL parameter is required"}
            )
        
        if not self._is_valid_url(url):
            return ToolResult(
                name=self.name,
                ok=False,
                data={"error": "Invalid URL format"}
            )
        
        # Try Runner if available
        if self.settings.RUNNER_BASE_URL:
            try:
                result = await self._browse_with_runner(url)
                return ToolResult(
                    name=self.name,
                    ok=True,
                    data=result
                )
            except Exception as e:
                logger.warning(f"Runner browse failed: {e}, falling back to stub")
        
        # Fallback to stub
        return self._get_stub_result(url)
    
    async def _browse_with_runner(self, url: str) -> Dict[str, Any]:
        """Browse URL using Runner service"""
        base_url = self.settings.RUNNER_BASE_URL.rstrip('/')
        runner_url = f"{base_url}/browse"
        
        payload = {"url": url}
        headers = {"Content-Type": "application/json"}
        
        logger.info(f"Calling Runner browse: {runner_url} with URL: {url}")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(runner_url, json=payload, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            
            data = response.json()
            logger.info(f"Runner browse response received for URL: {url}")
            
            return {
                "url": url,
                "title": data.get("title", "No title"),
                "text": data.get("text", data.get("content", "")),
                "source": "runner"
            }
    
    def _get_stub_result(self, url: str) -> ToolResult:
        """Return stub result when Runner is not available"""
        logger.info(f"Using stub browser result for URL: {url}")
        
        return ToolResult(
            name=self.name,
            ok=True,
            data={
                "url": url,
                "title": "Example Domain",
                "text": "Example Domain content snapshot (stub)",
                "source": "stub"
            }
        )
    
    # Legacy method for backward compatibility
    async def execute(self, url: str) -> Dict[str, Any]:
        """Legacy execute method for backward compatibility"""
        result = await self.__call__(url=url)
        if result.ok:
            return result.data
        else:
            return {
                "error": result.data.get("error", "Browse failed"),
                "url": url,
                "content": None
            }