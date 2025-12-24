#!/usr/bin/env python3
"""Test which Gemini models are available with the current API key."""
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("ERROR: GOOGLE_API_KEY not found in .env file")
    exit(1)

genai.configure(api_key=api_key)

print("Testing available Gemini models...\n")

# List all available models
print("=== Available Models ===")
try:
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"✅ {model.name}")
except Exception as e:
    print(f"Error listing models: {e}")

print("\n=== Testing Specific Models ===")

# Test specific model names
test_models = [
    'gemini-pro',
    'gemini-1.5-pro',
    'gemini-1.5-flash',
    'gemini-1.5-flash-latest',
    'gemini-1.5-pro-latest',
]

for model_name in test_models:
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say 'test successful' if you can read this.")
        print(f"✅ {model_name}: {response.text[:50]}")
    except Exception as e:
        print(f"❌ {model_name}: {str(e)[:100]}")
