"""
SEBI Guidelines Scraper
Scrapes mutual fund regulations and circulars from SEBI website.
"""

import requests
from bs4 import BeautifulSoup
import csv
import os
import time
import re
from typing import List, Dict
from urllib.parse import urljoin

# Constants
OUTPUT_FILE = "data/sebi_guidelines.csv"
BASE_URL = "https://www.sebi.gov.in"
CIRCULARS_URL = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=3&smession=MUTUAL+FUNDS"
MASTER_CIRCULAR_URL = "https://www.sebi.gov.in/legal/master-circulars.html"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}
TIMEOUT = 30
MAX_RETRIES = 3


def make_request(url: str, retries: int = MAX_RETRIES) -> requests.Response:
    """Make HTTP request with retry logic."""
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"  Attempt {attempt + 1}/{retries} failed for {url}: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
    return None


def scrape_sebi_circulars() -> List[Dict]:
    """Scrape mutual fund circulars from SEBI website."""
    data = []

    # Try multiple URL patterns for SEBI circulars
    urls_to_try = [
        "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1",
        "https://www.sebi.gov.in/legal/circulars/mutual-funds.html",
        "https://www.sebi.gov.in/legal/circulars.html",
    ]

    for url in urls_to_try:
        try:
            print(f"  Trying: {url}")
            response = make_request(url)
            if not response:
                continue

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find circular listings
            # SEBI uses various table structures
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:20]:  # Skip header, limit to 20 rows
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        # Extract date and title
                        date_cell = cells[0].get_text(strip=True)
                        title_cell = cells[1] if len(cells) > 1 else cells[0]

                        # Get link if available
                        link = title_cell.find('a')
                        title = link.get_text(strip=True) if link else title_cell.get_text(strip=True)
                        href = link.get('href', '') if link else ''

                        if title and len(title) > 10:
                            # Filter for mutual fund related
                            if any(keyword in title.lower() for keyword in ['mutual fund', 'mf ', 'nav', 'amc', 'aif', 'scheme']):
                                full_url = urljoin(BASE_URL, href) if href else url

                                data.append({
                                    'type': 'Circular',
                                    'date': date_cell[:50],
                                    'title': title[:300],
                                    'description': '',
                                    'source': full_url
                                })

            # Also look for list items
            list_items = soup.find_all('li', class_=lambda x: x and 'list' in str(x).lower())
            for item in list_items[:20]:
                link = item.find('a')
                if link:
                    title = link.get_text(strip=True)
                    href = link.get('href', '')

                    if any(keyword in title.lower() for keyword in ['mutual fund', 'mf ', 'nav']):
                        data.append({
                            'type': 'Guideline',
                            'date': '',
                            'title': title[:300],
                            'description': '',
                            'source': urljoin(BASE_URL, href)
                        })

            if data:
                print(f"  Found {len(data)} items from {url}")
                break

        except Exception as e:
            print(f"  Error with {url}: {e}")
            continue

    return data


