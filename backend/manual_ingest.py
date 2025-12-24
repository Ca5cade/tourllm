import asyncio
import sys
import os
import argparse

# Add the current directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.scraper import scrape_url, search_web
from app.rag import RAGEngine

async def process_source(source_input, limit, rag):
    """Decide if source is URL or topic, then scrape and ingest."""
    urls_to_scrape = []
    
    # Check if input looks like a URL
    if source_input.startswith("http://") or source_input.startswith("https://"):
        print(f"🔗 Detected URL: {source_input}")
        urls_to_scrape.append(source_input)
    else:
        # It's a topic/query
        print(f"🔍 Detected Topic: '{source_input}' - Searching web...")
        results = search_web(source_input, max_results=limit)
        if results:
            print(f"   Found {len(results)} results:")
            for r in results:
                print(f"    - {r['title']} ({r['href']})")
                urls_to_scrape.append(r['href'])
        else:
            print(f"   No results found for '{source_input}'")

    # Now scrape all identified URLs
    for url in urls_to_scrape:
        print(f"\n   ⬇️ Scraping: {url}...")
        try:
            text = await scrape_url(url)
            if len(text) > 200: # Simple check to ensure we got meaningful content
                print(f"      ✅ Scraped {len(text)} chars.")
                rag.ingest(text, source=url)
                print(f"      💾 Ingested into Database.")
            else:
                print(f"      ⚠️ Content too short or empty ({len(text)} chars). Skipped.")
        except Exception as e:
            print(f"      ❌ Error: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Manually ingest URLs or search topics into the Tourism Knowledge Base.")
    parser.add_argument("inputs", nargs="+", help="URLs or Search Topics to ingest")
    parser.add_argument("--limit", type=int, default=5, help="Number of search results to scrape per topic (default: 5)")
    
    args = parser.parse_args()
    
    print(f"🚀 Initializing RAG Engine & Database...")
    rag = RAGEngine()
    
    print(f"📋 Processing {len(args.inputs)} inputs (Search Limit: {args.limit} results/topic)...")
    print("="*60)
    
    for inp in args.inputs:
        await process_source(inp, args.limit, rag)
        print("="*60)
    
    print("\n✨ All Done! The Chatbot is now smarter.")

if __name__ == "__main__":
    # Fix for Windows asyncio loop issues if needed
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
