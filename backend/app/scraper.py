import requests
from bs4 import BeautifulSoup
import urllib.parse
import urllib.parse
import re
import httpx

def search_web(query: str, max_results: int = 5):
    """Searches the web using Yahoo Search (fallback due to DDG/Google blocks)."""
    results = []
    print(f"   🔎 Searching Yahoo for: '{query}'...")
    
    url = "https://search.yahoo.com/search"
    params = {'p': query, 'ei': 'UTF-8', 'nojs': 1}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Yahoo results are usually in 'div.algo'
            # We try multiple selectors to be robust
            search_results = soup.select(".algo")
            
            for res in search_results[:max_results]:
                # Title often in h3 > a
                title_tag = res.select_one("h3 a")
                if not title_tag:
                    title_tag = res.select_one("a") # Fallback
                
                if title_tag:
                    title = title_tag.get_text()
                    href = title_tag.get('href')
                    
                    # Clean up Yahoo redirect URL if possible
                    # Yahoo links often: https://r.search.yahoo.com/_ylt=.../RU=REAL_URL/...
                    if "RU=" in href:
                        try:
                            # Extract RU= parameter
                            start = href.find("RU=") + 3
                            end = href.find("/", start)
                            if end == -1: end = None
                            raw_url = href[start:end]
                            href = urllib.parse.unquote(raw_url)
                        except:
                            pass # Keep original if extraction fails

                    # Description
                    desc_tag = res.select_one(".compText") or res.select_one("p")
                    body = desc_tag.get_text() if desc_tag else ""
                    
                    if href and title:
                        results.append({
                            "title": title,
                            "href": href,
                            "body": body
                        })
    except Exception as e:
        print(f"   ⚠️ Yahoo Search failed: {e}")

    if not results:
        print(f"   ❌ Failed to get results for '{query}'.")

    return results

async def scrape_url(url: str):
    """Fetches and parses text from a URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text
            text = soup.get_text(separator=' ', strip=True)
            
            # Clean up excessive whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text[:10000] # Increased limit
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return ""

def extract_related_topics(text: str) -> list[str]:
    """
    Simple heuristic to extract potential tourism sub-topics from text.
    In a real production app, this would use a cheap LLM call (like Gemini Flash)
    to ask: 'Extract 3 interesting related tourism topics from this text'.
    For now, we use a basic keyword extraction or mock it to save initial API calls 
    until integrated fully.
    """
    # Heuristic: Find capitalized phrases near "visit", "tour", "explore"
    # Or just returning empty for now to let the user fill the queue
    # BUT, let's implement a simple keyword finder for demo purposes.
    
    potential_topics = []
    
    # Very basic dummy implementation for "autonomous" feel without heavy NLP yet.
    # We look for phrases like "visit X", "tour of X".
    import re
    matches = re.findall(r'(?:visit|explore|tour|discover)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', text)
    
    # Filter and clean
    for m in matches:
        topic = m.strip()
        if len(topic) > 3 and topic.lower() not in ["the", "this", "our", "more"]:
            potential_topics.append(f"{topic} Tunisia tourism")
            
    return list(set(potential_topics))[:3]
