"""
Mutual Fund Basics Scraper
Scrapes basic definitions, concepts, and categories of mutual funds in India.
"""

import requests
from bs4 import BeautifulSoup
import csv
import os
import time
from typing import List, Dict

# Constants
OUTPUT_FILE = "data/mutual_fund_basics.csv"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
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


def scrape_amfi_basics() -> List[Dict]:
    """Scrape mutual fund basics from AMFI website."""
    data = []

    # AMFI Knowledge Center URLs (updated to current structure)
    urls = [
        ("https://www.amfiindia.com/investor/knowledge-center-info?zoneName=TypesOfMutualFundSchemes", "Types of Mutual Fund Schemes"),
        ("https://www.amfiindia.com/investor/knowledge-center-info?zoneName=TaxRegimeForMutualFunds", "Tax Regime for Mutual Funds"),
        ("https://www.amfiindia.com/investor-corner/", "Investor Corner"),
    ]

    for url, topic in urls:
        try:
            print(f"  Scraping: {topic}")
            response = make_request(url)
            if response:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Find main content - try multiple selectors
                content_div = (
                    soup.find('div', class_='knowledge-center-content') or
                    soup.find('div', class_='content-area') or
                    soup.find('div', class_='main-content') or
                    soup.find('div', id='content') or
                    soup.find('article') or
                    soup.find('main')
                )

                if content_div:
                    # Get all text content
                    paragraphs = content_div.find_all(['p', 'li', 'div'])
                    content = ' '.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True) and len(p.get_text(strip=True)) > 20])

                    if content and len(content) > 100:
                        data.append({
                            'category': 'Basic Concept',
                            'topic': topic,
                            'content': content[:2000],  # Limit content length
                            'source': url
                        })
                else:
                    # Fallback: get all text from body
                    body = soup.find('body')
                    if body:
                        text = body.get_text(separator=' ', strip=True)
                        if len(text) > 200:
                            data.append({
                                'category': 'Basic Concept',
                                'topic': topic,
                                'content': text[:2000],
                                'source': url
                            })
        except Exception as e:
            print(f"  Error scraping {url}: {e}")

    return data


