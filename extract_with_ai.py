#!/usr/bin/env python3
"""
Extract structured data from local files using Google Gemini AI.

This script reads your downloaded mutual fund documents and uses AI to:
- Identify content type (FAQ, scheme info, guidelines, concepts)
- Extract structured data into proper fields
- Save to organized CSV files

Usage:
    # Set your API key first
    set GOOGLE_API_KEY=your-api-key-here   (Windows)
    export GOOGLE_API_KEY=your-api-key-here (Linux/Mac)

    # Run the extractor
    python extract_with_ai.py

    # Or pass API key directly
    python extract_with_ai.py --api-key YOUR_API_KEY

    # Specify input directory
    python extract_with_ai.py --input "C:\\path\\to\\files"
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.ai_extractor import run

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Extract structured mutual fund data from local files using Google Gemini AI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_with_ai.py
  python extract_with_ai.py --api-key YOUR_GEMINI_API_KEY
  python extract_with_ai.py --input "C:\\Users\\YourName\\Downloads\\mf_docs"

Output Files:
  data/extracted_faqs.csv       - Question/Answer pairs
  data/extracted_schemes.csv    - Mutual fund scheme details
  data/extracted_guidelines.csv - SEBI regulations and circulars
  data/extracted_basics.csv     - Definitions and concepts

Get your API key:
  1. Go to https://makersuite.google.com/app/apikey
  2. Create a new API key
  3. Set as environment variable or pass with --api-key
        """
    )

    parser.add_argument(
        '--input', '-i',
        default=r"C:\Users\Anish Karthik\Desktop\rawd",
        help='Input directory containing files to process'
    )

    parser.add_argument(
        '--api-key', '-k',
        help='Google Gemini API key (or set GOOGLE_API_KEY environment variable)'
    )

    args = parser.parse_args()

    # Run extractor
    results = run(input_dir=args.input, api_key=args.api_key)

    if results:
        total = sum(len(v) for v in results.values())
        print(f"\nExtraction complete! {total} records extracted.")
        print("\nOutput files are in the 'data/' directory.")
    else:
        print("\nExtraction failed. Check your API key and input directory.")
