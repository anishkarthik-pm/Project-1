"""
AI-Powered Extractor using Google Gemini
Extracts structured data from local files using AI to identify and categorize content.
"""

import os
import json
import csv
import time
from pathlib import Path
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

# Try to import Google Generative AI
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    print("Error: google-generativeai not installed. Install with: pip install google-generativeai")

# Try to import PDF library
try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

# Try to import DOCX library
try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

# Output files
OUTPUT_DIR = "data"
FAQS_OUTPUT = "data/extracted_faqs.csv"
SCHEMES_OUTPUT = "data/extracted_schemes.csv"
GUIDELINES_OUTPUT = "data/extracted_guidelines.csv"
BASICS_OUTPUT = "data/extracted_basics.csv"

# Gemini configuration
# Use "gemini-pro" for wider compatibility, or "gemini-1.5-flash" / "gemini-1.5-pro" if available
MODEL_NAME = "gemini-pro"
MAX_TOKENS = 8000


def configure_gemini(api_key: str):
    """Configure Gemini API with the provided key."""
    if not HAS_GEMINI:
        raise ImportError("google-generativeai package not installed")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(MODEL_NAME)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file."""
    if not HAS_PYPDF2:
        return ""
    text = []
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
        return '\n'.join(text)
    except Exception as e:
        print(f"  Error reading PDF {file_path}: {e}")
        return ""


def extract_text_from_html(file_path: str) -> str:
    """Extract text from HTML file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        soup = BeautifulSoup(content, 'html.parser')
        for script in soup(['script', 'style', 'nav', 'footer']):
            script.decompose()
        return soup.get_text(separator='\n', strip=True)
    except Exception as e:
        print(f"  Error reading HTML {file_path}: {e}")
        return ""


def extract_text_from_txt(file_path: str) -> str:
    """Extract text from TXT file."""
    try:
        for encoding in ['utf-8', 'utf-16', 'latin-1', 'cp1252']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        return ""
    except Exception as e:
        print(f"  Error reading TXT {file_path}: {e}")
        return ""


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX file."""
    if not HAS_DOCX:
        return ""
    try:
        doc = Document(file_path)
        return '\n'.join([para.text for para in doc.paragraphs if para.text.strip()])
    except Exception as e:
        print(f"  Error reading DOCX {file_path}: {e}")
        return ""


def extract_text_from_file(file_path: str) -> str:
    """Extract text from file based on extension."""
    ext = Path(file_path).suffix.lower()
    if ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext in ['.html', '.htm', '.mhtml']:
        return extract_text_from_html(file_path)
    elif ext in ['.txt', '.md', '.csv', '.json']:
        return extract_text_from_txt(file_path)
    elif ext in ['.docx', '.doc']:
        return extract_text_from_docx(file_path)
    else:
        return extract_text_from_txt(file_path)


def get_content_type_prompt() -> str:
    """Prompt to identify content type."""
    return """Analyze this document and identify what type of mutual fund content it contains.

Return a JSON object with:
{
    "content_types": ["faq", "scheme_info", "guideline", "basic_concept"],
    "primary_type": "the main type",
    "description": "brief description of content"
}

Only include content types that are actually present. Content types:
- "faq": Question and answer pairs
- "scheme_info": Mutual fund scheme details (NAV, expense ratio, returns, etc.)
- "guideline": SEBI regulations, circulars, rules
- "basic_concept": Definitions, explanations of MF concepts

Document content:
"""


def get_faq_extraction_prompt() -> str:
    """Prompt to extract FAQs."""
    return """Extract all question-answer pairs from this document about mutual funds.

Return a JSON array where each item has:
{
    "question": "the question text",
    "answer": "the complete answer",
    "category": "category like 'Taxation', 'SIP', 'NAV', 'Risk', 'General', etc."
}

Rules:
- Extract ALL Q&A pairs you can find
- Keep answers complete but concise (max 500 words)
- If content is not in Q&A format but explains a concept, convert it to Q&A format
- Categorize appropriately based on topic

Document content:
"""


def get_scheme_extraction_prompt() -> str:
    """Prompt to extract scheme information."""
    return """Extract mutual fund scheme information from this document.

Return a JSON array where each scheme has:
{
    "scheme_name": "full scheme name",
    "category": "Equity/Debt/Hybrid/Index/ETF",
    "sub_category": "Large Cap/Mid Cap/Small Cap/Liquid/etc.",
    "benchmark": "benchmark index name",
    "fund_manager": "fund manager name(s)",
    "aum": "assets under management",
    "expense_ratio": "expense ratio percentage",
    "nav": "current NAV if available",
    "min_investment": "minimum investment amount",
    "min_sip": "minimum SIP amount",
    "riskometer": "risk level",
    "returns_1y": "1 year returns",
    "returns_3y": "3 year returns",
    "returns_5y": "5 year returns",
    "scheme_objective": "investment objective"
}

Rules:
- Extract all schemes mentioned
- Use "N/A" for fields not found
- Keep values as strings with units (e.g., "Rs 5,000", "1.5%")

