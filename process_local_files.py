#!/usr/bin/env python3
"""
Process local files for RAG knowledge base.

Usage:
    python process_local_files.py
    python process_local_files.py --input "C:\\path\\to\\files"
    python process_local_files.py --strategy paragraph --chunk-size 1500
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.local_file_processor import run

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Process local files for RAG chatbot knowledge base',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python process_local_files.py
  python process_local_files.py --input "C:\\Users\\YourName\\Desktop\\mf_docs"
  python process_local_files.py --strategy paragraph --chunk-size 1500
  python process_local_files.py --strategy heading --overlap 300

Chunking Strategies:
  fixed     - Split into fixed-size chunks with overlap (default)
  paragraph - Split by paragraphs, combine small ones
  heading   - Split by headings/sections

Supported File Formats:
  - PDF (.pdf)
  - HTML (.html, .htm, .mhtml)
  - Text (.txt, .md)
  - Word (.docx)
  - Data (.json, .csv)
        """
    )

    parser.add_argument(
        '--input', '-i',
        default=r"C:\Users\Anish Karthik\Desktop\rawd",
        help='Input directory containing files to process'
    )

    parser.add_argument(
        '--output', '-o',
        default='data/rag_chunks.csv',
        help='Output CSV file path'
    )

    parser.add_argument(
        '--strategy', '-s',
        choices=['fixed', 'paragraph', 'heading'],
        default='fixed',
        help='Chunking strategy (default: fixed)'
    )

    parser.add_argument(
        '--chunk-size', '-c',
        type=int,
        default=1000,
        help='Target chunk size in characters (default: 1000)'
    )

    parser.add_argument(
        '--overlap',
        type=int,
        default=200,
        help='Overlap between chunks in characters (default: 200)'
    )

    args = parser.parse_args()

    # Run processor
    chunks = run(
        input_dir=args.input,
        output_file=args.output,
        chunk_strategy=args.strategy,
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap
    )

    if chunks:
        print(f"\nSuccess! {len(chunks)} chunks saved to {args.output}")
        print("\nYour RAG knowledge base is ready!")
    else:
        print("\nNo chunks created. Please check:")
        print(f"  1. Directory exists: {args.input}")
        print("  2. Directory contains supported files (PDF, HTML, TXT, DOCX)")
