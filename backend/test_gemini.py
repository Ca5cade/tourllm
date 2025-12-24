#!/usr/bin/env python3
"""Quick test of gemini-pro model."""
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

print("Testing gemini-pro model...")
try:
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content("In one sentence, what is Tunisia known for?")
    print(f"SUCCESS: {response.text}")
except Exception as e:
    print(f"ERROR: {e}")
