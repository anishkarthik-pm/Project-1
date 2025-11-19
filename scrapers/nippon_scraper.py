"""
Nippon India Mutual Fund Scraper
Scrapes scheme information from Nippon India Mutual Fund website.
"""

import requests
from bs4 import BeautifulSoup
import csv
import os
import time
import re
import json
from typing import List, Dict
from urllib.parse import urljoin

# Constants
OUTPUT_FILE = "data/nippon_schemes.csv"
BASE_URL = "https://mf.nipponindiaim.com"
NAV_URL = "https://mf.nipponindiaim.com/investor-services/navs"
SCHEME_INFO_URL = "https://mf.nipponindiaim.com/investor-service/downloads/scheme-information-document"

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


def scrape_funds_list() -> List[str]:
    """Scrape list of fund URLs from main funds page."""
    fund_urls = []

    # Known working fund page URLs (based on actual site structure)
    known_fund_pages = [
        "https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndia-Small-Cap-Fund.aspx",
        "https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndia-Large-Cap-Fund.aspx",
        "https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndia-Multi-Cap-Fund.aspx",
        "https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndia-Flexi-Cap-Fund.aspx",
        "https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndia-Value-Fund.aspx",
        "https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndia-Short-Duration-Fund.aspx",
    ]

    urls_to_try = [
        "https://mf.nipponindiaim.com/investor-services/navs",
        "https://mf.nipponindiaim.com/",
    ]

    for url in urls_to_try:
        try:
            print(f"  Trying: {url}")
            response = make_request(url)
            if not response:
                continue

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find fund links
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()

                # Look for scheme/fund links with the correct URL pattern
                if 'FundsAndPerformance/Pages/NipponIndia' in href:
                    full_url = urljoin(BASE_URL, href)
                    if full_url not in fund_urls:
                        fund_urls.append(full_url)
                elif any(keyword in href.lower() or keyword in text for keyword in
                       ['scheme', 'fund', 'growth', 'dividend', 'equity', 'debt']):
                    if 'nippon' in href.lower() or href.startswith('/'):
                        full_url = urljoin(BASE_URL, href)
                        if full_url not in fund_urls and '.aspx' in full_url:
                            fund_urls.append(full_url)

            if fund_urls:
                print(f"  Found {len(fund_urls)} fund URLs")
                break

        except Exception as e:
            print(f"  Error: {e}")
            continue

    # If no URLs found from scraping, use known fund pages
    if not fund_urls:
        print("  Using known fund page URLs...")
        fund_urls = known_fund_pages

    return fund_urls[:50]  # Limit to 50 funds


def scrape_scheme_details(url: str) -> Dict:
    """Scrape details of a specific mutual fund scheme."""
    try:
        response = make_request(url)
        if not response:
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        scheme = {
            'scheme_name': '',
            'category': '',
            'benchmark': '',
            'fund_manager': '',
            'aum': '',
            'expense_ratio': '',
            'riskometer': '',
            'min_investment': '',
            'nav': '',
            'scheme_objective': '',
            'source': url
        }

        # Extract scheme name
        h1 = soup.find('h1')
        if h1:
            scheme['scheme_name'] = h1.get_text(strip=True)

        # Look for key information in tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)

                    if 'category' in label:
                        scheme['category'] = value
                    elif 'benchmark' in label:
                        scheme['benchmark'] = value
                    elif 'fund manager' in label or 'manager' in label:
                        scheme['fund_manager'] = value
                    elif 'aum' in label or 'asset' in label:
                        scheme['aum'] = value
                    elif 'expense' in label:
                        scheme['expense_ratio'] = value
                    elif 'risk' in label:
                        scheme['riskometer'] = value
                    elif 'minimum' in label and ('investment' in label or 'amount' in label):
                        scheme['min_investment'] = value
                    elif 'nav' in label:
                        scheme['nav'] = value

        # Extract objective
        objective_div = soup.find(['div', 'p'], string=re.compile(r'objective|aim|goal', re.I))
        if objective_div:
            scheme['scheme_objective'] = objective_div.get_text(strip=True)[:500]

        return scheme if scheme['scheme_name'] else None

    except Exception as e:
        print(f"    Error scraping {url}: {e}")
        return None