Document content:
"""


def get_guideline_extraction_prompt() -> str:
    """Prompt to extract guidelines/regulations."""
    return """Extract SEBI guidelines, regulations, and circulars from this document.

Return a JSON array where each item has:
{
    "type": "Circular/Regulation/Guideline/Notification",
    "reference_number": "circular or regulation number if available",
    "date": "date of issue",
    "title": "title or subject",
    "description": "detailed description of the guideline (max 500 words)",
    "key_points": ["list of key points"],
    "applicable_to": "who this applies to"
}

Rules:
- Extract all regulatory content
- Include important dates and deadlines
- Summarize key requirements clearly

Document content:
"""


def get_basics_extraction_prompt() -> str:
    """Prompt to extract basic concepts."""
    return """Extract mutual fund concepts, definitions, and educational content from this document.

Return a JSON array where each item has:
{
    "topic": "concept name or topic",
    "category": "Definition/Fund Type/Taxation/Risk/Investment Strategy/Regulation",
    "content": "detailed explanation (max 500 words)",
    "key_points": ["list of key takeaways"]
}

Rules:
- Extract all educational/informational content
- Make explanations clear and comprehensive
- Include examples where relevant

Document content:
"""


def call_gemini(model, prompt: str, content: str, max_retries: int = 3) -> Optional[str]:
    """Call Gemini API with retry logic."""
    # Truncate content if too long
    if len(content) > 30000:
        content = content[:30000] + "\n\n[Content truncated...]"

    full_prompt = prompt + content

    for attempt in range(max_retries):
        try:
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            print(f"    Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return None
    return None


def parse_json_response(response: str) -> Optional[any]:
    """Parse JSON from Gemini response."""
    if not response:
        return None

    # Try to extract JSON from response
    try:
        # Remove markdown code blocks if present
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end]
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end]

        return json.loads(response.strip())
    except json.JSONDecodeError as e:
        print(f"    JSON parse error: {e}")
        return None


def process_file_with_ai(model, file_path: str, file_name: str) -> Dict[str, List]:
    """Process a single file with AI extraction."""
    results = {
        'faqs': [],
        'schemes': [],
        'guidelines': [],
        'basics': []
    }

    # Extract text
    text = extract_text_from_file(file_path)
    if not text or len(text) < 100:
        print(f"    Skipping {file_name}: No sufficient text content")
        return results

    print(f"    Extracted {len(text)} characters")

    # First, identify content type
    print(f"    Identifying content type...")
    type_response = call_gemini(model, get_content_type_prompt(), text[:10000])
    content_info = parse_json_response(type_response)

    if not content_info:
        # Default to extracting all types
        content_types = ['faq', 'basic_concept']
    else:
        content_types = content_info.get('content_types', ['faq', 'basic_concept'])
        print(f"    Detected types: {content_types}")

    # Extract based on content type
    if 'faq' in content_types:
        print(f"    Extracting FAQs...")
        faq_response = call_gemini(model, get_faq_extraction_prompt(), text)
        faqs = parse_json_response(faq_response)
        if faqs and isinstance(faqs, list):
            for faq in faqs:
                faq['source_file'] = file_name
            results['faqs'] = faqs
            print(f"    Found {len(faqs)} FAQs")

    if 'scheme_info' in content_types:
        print(f"    Extracting scheme information...")
        scheme_response = call_gemini(model, get_scheme_extraction_prompt(), text)
        schemes = parse_json_response(scheme_response)
        if schemes and isinstance(schemes, list):
            for scheme in schemes:
                scheme['source_file'] = file_name
            results['schemes'] = schemes
            print(f"    Found {len(schemes)} schemes")

    if 'guideline' in content_types:
        print(f"    Extracting guidelines...")
        guideline_response = call_gemini(model, get_guideline_extraction_prompt(), text)
        guidelines = parse_json_response(guideline_response)
        if guidelines and isinstance(guidelines, list):
            for guideline in guidelines:
                guideline['source_file'] = file_name
            results['guidelines'] = guidelines
            print(f"    Found {len(guidelines)} guidelines")

    if 'basic_concept' in content_types:
        print(f"    Extracting basic concepts...")
        basics_response = call_gemini(model, get_basics_extraction_prompt(), text)
        basics = parse_json_response(basics_response)
        if basics and isinstance(basics, list):
            for basic in basics:
                basic['source_file'] = file_name
            results['basics'] = basics
            print(f"    Found {len(basics)} concepts")

    return results


def save_faqs_to_csv(faqs: List[Dict], filename: str):
    """Save FAQs to CSV."""
    if not faqs:
        return

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    fieldnames = ['question', 'answer', 'category', 'source_file']

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(faqs)

    print(f"  Saved {len(faqs)} FAQs to {filename}")


def save_schemes_to_csv(schemes: List[Dict], filename: str):
    """Save schemes to CSV."""
    if not schemes:
        return

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    fieldnames = ['scheme_name', 'category', 'sub_category', 'benchmark', 'fund_manager',
                  'aum', 'expense_ratio', 'nav', 'min_investment', 'min_sip', 'riskometer',
                  'returns_1y', 'returns_3y', 'returns_5y', 'scheme_objective', 'source_file']

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(schemes)

    print(f"  Saved {len(schemes)} schemes to {filename}")


def save_guidelines_to_csv(guidelines: List[Dict], filename: str):
    """Save guidelines to CSV."""
    if not guidelines:
        return

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    fieldnames = ['type', 'reference_number', 'date', 'title', 'description',
                  'key_points', 'applicable_to', 'source_file']

    # Convert list fields to strings
    for g in guidelines:
        if isinstance(g.get('key_points'), list):
            g['key_points'] = '; '.join(g['key_points'])

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(guidelines)

    print(f"  Saved {len(guidelines)} guidelines to {filename}")


def save_basics_to_csv(basics: List[Dict], filename: str):
    """Save basic concepts to CSV."""
    if not basics:
        return

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    fieldnames = ['topic', 'category', 'content', 'key_points', 'source_file']

    # Convert list fields to strings
    for b in basics:
        if isinstance(b.get('key_points'), list):
            b['key_points'] = '; '.join(b['key_points'])

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(basics)

    print(f"  Saved {len(basics)} concepts to {filename}")


def run(input_dir: str = None, api_key: str = None):
    """
    Main function to process local files with AI extraction.

    Args:
        input_dir: Directory containing files to process
        api_key: Google Gemini API key
    """
    print("\n" + "="*60)
    print("AI-POWERED EXTRACTOR (Google Gemini)")
    print("="*60)

    # Default input directory
    if not input_dir:
        input_dir = r"C:\Users\Anish Karthik\Desktop\rawd"

    # Get API key
    if not api_key:
        api_key = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')

    if not api_key:
        print("\nError: No API key provided!")
        print("Set GOOGLE_API_KEY environment variable or pass api_key parameter")
        print("\nExample:")
        print('  set GOOGLE_API_KEY=your-api-key-here')
        print('  python extract_with_ai.py')
        return

    # Configure Gemini
    print(f"\nConfiguring Gemini ({MODEL_NAME})...")
    try:
        model = configure_gemini(api_key)
    except Exception as e:
        print(f"Error configuring Gemini: {e}")
        return

    # Find files
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"Error: Directory not found: {input_dir}")
        return

    supported_extensions = {'.pdf', '.html', '.htm', '.mhtml', '.txt', '.md', '.docx', '.doc'}
    files = []
    for ext in supported_extensions:
        files.extend(input_path.glob(f'*{ext}'))
        files.extend(input_path.glob(f'**/*{ext}'))
    files = sorted(set(files))

    print(f"\nFound {len(files)} files to process")
    print(f"Input directory: {input_dir}")

    # Process each file
    all_faqs = []
    all_schemes = []
    all_guidelines = []
    all_basics = []

    for i, file_path in enumerate(files, 1):
        file_name = file_path.name
        print(f"\n[{i}/{len(files)}] Processing: {file_name}")

        try:
            results = process_file_with_ai(model, str(file_path), file_name)

            all_faqs.extend(results['faqs'])
            all_schemes.extend(results['schemes'])
            all_guidelines.extend(results['guidelines'])
            all_basics.extend(results['basics'])

            # Rate limiting - be nice to the API
            time.sleep(1)

        except Exception as e:
            print(f"    Error processing {file_name}: {e}")
            continue

    # Save results
    print("\n" + "="*60)
    print("SAVING RESULTS")
    print("="*60)

    save_faqs_to_csv(all_faqs, FAQS_OUTPUT)
    save_schemes_to_csv(all_schemes, SCHEMES_OUTPUT)
    save_guidelines_to_csv(all_guidelines, GUIDELINES_OUTPUT)
    save_basics_to_csv(all_basics, BASICS_OUTPUT)

    # Summary
    print("\n" + "="*60)
    print("EXTRACTION SUMMARY")
    print("="*60)
    print(f"  Files processed: {len(files)}")
    print(f"  FAQs extracted: {len(all_faqs)}")
    print(f"  Schemes extracted: {len(all_schemes)}")
    print(f"  Guidelines extracted: {len(all_guidelines)}")
    print(f"  Concepts extracted: {len(all_basics)}")
    print("-"*60)
    print(f"  Total records: {len(all_faqs) + len(all_schemes) + len(all_guidelines) + len(all_basics)}")
    print("="*60)

    return {
        'faqs': all_faqs,
        'schemes': all_schemes,
        'guidelines': all_guidelines,
        'basics': all_basics
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Extract structured data from files using AI')
    parser.add_argument('--input', '-i',
                        default=r"C:\Users\Anish Karthik\Desktop\rawd",
                        help='Input directory containing files')
    parser.add_argument('--api-key', '-k',
                        help='Google Gemini API key (or set GOOGLE_API_KEY env var)')

    args = parser.parse_args()

    run(input_dir=args.input, api_key=args.api_key)
