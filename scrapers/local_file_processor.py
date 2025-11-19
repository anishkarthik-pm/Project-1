"""
Local File Processor for RAG
Processes local files (PDF, HTML, TXT, DOCX) and chunks them for RAG retrieval.
"""

import os
import re
import csv
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

# Try to import PDF library
try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False
    print("Warning: PyPDF2 not installed. PDF support disabled. Install with: pip install PyPDF2")

# Try to import DOCX library
try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
    print("Warning: python-docx not installed. DOCX support disabled. Install with: pip install python-docx")

# Constants
OUTPUT_FILE = "data/rag_chunks.csv"
DEFAULT_CHUNK_SIZE = 1000  # characters
DEFAULT_CHUNK_OVERLAP = 200  # characters


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file."""
    if not HAS_PYPDF2:
        print(f"  Skipping PDF (PyPDF2 not installed): {file_path}")
        return ""

    text = []
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page_num, page in enumerate(reader.pages):
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

        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()

        # Get text
        text = soup.get_text(separator='\n', strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return '\n'.join(lines)
    except Exception as e:
        print(f"  Error reading HTML {file_path}: {e}")
        return ""


def extract_text_from_txt(file_path: str) -> str:
    """Extract text from TXT file."""
    try:
        # Try different encodings
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
        print(f"  Skipping DOCX (python-docx not installed): {file_path}")
        return ""

    try:
        doc = Document(file_path)
        text = []
        for para in doc.paragraphs:
            if para.text.strip():
                text.append(para.text.strip())
        return '\n'.join(text)
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
        # Try as text file
        return extract_text_from_txt(file_path)


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)

    # Remove excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def chunk_text_fixed_size(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE,
                          overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[str]:
    """Chunk text into fixed-size pieces with overlap."""
    chunks = []

    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    start = 0
    while start < len(text):
        end = start + chunk_size

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence end within last 100 chars
            search_start = max(end - 100, start)
            last_period = text.rfind('. ', search_start, end)
            if last_period > start:
                end = last_period + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start with overlap
        start = end - overlap if end < len(text) else len(text)

    return chunks


def chunk_text_by_paragraph(text: str, max_chunk_size: int = 2000) -> List[str]:
    """Chunk text by paragraphs, combining small paragraphs."""
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) + 2 <= max_chunk_size:
            current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk)

            # If paragraph is too large, split it
            if len(para) > max_chunk_size:
                sub_chunks = chunk_text_fixed_size(para, max_chunk_size, 200)
                chunks.extend(sub_chunks)
                current_chunk = ""
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def chunk_text_by_heading(text: str, max_chunk_size: int = 2000) -> List[str]:
    """Chunk text by headings/sections."""
    # Split by common heading patterns
    sections = re.split(r'\n(?=[A-Z][^a-z]*:|\d+\.\s+[A-Z]|#{1,3}\s+)', text)

    chunks = []
    current_chunk = ""

    for section in sections:
        section = section.strip()
        if not section:
            continue

        if len(current_chunk) + len(section) + 2 <= max_chunk_size:
            current_chunk = f"{current_chunk}\n\n{section}" if current_chunk else section
        else:
            if current_chunk:
                chunks.append(current_chunk)

            if len(section) > max_chunk_size:
                sub_chunks = chunk_text_fixed_size(section, max_chunk_size, 200)
                chunks.extend(sub_chunks)
                current_chunk = ""
            else:
                current_chunk = section

    if current_chunk:
        chunks.append(current_chunk)

    return chunks if chunks else chunk_text_by_paragraph(text, max_chunk_size)


def generate_chunk_id(source: str, chunk_index: int) -> str:
    """Generate unique ID for a chunk."""
    content = f"{source}_{chunk_index}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def process_directory(input_dir: str,
                      chunk_strategy: str = 'fixed',
                      chunk_size: int = DEFAULT_CHUNK_SIZE,
                      chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[Dict]:
    """
    Process all files in a directory and return chunked data.

    Args:
        input_dir: Path to directory containing files
        chunk_strategy: 'fixed', 'paragraph', or 'heading'
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks

    Returns:
        List of chunk dictionaries
    """
    all_chunks = []

    # Supported extensions
    supported_extensions = {'.pdf', '.html', '.htm', '.mhtml', '.txt', '.md',
                           '.docx', '.doc', '.json', '.csv'}

    # Get all files
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"Error: Directory not found: {input_dir}")
        return []

    files = []
    for ext in supported_extensions:
        files.extend(input_path.glob(f'*{ext}'))
        files.extend(input_path.glob(f'**/*{ext}'))  # Recursive

    # Remove duplicates and sort
    files = sorted(set(files))

    print(f"\nFound {len(files)} files to process")

    for file_path in files:
        file_name = file_path.name
        print(f"\nProcessing: {file_name}")

        # Extract text
        text = extract_text_from_file(str(file_path))
        if not text:
            print(f"  No text extracted from {file_name}")
            continue

        # Clean text
        text = clean_text(text)
        print(f"  Extracted {len(text)} characters")

        # Chunk text based on strategy
        if chunk_strategy == 'fixed':
            chunks = chunk_text_fixed_size(text, chunk_size, chunk_overlap)
        elif chunk_strategy == 'paragraph':
            chunks = chunk_text_by_paragraph(text, chunk_size)
        elif chunk_strategy == 'heading':
            chunks = chunk_text_by_heading(text, chunk_size)
        else:
            chunks = chunk_text_fixed_size(text, chunk_size, chunk_overlap)

        print(f"  Created {len(chunks)} chunks")

        # Create chunk records
        for i, chunk in enumerate(chunks):
            chunk_id = generate_chunk_id(file_name, i)

            all_chunks.append({
                'chunk_id': chunk_id,
                'source_file': file_name,
                'chunk_index': i,
                'total_chunks': len(chunks),
                'content': chunk,
                'char_count': len(chunk),
                'source_path': str(file_path)
            })

    return all_chunks


def save_chunks_to_csv(chunks: List[Dict], output_file: str):
    """Save chunks to CSV file."""
    if not chunks:
        print("No chunks to save")
        return

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)

    fieldnames = ['chunk_id', 'source_file', 'chunk_index', 'total_chunks',
                  'content', 'char_count', 'source_path']

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(chunks)

    print(f"\nSaved {len(chunks)} chunks to {output_file}")


def run(input_dir: str = None,
        output_file: str = OUTPUT_FILE,
        chunk_strategy: str = 'fixed',
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP):
    """
    Main function to process local files for RAG.

    Args:
        input_dir: Directory containing files to process
        output_file: Output CSV file path
        chunk_strategy: 'fixed', 'paragraph', or 'heading'
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks
    """
    print("\n" + "="*60)
    print("LOCAL FILE PROCESSOR FOR RAG")
    print("="*60)

    if not input_dir:
        # Default path for Windows
        input_dir = r"C:\Users\Anish Karthik\Desktop\rawd"

    print(f"\nInput directory: {input_dir}")
    print(f"Output file: {output_file}")
    print(f"Chunk strategy: {chunk_strategy}")
    print(f"Chunk size: {chunk_size} chars")
    print(f"Chunk overlap: {chunk_overlap} chars")

    # Process files
    chunks = process_directory(
        input_dir,
        chunk_strategy=chunk_strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    if chunks:
        # Save to CSV
        save_chunks_to_csv(chunks, output_file)

        # Print summary
        print("\n" + "="*60)
        print("PROCESSING SUMMARY")
        print("="*60)

        # Group by source file
        files_processed = {}
        for chunk in chunks:
            source = chunk['source_file']
            if source not in files_processed:
                files_processed[source] = 0
            files_processed[source] += 1

        for source, count in sorted(files_processed.items()):
            print(f"  {source}: {count} chunks")

        print("-"*60)
        print(f"  Total files: {len(files_processed)}")
        print(f"  Total chunks: {len(chunks)}")

        # Calculate avg chunk size
        avg_size = sum(c['char_count'] for c in chunks) / len(chunks)
        print(f"  Avg chunk size: {avg_size:.0f} chars")

        print("="*60)
    else:
        print("\nNo chunks created. Check if the directory contains supported files.")

    return chunks


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Process local files for RAG')
    parser.add_argument('--input', '-i',
                        default=r"C:\Users\Anish Karthik\Desktop\rawd",
                        help='Input directory containing files')
    parser.add_argument('--output', '-o',
                        default='data/rag_chunks.csv',
                        help='Output CSV file')
    parser.add_argument('--strategy', '-s',
                        choices=['fixed', 'paragraph', 'heading'],
                        default='fixed',
                        help='Chunking strategy')
    parser.add_argument('--chunk-size', '-c',
                        type=int, default=1000,
                        help='Chunk size in characters')
    parser.add_argument('--overlap',
                        type=int, default=200,
                        help='Overlap between chunks')

    args = parser.parse_args()

    run(
        input_dir=args.input,
        output_file=args.output,
        chunk_strategy=args.strategy,
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap
    )