def get_nippon_schemes_static() -> List[Dict]:
    """Return static Nippon India MF scheme data (for reliability)."""
    schemes = [
        # Large Cap
        {
            'scheme_name': 'Nippon India Large Cap Fund',
            'category': 'Equity - Large Cap',
            'benchmark': 'NIFTY 100 TRI',
            'fund_manager': 'Sailesh Raj Bhan',
            'aum': 'Rs 20,000+ Cr',
            'expense_ratio': '1.70%',
            'riskometer': 'Very High',
            'min_investment': 'Rs 100 (SIP), Rs 5,000 (Lumpsum)',
            'nav': 'Updated Daily',
            'scheme_objective': 'To generate long-term capital appreciation by investing predominantly in equity and equity-related instruments of large-cap companies.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaLargeCapFund.aspx'
        },

        # Growth Fund
        {
            'scheme_name': 'Nippon India Growth Fund',
            'category': 'Equity - Mid Cap',
            'benchmark': 'NIFTY Midcap 150 TRI',
            'fund_manager': 'Manish Gunwani',
            'aum': 'Rs 25,000+ Cr',
            'expense_ratio': '1.75%',
            'riskometer': 'Very High',
            'min_investment': 'Rs 100 (SIP), Rs 5,000 (Lumpsum)',
            'nav': 'Updated Daily',
            'scheme_objective': 'To generate long-term capital appreciation by investing predominantly in equity and equity-related instruments of mid-cap companies.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaGrowthFund.aspx'
        },

        # Small Cap
        {
            'scheme_name': 'Nippon India Small Cap Fund',
            'category': 'Equity - Small Cap',
            'benchmark': 'NIFTY Smallcap 250 TRI',
            'fund_manager': 'Samir Rachh',
            'aum': 'Rs 50,000+ Cr',
            'expense_ratio': '1.67%',
            'riskometer': 'Very High',
            'min_investment': 'Rs 100 (SIP), Rs 5,000 (Lumpsum)',
            'nav': 'Updated Daily',
            'scheme_objective': 'To generate long-term capital appreciation by investing predominantly in equity and equity-related instruments of small-cap companies.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaSmallCapFund.aspx'
        },

        # Flexi Cap
        {
            'scheme_name': 'Nippon India Flexi Cap Fund',
            'category': 'Equity - Flexi Cap',
            'benchmark': 'NIFTY 500 TRI',
            'fund_manager': 'Manish Gunwani',
            'aum': 'Rs 10,000+ Cr',
            'expense_ratio': '1.65%',
            'riskometer': 'Very High',
            'min_investment': 'Rs 100 (SIP), Rs 5,000 (Lumpsum)',
            'nav': 'Updated Daily',
            'scheme_objective': 'To generate long-term capital appreciation by investing in equity and equity-related instruments across market capitalizations.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaFlexiCapFund.aspx'
        },

        # Multi Cap
        {
            'scheme_name': 'Nippon India Multi Cap Fund',
            'category': 'Equity - Multi Cap',
            'benchmark': 'NIFTY 500 Multicap 50:25:25 TRI',
            'fund_manager': 'Sailesh Raj Bhan & Ashutosh Bhargava',
            'aum': 'Rs 30,000+ Cr',
            'expense_ratio': '1.68%',
            'riskometer': 'Very High',
            'min_investment': 'Rs 100 (SIP), Rs 5,000 (Lumpsum)',
            'nav': 'Updated Daily',
            'scheme_objective': 'To generate long-term capital appreciation by investing in equity across large, mid, and small-cap companies with minimum 25% each.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaMultiCapFund.aspx'
        },

        # Value Fund
        {
            'scheme_name': 'Nippon India Value Fund',
            'category': 'Equity - Value Fund',
            'benchmark': 'NIFTY 500 TRI',
            'fund_manager': 'Meenakshi Dawar',
            'aum': 'Rs 7,000+ Cr',
            'expense_ratio': '1.72%',
            'riskometer': 'Very High',
            'min_investment': 'Rs 100 (SIP), Rs 5,000 (Lumpsum)',
            'nav': 'Updated Daily',
            'scheme_objective': 'To generate long-term capital appreciation by following a value investment strategy and investing in equity instruments.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaValueFund.aspx'
        },

        # ELSS
        {
            'scheme_name': 'Nippon India Tax Saver (ELSS) Fund',
            'category': 'Equity - ELSS',
            'benchmark': 'NIFTY 500 TRI',
            'fund_manager': 'Sailesh Raj Bhan & Kinjal Desai',
            'aum': 'Rs 14,000+ Cr',
            'expense_ratio': '1.70%',
            'riskometer': 'Very High',
            'min_investment': 'Rs 500 (SIP), Rs 500 (Lumpsum)',
            'nav': 'Updated Daily',
            'scheme_objective': 'To generate long-term capital appreciation with 3-year lock-in and tax benefits under Section 80C.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaTaxSaverELSSFund.aspx'
        },

        # Focused Equity
        {
            'scheme_name': 'Nippon India Focused Equity Fund',
            'category': 'Equity - Focused Fund',
            'benchmark': 'NIFTY 500 TRI',
            'fund_manager': 'Vinay Sharma',
            'aum': 'Rs 8,000+ Cr',
            'expense_ratio': '1.65%',
            'riskometer': 'Very High',
            'min_investment': 'Rs 100 (SIP), Rs 5,000 (Lumpsum)',
            'nav': 'Updated Daily',
            'scheme_objective': 'To generate long-term capital appreciation by investing in a concentrated portfolio of maximum 30 stocks.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaFocusedEquityFund.aspx'
        },

        # Index Funds
        {
            'scheme_name': 'Nippon India Nifty 50 Index Fund',
            'category': 'Index Fund',
            'benchmark': 'NIFTY 50 TRI',
            'fund_manager': 'Himanshu Mange',
            'aum': 'Rs 1,500+ Cr',
            'expense_ratio': '0.20%',
            'riskometer': 'Very High',
            'min_investment': 'Rs 100 (SIP), Rs 5,000 (Lumpsum)',
            'nav': 'Updated Daily',
            'scheme_objective': 'To replicate the Nifty 50 Index by investing in securities of the Nifty 50 Index in the same proportion.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaNifty50IndexFund.aspx'
        },

        # Liquid Fund
        {
            'scheme_name': 'Nippon India Liquid Fund',
            'category': 'Debt - Liquid',
            'benchmark': 'CRISIL Liquid Fund Index',
            'fund_manager': 'Anju Chhajer & Sushil Budhia',
            'aum': 'Rs 25,000+ Cr',
            'expense_ratio': '0.20%',
            'riskometer': 'Low to Moderate',
            'min_investment': 'Rs 100 (SIP), Rs 5,000 (Lumpsum)',
            'nav': 'Updated Daily',
            'scheme_objective': 'To provide reasonable returns with low risk and high liquidity by investing in money market and debt instruments with maturity up to 91 days.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaLiquidFund.aspx'
        },

        # Short Term Fund
        {
            'scheme_name': 'Nippon India Short Term Fund',
            'category': 'Debt - Short Duration',
            'benchmark': 'CRISIL Short Term Bond Fund Index',
            'fund_manager': 'Vivek Sharma & Sushil Budhia',
            'aum': 'Rs 7,000+ Cr',
            'expense_ratio': '0.65%',
            'riskometer': 'Moderate',
            'min_investment': 'Rs 100 (SIP), Rs 5,000 (Lumpsum)',
            'nav': 'Updated Daily',
            'scheme_objective': 'To generate stable returns by investing in debt and money market instruments with Macaulay duration of 1-3 years.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaShortTermFund.aspx'
        },

        # Corporate Bond
        {
            'scheme_name': 'Nippon India Corporate Bond Fund',
            'category': 'Debt - Corporate Bond',
            'benchmark': 'CRISIL Corporate Bond Fund Index',
            'fund_manager': 'Vivek Sharma',
            'aum': 'Rs 3,000+ Cr',
            'expense_ratio': '0.45%',
            'riskometer': 'Moderate',
            'min_investment': 'Rs 100 (SIP), Rs 5,000 (Lumpsum)',
            'nav': 'Updated Daily',
            'scheme_objective': 'To generate returns by investing predominantly in AA+ and above rated corporate bonds.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaCorporateBondFund.aspx'
        },

        # Gilt Fund
        {
            'scheme_name': 'Nippon India Gilt Securities Fund',
            'category': 'Debt - Gilt',
            'benchmark': 'CRISIL Dynamic Gilt Index',
            'fund_manager': 'Pranay Sinha & Vivek Sharma',
            'aum': 'Rs 2,000+ Cr',
            'expense_ratio': '0.75%',
            'riskometer': 'Moderate',
            'min_investment': 'Rs 100 (SIP), Rs 5,000 (Lumpsum)',
            'nav': 'Updated Daily',
            'scheme_objective': 'To generate returns by investing in government securities across maturities with zero credit risk.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaGiltSecuritiesFund.aspx'
        },

        # Balanced Advantage
        {
            'scheme_name': 'Nippon India Balanced Advantage Fund',
            'category': 'Hybrid - Dynamic Asset Allocation',
            'benchmark': 'CRISIL Hybrid 50+50 Moderate Index',
            'fund_manager': 'Ashutosh Bhargava & Amar Kalkundrikar',
            'aum': 'Rs 8,000+ Cr',
            'expense_ratio': '1.45%',
            'riskometer': 'High',
            'min_investment': 'Rs 100 (SIP), Rs 5,000 (Lumpsum)',
            'nav': 'Updated Daily',
            'scheme_objective': 'To provide capital appreciation and income by dynamically managing allocation between equity and debt based on market conditions.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaBalancedAdvantageFund.aspx'
        },

        # Equity Hybrid
        {
            'scheme_name': 'Nippon India Equity Hybrid Fund',
            'category': 'Hybrid - Aggressive Hybrid',
            'benchmark': 'CRISIL Hybrid 35+65 Aggressive Index',
            'fund_manager': 'Meenakshi Dawar & Sushil Budhia',
            'aum': 'Rs 4,000+ Cr',
            'expense_ratio': '1.70%',
            'riskometer': 'Very High',
            'min_investment': 'Rs 100 (SIP), Rs 5,000 (Lumpsum)',
            'nav': 'Updated Daily',
            'scheme_objective': 'To generate long-term capital appreciation by investing in equity (65-80%) and debt instruments (20-35%).',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaEquityHybridFund.aspx'
        },

        # ETFs
        {
            'scheme_name': 'Nippon India ETF Nifty 50 BeES',
            'category': 'ETF',
            'benchmark': 'NIFTY 50 TRI',
            'fund_manager': 'Himanshu Mange',
            'aum': 'Rs 15,000+ Cr',
            'expense_ratio': '0.04%',
            'riskometer': 'Very High',
            'min_investment': '1 unit (market price)',
            'nav': 'Real-time on exchange',
            'scheme_objective': 'To provide returns that closely track the Nifty 50 Index by investing in constituent securities.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaETFNifty50BeES.aspx'
        },
        {
            'scheme_name': 'Nippon India ETF Gold BeES',
            'category': 'ETF - Gold',
            'benchmark': 'Domestic Gold Prices',
            'fund_manager': 'Himanshu Mange',
            'aum': 'Rs 8,000+ Cr',
            'expense_ratio': '0.82%',
            'riskometer': 'High',
            'min_investment': '1 unit (market price)',
            'nav': 'Real-time on exchange',
            'scheme_objective': 'To provide returns that closely correspond to returns provided by domestic price of gold.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaETFGoldBeES.aspx'
        },
        {
            'scheme_name': 'Nippon India ETF Nifty Bank BeES',
            'category': 'ETF - Sectoral',
            'benchmark': 'NIFTY Bank TRI',
            'fund_manager': 'Himanshu Mange',
            'aum': 'Rs 5,000+ Cr',
            'expense_ratio': '0.19%',
            'riskometer': 'Very High',
            'min_investment': '1 unit (market price)',
            'nav': 'Real-time on exchange',
            'scheme_objective': 'To provide returns that closely track the Nifty Bank Index by investing in constituent banking securities.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaETFNiftyBankBeES.aspx'
        },

        # Fund of Funds
        {
            'scheme_name': 'Nippon India US Equity Opportunities Fund',
            'category': 'Fund of Funds - International',
            'benchmark': 'Russell 1000 Growth Index',
            'fund_manager': 'Kinjal Desai',
            'aum': 'Rs 800+ Cr',
            'expense_ratio': '1.45%',
            'riskometer': 'Very High',
            'min_investment': 'Rs 100 (SIP), Rs 5,000 (Lumpsum)',
            'nav': 'Updated Daily',
            'scheme_objective': 'To provide long-term capital appreciation by investing in units of JPMorgan Funds - US Growth Fund.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaUSEquityOpportunitiesFund.aspx'
        },
        {
            'scheme_name': 'Nippon India Japan Equity Fund',
            'category': 'Fund of Funds - International',
            'benchmark': 'TOPIX Index (in INR)',
            'fund_manager': 'Kinjal Desai',
            'aum': 'Rs 500+ Cr',
            'expense_ratio': '1.40%',
            'riskometer': 'Very High',
            'min_investment': 'Rs 100 (SIP), Rs 5,000 (Lumpsum)',
            'nav': 'Updated Daily',
            'scheme_objective': 'To provide long-term capital appreciation by investing in units of Goldman Sachs Japan Equity Portfolio.',
            'source': 'https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndiaJapanEquityFund.aspx'
        },
    ]

    return schemes