def get_sebi_guidelines_static() -> List[Dict]:
    """Return key SEBI mutual fund guidelines (static data for reliability)."""
    guidelines = [
        # Core Regulations
        {
            'type': 'Regulation',
            'date': '1996',
            'title': 'SEBI (Mutual Funds) Regulations, 1996',
            'description': 'The primary regulation governing mutual funds in India. Covers registration of AMCs, scheme approvals, valuation norms, investor protection, disclosures, and compliance requirements. All mutual funds must be registered with SEBI under these regulations.',
            'source': 'https://www.sebi.gov.in/legal/regulations/dec-1996/sebi-mutual-funds-regulations-1996_34619.html'
        },

        # Categorization and Rationalization
        {
            'type': 'Master Circular',
            'date': '2017-10-06',
            'title': 'Categorization and Rationalization of Mutual Fund Schemes',
            'description': 'SEBI circular mandating standardized scheme categories. Defined 36 categories across equity (10), debt (16), hybrid (6), and solution-oriented (4) schemes. Each AMC can have only one scheme per category except index funds and sectoral/thematic funds.',
            'source': 'https://www.sebi.gov.in/legal/circulars/oct-2017/categorization-and-rationalization-of-mutual-fund-schemes_36199.html'
        },

        # Expense Ratio
        {
            'type': 'Circular',
            'date': '2018-09-18',
            'title': 'Total Expense Ratio (TER) Limits',
            'description': 'SEBI mandated TER slabs based on AUM: Up to Rs 500 crore - 2.25% (equity), 2% (other); Rs 500-750 crore - 2%, 1.75%; Rs 750-2000 crore - 1.75%, 1.5%; Rs 2000-5000 crore - 1.6%, 1.35%; Rs 5000-10000 crore - 1.5%, 1.25%; Rs 10000-50000 crore - TER reduced by 0.05% for every Rs 5000 crore increase; Above Rs 50000 crore - 1.05%, 0.80%.',
            'source': 'https://www.sebi.gov.in/legal/circulars/sep-2018/circular-on-total-expense-ratio-ter-_40403.html'
        },

        # Risk-o-meter
        {
            'type': 'Circular',
            'date': '2020-10-05',
            'title': 'Product Labeling in Mutual Funds - Risk-o-meter',
            'description': 'Six-level risk classification mandatory for all schemes: Low, Low to Moderate, Moderate, Moderately High, High, Very High. Risk level must be evaluated monthly and disclosed on websites. Changes in risk level must be communicated to investors.',
            'source': 'https://www.sebi.gov.in/legal/circulars/oct-2020/circular-on-product-labeling-in-mutual-funds-risk-o-meter_47798.html'
        },

        # NAV Applicability
        {
            'type': 'Circular',
            'date': '2020-09-17',
            'title': 'Applicability of NAV - Realization of Funds',
            'description': 'For purchase: NAV of the day on which funds are available for utilization. Cut-off time is 3 PM for equity/debt schemes and 1:30 PM for liquid/overnight funds. Amount should reach AMC before cut-off for same day NAV.',
            'source': 'https://www.sebi.gov.in/legal/circulars/sep-2020/circular-on-applicability-of-nav_47574.html'
        },

        # Valuation Norms
        {
            'type': 'Guideline',
            'date': '2023',
            'title': 'Valuation of Securities',
            'description': 'Detailed norms for valuing debt and money market instruments. Includes mark-to-market valuation, waterfall approach for illiquid securities, side-pocketing for segregated portfolios, and treatment of interest rate changes. All valuations must be done daily.',
            'source': 'https://www.sebi.gov.in/legal/circulars/mar-2019/valuation-of-money-market-and-debt-securities_42534.html'
        },

        # Disclosure Requirements
        {
            'type': 'Guideline',
            'date': '2023',
            'title': 'Scheme Information Document (SID) Disclosure',
            'description': 'Mandatory disclosures include: investment objective, asset allocation, risk factors, benchmark, fund manager details, load structure, minimum investment, NAV disclosure frequency, tax implications, and investor rights. SID must be updated annually.',
            'source': 'https://www.sebi.gov.in'
        },
        {
            'type': 'Guideline',
            'date': '2023',
            'title': 'Monthly Portfolio Disclosure',
            'description': 'AMCs must disclose complete portfolio of all schemes on monthly basis within 10 days of month end. Disclosure includes security name, ISIN, quantity, market value, and percentage of AUM. Daily disclosure of portfolio required for ETFs.',
            'source': 'https://www.sebi.gov.in'
        },

        # KYC Requirements
        {
            'type': 'Circular',
            'date': '2023',
            'title': 'KYC Requirements for Mutual Fund Investors',
            'description': 'All investors must complete KYC through KRA (KYC Registration Agency). Documents required: PAN card (mandatory for investments above Rs 50,000), proof of address, photograph. Aadhaar-based e-KYC allowed. In-person verification required for investments above Rs 2 lakh.',
            'source': 'https://www.sebi.gov.in'
        },

        # Investment Restrictions
        {
            'type': 'Regulation',
            'date': '2023',
            'title': 'Investment Restrictions for Mutual Funds',
            'description': 'Key restrictions: No scheme can invest more than 10% in single company; total investment in single company across schemes cannot exceed 10% of company NAV; sector exposure limits for sectoral funds; group company exposure limits; derivative exposure limits for hedge/protection.',
            'source': 'https://www.sebi.gov.in'
        },

        # Exit Load
        {
            'type': 'Circular',
            'date': '2023',
            'title': 'Exit Load Structure',
            'description': 'Exit load is charged for early redemptions to discourage short-term trading. Maximum exit load is 2% of NAV. Typical structures: Equity funds - 1% if redeemed within 1 year; Liquid funds - graded exit load for redemptions within 7 days; ELSS - no exit load but 3-year lock-in.',
            'source': 'https://www.sebi.gov.in'
        },

        # Investor Protection
        {
            'type': 'Guideline',
            'date': '2023',
            'title': 'Investor Grievance Redressal',
            'description': 'AMCs must have dedicated investor grievance cell. Complaints can be lodged through SCORES portal. Response time: 30 days for AMC, escalation to SEBI if unresolved. Investor Protection Fund maintained by AMCs.',
            'source': 'https://scores.gov.in'
        },

        # Side Pocketing
        {
            'type': 'Circular',
            'date': '2018-12-28',
            'title': 'Side Pocketing for Segregated Portfolios',
            'description': 'AMCs can create segregated portfolios to separate distressed assets from main portfolio. Triggered by credit events like downgrade to below investment grade. Existing investors get units in segregated portfolio; new investors excluded from segregated assets.',
            'source': 'https://www.sebi.gov.in/legal/circulars/dec-2018/creation-of-segregated-portfolio-in-mutual-fund-schemes_41565.html'
        },

        # Nomination
        {
            'type': 'Circular',
            'date': '2023',
            'title': 'Mandatory Nomination for Individual Investors',
            'description': 'All individual mutual fund investors must provide nomination or opt-out declaration. Nomination can be registered online through AMC website. Multiple nominees allowed with percentage allocation. Nomination facilitates easy transmission of units.',
            'source': 'https://www.sebi.gov.in'
        },

        # Direct Plans
        {
            'type': 'Circular',
            'date': '2012-09-13',
            'title': 'Direct Plans for Mutual Fund Schemes',
            'description': 'All mutual fund schemes must offer Direct Plan option with lower expense ratio (no distributor commission). Direct plans have separate NAV and portfolio is common with regular plan. Investors can switch from regular to direct plan.',
            'source': 'https://www.sebi.gov.in/legal/circulars/sep-2012/direct-plan-for-mutual-fund-schemes_24266.html'
        },

        # Benchmark
        {
            'type': 'Circular',
            'date': '2021',
            'title': 'Tier-1 and Tier-2 Benchmark Requirements',
            'description': 'All schemes must declare two benchmarks: Tier-1 (broad market index) and Tier-2 (scheme-specific). Performance must be disclosed against both benchmarks. Helps investors compare scheme performance with appropriate market indices.',
            'source': 'https://www.sebi.gov.in'
        },
    ]

    return guidelines