def get_static_basics() -> List[Dict]:
    """Return static mutual fund basics data (standard definitions)."""
    basics = [
        # Basic Definitions
        {
            'category': 'Definition',
            'topic': 'What is a Mutual Fund',
            'content': 'A mutual fund is a professionally managed investment vehicle that pools money from multiple investors to purchase securities like stocks, bonds, and other assets. Each investor owns shares representing a portion of the holdings. Mutual funds are regulated by SEBI in India and managed by Asset Management Companies (AMCs).',
            'source': 'Standard Definition'
        },
        {
            'category': 'Definition',
            'topic': 'Net Asset Value (NAV)',
            'content': 'NAV is the per-unit market value of a mutual fund scheme. It is calculated by dividing the total value of all assets in the portfolio minus liabilities by the number of units outstanding. NAV = (Total Assets - Total Liabilities) / Number of Units. NAV is declared daily by mutual funds.',
            'source': 'Standard Definition'
        },
        {
            'category': 'Definition',
            'topic': 'Expense Ratio',
            'content': 'Expense ratio is the annual fee charged by mutual funds to cover operating expenses including management fees, administrative costs, and distribution charges. It is expressed as a percentage of average assets under management (AUM). Lower expense ratios mean higher returns for investors. SEBI has capped expense ratios based on AUM slabs.',
            'source': 'Standard Definition'
        },

        # Fund Categories
        {
            'category': 'Fund Type',
            'topic': 'Equity Funds',
            'content': 'Equity funds invest primarily (at least 65%) in stocks of companies. Sub-categories include: Large-cap (top 100 companies), Mid-cap (101-250), Small-cap (251+), Multi-cap, Flexi-cap, Sectoral/Thematic, ELSS (tax-saving), and Focused funds. They offer high growth potential but come with higher risk and volatility.',
            'source': 'SEBI Categorization'
        },
        {
            'category': 'Fund Type',
            'topic': 'Debt Funds',
            'content': 'Debt funds invest in fixed-income securities like government bonds, corporate bonds, treasury bills, and money market instruments. Types include: Overnight, Liquid, Ultra-short duration, Low duration, Money market, Short duration, Medium duration, Long duration, Dynamic bond, Corporate bond, Credit risk, Banking & PSU, and Gilt funds.',
            'source': 'SEBI Categorization'
        },
        {
            'category': 'Fund Type',
            'topic': 'Hybrid Funds',
            'content': 'Hybrid funds invest in a mix of equity and debt instruments. Categories include: Conservative hybrid (10-25% equity), Balanced hybrid (40-60% equity), Aggressive hybrid (65-80% equity), Dynamic asset allocation, Multi-asset allocation (minimum 3 asset classes), Arbitrage funds, and Equity savings funds.',
            'source': 'SEBI Categorization'
        },
        {
            'category': 'Fund Type',
            'topic': 'Index Funds',
            'content': 'Index funds passively track a specific market index like Nifty 50, Sensex, or Nifty Next 50. They aim to replicate the index composition and returns with minimal tracking error. They have lower expense ratios than actively managed funds and are suitable for long-term passive investing.',
            'source': 'SEBI Categorization'
        },
        {
            'category': 'Fund Type',
            'topic': 'Exchange Traded Funds (ETFs)',
            'content': 'ETFs are index funds that trade on stock exchanges like regular shares. They track indices, commodities, or baskets of assets. Benefits include real-time trading, lower expense ratios, and transparency. Types include equity ETFs, gold ETFs, bond ETFs, and international ETFs.',
            'source': 'SEBI Categorization'
        },
        {
            'category': 'Fund Type',
            'topic': 'Fund of Funds (FoF)',
            'content': 'Fund of Funds invest in other mutual fund schemes rather than directly in securities. They provide diversification across multiple fund managers and strategies. FoFs may invest in domestic or international funds and are suitable for investors seeking simplified diversification.',
            'source': 'SEBI Categorization'
        },

        # Riskometer
        {
            'category': 'Risk Classification',
            'topic': 'Riskometer Categories',
            'content': 'SEBI mandates a 6-level riskometer for all mutual funds: 1) Low - Principal at low risk (overnight, liquid funds), 2) Low to Moderate - Principal at low to moderate risk (ultra-short duration funds), 3) Moderate - Principal at moderate risk (short duration debt), 4) Moderately High - Principal at moderately high risk (hybrid funds), 5) High - Principal at high risk (equity funds), 6) Very High - Principal at very high risk (small-cap, sectoral funds).',
            'source': 'SEBI Guidelines'
        },

        # Taxation
        {
            'category': 'Taxation',
            'topic': 'Equity Fund Taxation',
            'content': 'Equity funds (65%+ in equity): Short-term capital gains (STCG) on units held less than 12 months are taxed at 15%. Long-term capital gains (LTCG) on units held over 12 months are taxed at 10% on gains exceeding Rs 1 lakh per year. Dividends are taxed at slab rates.',
            'source': 'Income Tax Act'
        },
        {
            'category': 'Taxation',
            'topic': 'Debt Fund Taxation',
            'content': 'Debt funds: All capital gains (short-term and long-term) are added to income and taxed at applicable slab rates. There is no distinction based on holding period for tax purposes. TDS of 10% applies if annual gains exceed Rs 5,000.',
            'source': 'Income Tax Act'
        },
        {
            'category': 'Taxation',
            'topic': 'ELSS Tax Benefits',
            'content': 'Equity Linked Savings Schemes (ELSS) qualify for tax deduction under Section 80C up to Rs 1.5 lakh per year. They have a mandatory 3-year lock-in period, the shortest among 80C instruments. LTCG on ELSS is taxed at 10% on gains exceeding Rs 1 lakh.',
            'source': 'Income Tax Act'
        },

        # Investment Concepts
        {
            'category': 'Investment Concept',
            'topic': 'Systematic Investment Plan (SIP)',
            'content': 'SIP allows investors to invest a fixed amount regularly (weekly, monthly, quarterly) in mutual funds. Benefits include rupee cost averaging, disciplined investing, power of compounding, and flexibility. Minimum SIP can be as low as Rs 100-500 per month.',
            'source': 'Standard Definition'
        },
        {
            'category': 'Investment Concept',
            'topic': 'Systematic Withdrawal Plan (SWP)',
            'content': 'SWP allows investors to withdraw a fixed amount from their mutual fund investments at regular intervals. It provides regular income while remaining investment continues to grow. Useful for retirees or those needing regular cash flow.',
            'source': 'Standard Definition'
        },
        {
            'category': 'Investment Concept',
            'topic': 'Systematic Transfer Plan (STP)',
            'content': 'STP allows automatic transfer of a fixed amount from one mutual fund scheme to another within the same AMC. Commonly used to transfer from debt/liquid funds to equity funds gradually, reducing market timing risk.',
            'source': 'Standard Definition'
        },

        # Regulatory Concepts
        {
            'category': 'Regulation',
            'topic': 'SEBI Role',
            'content': 'Securities and Exchange Board of India (SEBI) regulates mutual funds under SEBI (Mutual Funds) Regulations, 1996. SEBI approves AMCs, mandates disclosures, sets expense ratio limits, defines fund categories, and protects investor interests through various guidelines.',
            'source': 'SEBI'
        },
        {
            'category': 'Regulation',
            'topic': 'AMFI Role',
            'content': 'Association of Mutual Funds in India (AMFI) is the industry body representing all AMCs. It sets ethical standards, provides investor education, maintains distributor certification (ARN), publishes NAV data, and promotes best practices in the industry.',
            'source': 'AMFI'
        },
    ]

    return basics


