"""Web search and browsing tools for AutoHost.

This module provides web search and content fetching capabilities
without requiring browser automation.
"""

from typing import Any

import requests  # type: ignore[import-untyped]
import structlog
from bs4 import BeautifulSoup
from ddgs import DDGS

logger = structlog.get_logger(__name__)

# Request timeout in seconds
REQUEST_TIMEOUT = 15

# User agent to avoid blocks
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """
    Search the web using DuckDuckGo.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default 5)

    Returns:
        Dict with 'results' list or 'error' string
    """
    try:
        logger.debug(f"Web search: {query}")

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return {"results": [], "message": "No results found"}

        # Format results
        formatted = []
        for r in results:
            formatted.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", r.get("link", "")),
                    "snippet": r.get("body", r.get("snippet", "")),
                }
            )

        return {"results": formatted}

    except Exception as e:
        logger.error(f"Web search error: {e}")
        return {"error": f"Search failed: {str(e)}"}


def fetch_webpage(url: str, extract_text: bool = True) -> dict[str, Any]:
    """
    Fetch content from a webpage.

    Args:
        url: The URL to fetch
        extract_text: If True, extract readable text. If False, return raw HTML.

    Returns:
        Dict with 'content', 'title', 'url' or 'error'
    """
    try:
        logger.debug(f"Fetching webpage: {url}")

        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Get title
        title = soup.title.string if soup.title else ""

        if extract_text:
            # Remove script and style elements
            for element in soup(
                ["script", "style", "nav", "footer", "header", "aside"]
            ):
                element.decompose()

            # Get text content
            text = soup.get_text(separator="\n", strip=True)

            # Clean up excessive whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            content = "\n".join(lines)

            # Truncate if too long (keep first 8000 chars for context window)
            if len(content) > 8000:
                content = content[:8000] + "\n\n[Content truncated...]"
        else:
            content = response.text

        return {
            "title": title,
            "url": url,
            "content": content,
        }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out for {url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch {url}: {str(e)}"}
    except Exception as e:
        logger.error(f"Webpage fetch error: {e}")
        return {"error": f"Error processing {url}: {str(e)}"}


def search_and_summarize(query: str, max_results: int = 3) -> dict[str, Any]:
    """
    Search the web and fetch content from top results.

    Args:
        query: Search query
        max_results: Number of pages to fetch (default 3)

    Returns:
        Dict with search results and their content
    """
    # First search
    search_result = web_search(query, max_results=max_results)

    if "error" in search_result:
        return search_result

    results = search_result.get("results", [])
    if not results:
        return {"results": [], "message": "No results found"}

    # Fetch content from each result
    enriched = []
    for r in results:
        url = r.get("url", "")
        if url:
            page = fetch_webpage(url)
            enriched.append(
                {
                    "title": r.get("title", ""),
                    "url": url,
                    "snippet": r.get("snippet", ""),
                    "content": page.get(
                        "content", page.get("error", "Could not fetch")
                    ),
                }
            )

    return {"results": enriched}


def crawl_internal(start_url: str, max_pages: int = 3) -> dict[str, Any]:
    """
    Crawl a URL and follow internal links up to max_pages.
    Great for scraping internal network docs or localhost.

    Args:
        start_url: Origin URL to start scraping.
        max_pages: Maximum number of internal pages to read.

    Returns:
        Dict with concatenated content and number of pages crawled.
    """
    from urllib.parse import urljoin, urlparse

    try:
        visited = set()
        to_visit = [start_url]
        content_parts = []
        domain = urlparse(start_url).netloc

        while to_visit and len(visited) < max_pages:
            url = to_visit.pop(0)
            if url in visited:
                continue
            visited.add(url)

            try:
                headers = {"User-Agent": USER_AGENT}
                response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
                if response.status_code != 200:
                    continue

                soup = BeautifulSoup(response.text, "lxml")

                for element in soup(
                    ["script", "style", "nav", "footer", "header", "aside"]
                ):
                    element.decompose()

                text = soup.get_text(separator="\n", strip=True)
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                page_text = (
                    f"--- START {url} ---\n" + "\n".join(lines) + f"\n--- END {url} ---"
                )
                content_parts.append(page_text)

                for a in soup.find_all("a", href=True):
                    href_val = a["href"]
                    next_url = urljoin(
                        url,
                        str(href_val[0] if isinstance(href_val, list) else href_val),
                    )
                    if (
                        urlparse(next_url).netloc == domain
                        and next_url not in visited
                        and next_url not in to_visit
                    ) and not any(
                        next_url.endswith(ext)
                        for ext in [".png", ".jpg", ".pdf", ".zip"]
                    ):
                        to_visit.append(next_url)
            except Exception:
                continue

        content = "\n\n".join(content_parts)
        if len(content) > 15000:
            content = content[:15000] + "\n\n[Content truncated...]"

        return {"content": content, "pages_crawled": len(visited)}
    except Exception as e:
        logger.error(f"Internal crawl error: {e}")
        return {"error": f"Crawl failed: {str(e)}"}
