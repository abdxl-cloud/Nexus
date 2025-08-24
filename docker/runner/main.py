from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from playwright.async_api import async_playwright
import logging
import asyncio
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Browser Runner Service", version="1.0.0")

class BrowseRequest(BaseModel):
    url: HttpUrl

class BrowseResponse(BaseModel):
    title: str
    text: str
    url: str
    success: bool
    error: Optional[str] = None

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "browser-runner"}

@app.post("/browse", response_model=BrowseResponse)
async def browse_url(request: BrowseRequest):
    """Browse a URL and extract title and text content"""
    url = str(request.url)
    logger.info(f"Browsing URL: {url}")
    
    try:
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            try:
                # Create new page
                page = await browser.new_page()
                
                # Set user agent
                await page.set_user_agent(
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                )
                
                # Navigate to URL with timeout
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                
                # Wait a bit for dynamic content
                await page.wait_for_timeout(2000)
                
                # Extract title
                title = await page.title()
                if not title:
                    title = "No title found"
                
                # Extract text content
                # Remove script and style elements, then get text
                await page.evaluate("""
                    () => {
                        const scripts = document.querySelectorAll('script, style, nav, header, footer, aside');
                        scripts.forEach(el => el.remove());
                    }
                """)
                
                # Get main content text
                text_content = await page.evaluate("""
                    () => {
                        const main = document.querySelector('main') || 
                                   document.querySelector('article') || 
                                   document.querySelector('.content') || 
                                   document.querySelector('#content') || 
                                   document.body;
                        return main ? main.innerText.trim() : document.body.innerText.trim();
                    }
                """)
                
                # Clean up text
                if text_content:
                    # Remove excessive whitespace and limit length
                    text_content = ' '.join(text_content.split())
                    if len(text_content) > 5000:
                        text_content = text_content[:5000] + "..."
                else:
                    text_content = "No text content found"
                
                logger.info(f"Successfully extracted content from {url}")
                
                return BrowseResponse(
                    title=title,
                    text=text_content,
                    url=url,
                    success=True
                )
                
            finally:
                await browser.close()
                
    except asyncio.TimeoutError:
        logger.error(f"Timeout while browsing {url}")
        return BrowseResponse(
            title="Error",
            text="Request timed out",
            url=url,
            success=False,
            error="Timeout error"
        )
    except Exception as e:
        logger.error(f"Error browsing {url}: {str(e)}")
        return BrowseResponse(
            title="Error",
            text=f"Failed to browse URL: {str(e)}",
            url=url,
            success=False,
            error=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)