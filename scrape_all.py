#!/usr/bin/env python3
"""
Main script to run all mutual fund scrapers.
Scrapes data from various sources and saves to CSV files.

Usage:
    python scrape_all.py
    python scrape_all.py --only basics sebi
    python scrape_all.py --help
"""

import argparse
import sys
import os
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import scrapers
from scrapers import mutual_fund_basics
from scrapers import sebi_scraper
from scrapers import nippon_scraper
from scrapers import faqs_scraper
from scrapers import comprehensive_fund_scraper


def print_banner():
    """Print welcome banner."""
    print("\n" + "="*60)
    print("  MUTUAL FUND DATA SCRAPER")
    print("  Building Knowledge Base for Chatbot")
    print("="*60)
    print(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)


def print_summary(results: dict):
    """Print summary of scraping results."""
    print("\n" + "="*60)
    print("  SCRAPING SUMMARY")
    print("="*60)

    total_records = 0
    for scraper, data in results.items():
        count = len(data) if data else 0
        total_records += count
        status = "✓" if count > 0 else "✗"
        print(f"  {status} {scraper}: {count} records")

    print("-"*60)
    print(f"  Total records scraped: {total_records}")
    print("="*60)

    # Print output files
    print("\n  Output files:")
    output_files = [
        "data/mutual_fund_basics.csv",
        "data/sebi_guidelines.csv",
        "data/nippon_schemes.csv",
        "data/faqs.csv",
        "data/comprehensive_schemes.csv"
    ]
    for f in output_files:
        if os.path.exists(f):
            size = os.path.getsize(f)
            print(f"    ✓ {f} ({size:,} bytes)")
        else:
            print(f"    ✗ {f} (not created)")

    print("\n" + "="*60)


def run_all_scrapers(scrapers_to_run=None):
    """
    Run all or selected scrapers.

    Args:
        scrapers_to_run: List of scraper names to run, or None for all
    """
    results = {}

    # Define available scrapers
    scrapers = {
        'basics': ('Mutual Fund Basics', mutual_fund_basics.run),
        'sebi': ('SEBI Guidelines', sebi_scraper.run),
        'nippon': ('Nippon India MF', nippon_scraper.run),
        'faqs': ('FAQs', faqs_scraper.run),
        'comprehensive': ('Comprehensive Fund Data', comprehensive_fund_scraper.main),
    }

    # Filter scrapers if specific ones requested
    if scrapers_to_run:
        scrapers = {k: v for k, v in scrapers.items() if k in scrapers_to_run}
        if not scrapers:
            print(f"Error: No valid scrapers found. Available: {list(scrapers.keys())}")
            return results

    # Run each scraper
    for key, (name, scraper_func) in scrapers.items():
        try:
            print(f"\n{'='*60}")
            print(f"Running: {name}")
            print(f"{'='*60}")

            start_time = time.time()
            data = scraper_func()
            elapsed = time.time() - start_time

            results[name] = data
            print(f"\nCompleted in {elapsed:.2f} seconds")

        except Exception as e:
            print(f"\nError running {name}: {e}")
            results[name] = []

        # Small delay between scrapers to be polite
        time.sleep(1)

    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Scrape mutual fund data from various sources',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scrape_all.py                    # Run all scrapers
  python scrape_all.py --only basics      # Run only basics scraper
  python scrape_all.py --only sebi faqs   # Run SEBI and FAQs scrapers

Available scrapers:
  basics         - Mutual fund definitions and concepts
  sebi           - SEBI guidelines and regulations
  nippon         - Nippon India mutual fund schemes
  faqs           - Frequently asked questions
  comprehensive  - Comprehensive fund data with fund managers, sectors, holdings, returns, exit load
        """
    )

    parser.add_argument(
        '--only',
        nargs='+',
        choices=['basics', 'sebi', 'nippon', 'faqs', 'comprehensive'],
        help='Run only specified scrapers'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Print banner
    print_banner()

    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)

    # Run scrapers
    start_time = time.time()
    results = run_all_scrapers(args.only)
    total_time = time.time() - start_time

    # Print summary
    print_summary(results)

    print(f"\n  Total time: {total_time:.2f} seconds")
    print(f"  Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "="*60)
    print("  Data is ready for chatbot knowledge base!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
