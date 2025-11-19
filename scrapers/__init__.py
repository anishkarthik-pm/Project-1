"""
Mutual Fund Scrapers Package
Contains scrapers for various mutual fund data sources.
"""

from .mutual_fund_basics import run as scrape_basics
from .sebi_scraper import run as scrape_sebi
from .nippon_scraper import run as scrape_nippon
from .faqs_scraper import run as scrape_faqs

__all__ = ['scrape_basics', 'scrape_sebi', 'scrape_nippon', 'scrape_faqs']
