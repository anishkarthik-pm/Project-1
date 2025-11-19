#!/usr/bin/env python3
"""
Check available Gemini models for your API key.
Run this to find the correct model name to use.
"""

import os

try:
    import google.generativeai as genai
except ImportError:
    print("Error: google-generativeai not installed")
    print("Run: pip install google-generativeai")
    exit(1)

# Get API key
api_key = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')

if not api_key:
    print("Error: No API key found!")
    print("Set your API key first:")
    print("  set GOOGLE_API_KEY=your-api-key-here  (Windows CMD)")
    print("  $env:GOOGLE_API_KEY='your-api-key'    (PowerShell)")
    exit(1)

# Configure API
genai.configure(api_key=api_key)

# List models
print("Available Gemini models for your API key:\n")
print("-" * 50)

text_models = []
for m in genai.list_models():
    # supported_generation_methods is a list of strings
    if 'generateContent' in m.supported_generation_methods:
        text_models.append(m.name)
        print(f"  {m.name}")

print("-" * 50)
print(f"\nTotal text generation models: {len(text_models)}")

# Recommend a model
if text_models:
    # Prefer these models in order
    preferred = ['gemini-pro', 'gemini-1.0-pro', 'gemini-1.5-flash', 'gemini-1.5-pro']
    recommended = None
    for pref in preferred:
        for model in text_models:
            if pref in model:
                recommended = model
                break
        if recommended:
            break

    if not recommended:
        recommended = text_models[0]

    print(f"\nRecommended model: {recommended}")
    print(f"\nUpdate scrapers/ai_extractor.py line 45:")
    print(f'  MODEL_NAME = "{recommended.replace("models/", "")}"')