def scrape_groww_basics() -> List[Dict]:
    """Scrape additional content from Groww's educational pages."""
    data = []

    urls = [
        "https://groww.in/mutual-funds",
    ]

    for url in urls:
        try:
            print(f"  Scraping Groww: {url}")
            response = make_request(url)
            if response:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Find educational content sections
                sections = soup.find_all(['section', 'div'], class_=lambda x: x and ('content' in x.lower() or 'article' in x.lower()))

                for section in sections[:5]:  # Limit to first 5 sections
                    heading = section.find(['h1', 'h2', 'h3'])
                    paragraphs = section.find_all('p')

                    if heading and paragraphs:
                        title = heading.get_text(strip=True)
                        content = ' '.join([p.get_text(strip=True) for p in paragraphs])

                        if len(content) > 50:
                            data.append({
                                'category': 'Educational Content',
                                'topic': title[:100],
                                'content': content[:1500],
                                'source': url
                            })
        except Exception as e:
            print(f"  Error scraping Groww: {e}")

    return data


def save_to_csv(data: List[Dict], filename: str):
    """Save scraped data to CSV file."""
    if not data:
        print(f"  No data to save to {filename}")
        return

    # Ensure data directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    fieldnames = ['category', 'topic', 'content', 'source']

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"  Saved {len(data)} records to {filename}")


def run():
    """Main function to run the mutual fund basics scraper."""
    print("\n" + "="*60)
    print("MUTUAL FUND BASICS SCRAPER")
    print("="*60)

    all_data = []

    # Get static basics (reliable, always available)
    print("\nLoading standard definitions...")
    static_data = get_static_basics()
    all_data.extend(static_data)
    print(f"  Loaded {len(static_data)} standard definitions")

    # Scrape AMFI basics
    print("\nScraping AMFI website...")
    try:
        amfi_data = scrape_amfi_basics()
        all_data.extend(amfi_data)
        print(f"  Scraped {len(amfi_data)} items from AMFI")
    except Exception as e:
        print(f"  Failed to scrape AMFI: {e}")

    # Scrape Groww basics
    print("\nScraping Groww educational content...")
    try:
        groww_data = scrape_groww_basics()
        all_data.extend(groww_data)
        print(f"  Scraped {len(groww_data)} items from Groww")
    except Exception as e:
        print(f"  Failed to scrape Groww: {e}")

    # Save to CSV
    print("\nSaving data...")
    save_to_csv(all_data, OUTPUT_FILE)

    print(f"\nTotal records: {len(all_data)}")
    print("="*60)

    return all_data


if __name__ == "__main__":
    run()