def save_to_csv(data: List[Dict], filename: str):
    """Save scraped data to CSV file."""
    if not data:
        print(f"  No data to save to {filename}")
        return

    # Ensure data directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    fieldnames = ['type', 'date', 'title', 'description', 'source']

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"  Saved {len(data)} records to {filename}")


def run():
    """Main function to run the SEBI guidelines scraper."""
    print("\n" + "="*60)
    print("SEBI GUIDELINES SCRAPER")
    print("="*60)

    all_data = []

    # Get static guidelines (comprehensive and reliable)
    print("\nLoading SEBI guidelines and regulations...")
    static_data = get_sebi_guidelines_static()
    all_data.extend(static_data)
    print(f"  Loaded {len(static_data)} guidelines")

    # Scrape latest circulars
    print("\nScraping SEBI website for latest circulars...")
    try:
        circular_data = scrape_sebi_circulars()
        # Avoid duplicates
        existing_titles = {item['title'].lower() for item in all_data}
        new_data = [item for item in circular_data if item['title'].lower() not in existing_titles]
        all_data.extend(new_data)
        print(f"  Added {len(new_data)} new circulars")
    except Exception as e:
        print(f"  Failed to scrape circulars: {e}")

    # Save to CSV
    print("\nSaving data...")
    save_to_csv(all_data, OUTPUT_FILE)

    print(f"\nTotal records: {len(all_data)}")
    print("="*60)

    return all_data


if __name__ == "__main__":
    run()
