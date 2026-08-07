
"""
web_scraper — Gives Jarvis the ability to read and extract content from web pages.
Two tools:
  - scrape_webpage: Fast, lightweight scraping for static HTML pages (httpx + BeautifulSoup).
  - scrape_dynamic_page: Full browser rendering for JavaScript-heavy pages (Playwright).
""" 

import httpx 
from bs4 import BeautifulSoup 
from langchain_core.tools import tool 
from agent.tools.safety import logger  
# helpers ------------------------------------------------------------

# a realistic browser user-agent so servers do not block us 
HEADERS = {
    'user-agent': (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
} 

# tags that contain noise, not content 
NOISE_TAGS = [
    "script", "style", "nav", "header", "footer",
    "aside", "form", "button", "iframe", "noscript",
] 

def clean_html(html: str, max_chars: int = 8000) -> str: 
    """
    Parse raw HTML and extract readable text content.
    Removes navigation, scripts, styles, and other noise.
    Truncates to max_chars to avoid overwhelming the LLM context.
    """

    soup = BeautifulSoup(html, 'html.parser') 

    # remove all noise tags 
    for tag in soup.find_all(NOISE_TAGS): 
        tag.decompose() 

    # try to find the main content area first 
    main = (
        soup.find('main')
        or soup.find('article')
        or soup.find("div", {"role": "main"})
        or soup.find("div", {"id": "content"})
        or soup.find("div", {"class": "content"})
        or soup.body
        or soup
    )

    # extract text with newlines between block elements 
    text = main.get_text(separator="\n", strip=True)

    # collapse multiple blank lines into one 
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    clean_text = '\n'.join(lines) 
    
    # truncate if too long 
    if len(clean_text) > max_chars: 
        clean_text = clean_text[:max_chars] + '\n\n[... content truncated ...]'

    return clean_text
# tool1 :  static page scrapper --------------------------------------------

@tool
def scrape_webpage(url: str, max_chars: int = 8000) -> str:
    """
    Fetch and extract readable text content from a web page URL.
    Best for static pages like news articles, Wikipedia, blogs, and documentation.
    Does NOT work for JavaScript-heavy sites (use scrape_dynamic_page for those).
    Args:
        url: The full URL to scrape (must start with http:// or https://).
        max_chars: Maximum characters to return (default 8000).
    """
    logger.log("scrape_webpage", {"url": url}, "Scraping started")
    try:
        response = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        return f"HTTP error {e.response.status_code} when fetching {url}"
    except httpx.RequestError as e:
        return f"Connection error: {e}"
    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "application" not in content_type:
        return f"URL returned non-HTML content: {content_type}"
    text = clean_html(response.text, max_chars=max_chars)
    if not text.strip():
        return "Page fetched but no readable text content was found. It may be a JavaScript-rendered site — try scrape_dynamic_page instead."
    return f"Content from {url}:\n\n{text}"


# tool2 :  dynamic page scrapper (playwright) ----------------------------------- 

@tool
def scrape_dynamic_page(url: str, wait_seconds: int = 3, max_chars: int = 8000) -> str:
    """
    Render a JavaScript-heavy web page using a real browser and extract its text content.
    Use this when scrape_webpage returns empty or incomplete results.
    This is slower but handles dynamic content (React, Angular, SPAs, etc.).
    Args:
        url: The full URL to scrape.
        wait_seconds: Seconds to wait for JavaScript to finish rendering (default 3).
        max_chars: Maximum characters to return (default 8000).
    """
    logger.log("scrape_dynamic_page", {"url": url, "wait_seconds": wait_seconds}, "Scraping started")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=HEADERS["user-agent"])
            page.goto(url, timeout=20000)
            page.wait_for_timeout(wait_seconds * 1000)
            html = page.content()
            browser.close()
        text = clean_html(html, max_chars=max_chars)
        if not text.strip():
            return "Page rendered but no readable text content was found."
        return f"Content from {url}:\n\n{text}"
    except Exception as e:
        return f"Browser rendering failed: {e}"