from googlesearch import search
import time

query = "Tunisian street food blogs"
print(f"Testing Google Search for: {query}")

try:
    results = search(query, num_results=5, advanced=True)
    for i, r in enumerate(results):
        print(f"{i+1}. {r.title} ({r.url})")
        print(f"   {r.description}")
except Exception as e:
    print(f"Google Search failed: {e}")