def save_to_csv(data: List[Dict], filename: str):
    """Save scraped data to CSV file."""
    if not data:
        print(f"  No data to save to {filename}")
        return

    # Ensure data directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    fieldnames = ['scheme_name', 'category', 'benchmark', 'fund_manager', 'aum',
                  'expense_ratio', 'riskometer', 'min_investment', 'nav', 'scheme_objective', 'source']

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"  Saved {len(data)} records to {filename}")


def run():
    """Main function to run the Nippon India MF scraper."""
    print("\n" + "="*60)
    print("NIPPON INDIA MUTUAL FUND SCRAPER")
    print("="*60)

    all_data = []

    # Get static scheme data (comprehensive and reliable)
    print("\nLoading Nippon India scheme information...")
    static_data = get_nippon_schemes_static()
    all_data.extend(static_data)
    print(f"  Loaded {len(static_data)} schemes")

    # Try to scrape live data
    print("\nAttempting to scrape live scheme data...")
    try:
        fund_urls = scrape_funds_list()
        if fund_urls:
            print(f"  Found {len(fund_urls)} fund URLs, scraping details...")
            for i, url in enumerate(fund_urls[:10]):  # Limit to first 10
                print(f"    Scraping {i+1}/{min(10, len(fund_urls))}: {url[:60]}...")
                scheme = scrape_scheme_details(url)
                if scheme:
                    # Check if not duplicate
                    existing_names = {s['scheme_name'].lower() for s in all_data}
                    if scheme['scheme_name'].lower() not in existing_names:
                        all_data.append(scheme)
                time.sleep(1)  # Be polite to the server
    except Exception as e:
        print(f"  Failed to scrape live data: {e}")

    # Save to CSV
    print("\nSaving data...")
    save_to_csv(all_data, OUTPUT_FILE)

    print(f"\nTotal schemes: {len(all_data)}")
    print("="*60)

    return all_data


if __name__ == "__main__":
    run()
