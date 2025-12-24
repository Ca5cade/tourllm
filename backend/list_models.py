#!/usr/bin/env python3
"""List all available Gemini models for this API key."""
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("ERROR: GOOGLE_API_KEY not found")
    exit(1)

print(f"API Key (first 10 chars): {api_key[:10]}...")
genai.configure(api_key=api_key)

print("\nListing all available models...")
print("=" * 60)

try:
    with open("models.txt", "w", encoding="utf-8") as f:
        models = genai.list_models()
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                line = f"Model Name: {model.name}\n"
                print(line)
                f.write(line)
except Exception as e:
    print(f"ERROR listing models: {e}")
    print("\nTrying direct model access...")
    
    # Try accessing models differently
    test_names = ['models/gemini-pro', 'models/gemini-1.5-pro', 'models/gemini-1.5-flash']
    for name in test_names:
        try:
            model = genai.GenerativeModel(name)
            print(f"  SUCCESS: {name}")
        except Exception as e2:
            print(f"  FAILED: {name} - {str(e2)[:60]}")
