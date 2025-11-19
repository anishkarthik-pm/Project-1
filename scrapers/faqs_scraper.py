"""
FAQs Scraper
Scrapes frequently asked questions about mutual funds from various sources.
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
OUTPUT_FILE = "data/faqs.csv"
AMFI_FAQ_URL = "https://www.amfiindia.com/investor-corner/investor-awareness/faqs"

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


def scrape_amfi_faqs() -> List[Dict]:
    """Scrape FAQs from AMFI website."""
    data = []

    try:
        print(f"  Scraping: {AMFI_FAQ_URL}")
        response = make_request(AMFI_FAQ_URL)
        if not response:
            return data

        soup = BeautifulSoup(response.content, 'html.parser')

        # AMFI uses accordion-style FAQs
        # Look for question-answer pairs

        # Try different HTML structures
        # Pattern 1: Accordion items
        accordions = soup.find_all(['div', 'section'], class_=lambda x: x and ('accordion' in str(x).lower() or 'faq' in str(x).lower()))

        for accordion in accordions:
            # Find question headers
            questions = accordion.find_all(['h3', 'h4', 'h5', 'button', 'div'],
                                          class_=lambda x: x and ('question' in str(x).lower() or 'header' in str(x).lower() or 'title' in str(x).lower()))

            for q_elem in questions:
                question = q_elem.get_text(strip=True)

                # Find the next sibling or child that contains the answer
                answer_elem = q_elem.find_next_sibling(['div', 'p']) or q_elem.find_next(['div', 'p'])

                if answer_elem:
                    answer = answer_elem.get_text(strip=True)

                    if question and answer and len(question) > 10 and len(answer) > 20:
                        data.append({
                            'question': question[:500],
                            'answer': answer[:2000],
                            'category': 'General',
                            'source': AMFI_FAQ_URL
                        })

        # Pattern 2: Definition lists
        dl_elements = soup.find_all('dl')
        for dl in dl_elements:
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')

            for dt, dd in zip(dts, dds):
                question = dt.get_text(strip=True)
                answer = dd.get_text(strip=True)

                if question and answer:
                    data.append({
                        'question': question[:500],
                        'answer': answer[:2000],
                        'category': 'General',
                        'source': AMFI_FAQ_URL
                    })

        # Pattern 3: Q&A with specific classes
        q_elements = soup.find_all(['div', 'p', 'span'], string=re.compile(r'^Q[\d\.\:\s]|^Question', re.I))
        for q_elem in q_elements:
            question = q_elem.get_text(strip=True)
            answer_elem = q_elem.find_next(['div', 'p'])

            if answer_elem:
                answer = answer_elem.get_text(strip=True)
                if answer and not answer.startswith('Q'):
                    data.append({
                        'question': question[:500],
                        'answer': answer[:2000],
                        'category': 'General',
                        'source': AMFI_FAQ_URL
                    })

        print(f"  Scraped {len(data)} FAQs from AMFI")

    except Exception as e:
        print(f"  Error scraping AMFI FAQs: {e}")

    return data


def scrape_groww_faqs() -> List[Dict]:
    """Scrape FAQs from Groww website."""
    data = []

    urls = [
        "https://groww.in/mutual-funds",
    ]

    for url in urls:
        try:
            print(f"  Scraping: {url}")
            response = make_request(url)
            if not response:
                continue

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for FAQ sections
            faq_sections = soup.find_all(['div', 'section'], class_=lambda x: x and 'faq' in str(x).lower())

            for section in faq_sections:
                items = section.find_all(['div', 'details'], recursive=True)

                for item in items:
                    q_elem = item.find(['summary', 'h3', 'h4', 'button'])
                    a_elem = item.find(['p', 'div'], class_=lambda x: x != q_elem.get('class') if q_elem else True)

                    if q_elem and a_elem:
                        question = q_elem.get_text(strip=True)
                        answer = a_elem.get_text(strip=True)

                        if question and answer and len(answer) > 20:
                            data.append({
                                'question': question[:500],
                                'answer': answer[:2000],
                                'category': 'General',
                                'source': url
                            })

        except Exception as e:
            print(f"  Error scraping {url}: {e}")

    return data


def get_static_faqs() -> List[Dict]:
    """Return comprehensive static FAQs about mutual funds."""
    faqs = [
        # Basic Concepts
        {
            'question': 'What is a mutual fund?',
            'answer': 'A mutual fund is a professionally managed investment vehicle that pools money from multiple investors to purchase a diversified portfolio of securities like stocks, bonds, and other assets. Each investor owns shares (units) representing a portion of the holdings. Mutual funds are managed by Asset Management Companies (AMCs) and regulated by SEBI in India.',
            'category': 'Basic Concepts',
            'source': 'Standard FAQ'
        },
        {
            'question': 'What is NAV (Net Asset Value)?',
            'answer': 'NAV is the per-unit market value of a mutual fund scheme. It is calculated by dividing the total value of all assets in the portfolio minus liabilities by the total number of units outstanding. Formula: NAV = (Total Assets - Total Liabilities) / Number of Units. NAV is declared daily by mutual funds after market close.',
            'category': 'Basic Concepts',
            'source': 'Standard FAQ'
        },
        {
            'question': 'What is the difference between direct and regular plans?',
            'answer': 'Direct plans are purchased directly from the AMC without any distributor, resulting in lower expense ratios (no commission). Regular plans are purchased through distributors/agents who receive commission, leading to higher expense ratios. Both plans have the same portfolio but different NAVs due to expense ratio differences. Direct plans typically give 0.5-1% higher returns annually.',
            'category': 'Basic Concepts',
            'source': 'Standard FAQ'
        },
        {
            'question': 'What is expense ratio?',
            'answer': 'Expense ratio is the annual fee charged by mutual funds as a percentage of assets under management (AUM) to cover operating costs including fund management fees, administrative costs, and distribution expenses. SEBI has capped expense ratios based on AUM slabs. Lower expense ratios mean more of your money is invested rather than paid as fees.',
            'category': 'Basic Concepts',
            'source': 'Standard FAQ'
        },
        {
            'question': 'What is exit load?',
            'answer': 'Exit load is a fee charged when you redeem (sell) your mutual fund units before a specified period. It discourages short-term trading and protects long-term investors. Typical exit loads are 1% if redeemed within 1 year for equity funds. Liquid funds have graded exit loads for redemptions within 7 days. The exit load amount goes back into the scheme.',
            'category': 'Basic Concepts',
            'source': 'Standard FAQ'
        },

        # Investment Methods
        {
            'question': 'What is SIP (Systematic Investment Plan)?',
            'answer': 'SIP allows you to invest a fixed amount regularly (weekly, monthly, quarterly) in a mutual fund scheme. Benefits include rupee cost averaging (buying more units when prices are low), disciplined investing, power of compounding, and flexibility to start with small amounts (as low as Rs 100-500). SIPs help avoid market timing risk.',
            'category': 'Investment Methods',
            'source': 'Standard FAQ'
        },
        {
            'question': 'What is lumpsum investment?',
            'answer': 'Lumpsum investment is when you invest a large amount at once in a mutual fund scheme. It is suitable when you have surplus funds and believe market conditions are favorable. Minimum lumpsum investment is typically Rs 5,000. Lumpsum works well for long-term goals when markets are at reasonable valuations.',
            'category': 'Investment Methods',
            'source': 'Standard FAQ'
        },
        {
            'question': 'What is STP (Systematic Transfer Plan)?',
            'answer': 'STP allows automatic transfer of a fixed amount from one mutual fund scheme to another within the same AMC at regular intervals. Commonly used to transfer from debt/liquid funds to equity funds gradually, reducing market timing risk. It combines the safety of debt funds with the growth potential of equity funds.',
            'category': 'Investment Methods',
            'source': 'Standard FAQ'
        },
        {
            'question': 'What is SWP (Systematic Withdrawal Plan)?',
            'answer': 'SWP allows you to withdraw a fixed amount from your mutual fund investment at regular intervals while the remaining investment continues to grow. It provides regular income and is useful for retirees or those needing periodic cash flow. You can choose the withdrawal amount and frequency.',
            'category': 'Investment Methods',
            'source': 'Standard FAQ'
        },

        # Fund Types
        {
            'question': 'What are equity funds?',
            'answer': 'Equity funds invest primarily (at least 65%) in stocks of companies. They offer high growth potential but come with higher risk and volatility. Types include large-cap, mid-cap, small-cap, multi-cap, flexi-cap, sectoral/thematic, ELSS, and focused funds. Suitable for long-term wealth creation with investment horizon of 5+ years.',
            'category': 'Fund Types',
            'source': 'Standard FAQ'
        },
        {
            'question': 'What are debt funds?',
            'answer': 'Debt funds invest in fixed-income securities like government bonds, corporate bonds, treasury bills, and money market instruments. They offer relatively stable returns with lower risk than equity funds. Types include liquid, overnight, short duration, corporate bond, gilt, and dynamic bond funds. Suitable for short to medium-term goals.',
            'category': 'Fund Types',
            'source': 'Standard FAQ'
        },
        {
            'question': 'What are hybrid funds?',
            'answer': 'Hybrid funds invest in a mix of equity and debt instruments to balance risk and return. Types include conservative hybrid (10-25% equity), balanced hybrid (40-60% equity), aggressive hybrid (65-80% equity), dynamic asset allocation, and multi-asset funds. They provide diversification within a single fund.',
            'category': 'Fund Types',
            'source': 'Standard FAQ'
        },
        {
            'question': 'What are index funds?',
            'answer': 'Index funds passively track a specific market index like Nifty 50 or Sensex by investing in the same securities in the same proportion. They aim to replicate index returns with minimal tracking error. Benefits include low expense ratios, transparency, and diversification. Suitable for passive long-term investing.',
            'category': 'Fund Types',
            'source': 'Standard FAQ'
        },
        {
            'question': 'What are ETFs (Exchange Traded Funds)?',
            'answer': 'ETFs are index funds that trade on stock exchanges like regular shares. They track indices, commodities, or baskets of assets. Benefits include real-time trading, lower expense ratios, transparency, and no exit load. You need a demat account to invest in ETFs. Types include equity ETFs, gold ETFs, and bond ETFs.',
            'category': 'Fund Types',
            'source': 'Standard FAQ'
        },
        {
            'question': 'What is ELSS (Equity Linked Savings Scheme)?',
            'answer': 'ELSS is a type of equity mutual fund that qualifies for tax deduction under Section 80C up to Rs 1.5 lakh per year. It has a mandatory 3-year lock-in period, the shortest among 80C instruments. ELSS invests primarily in equities and offers potential for wealth creation along with tax benefits.',
            'category': 'Fund Types',
            'source': 'Standard FAQ'
        },

        # Risk and Returns
        {
            'question': 'What is the riskometer in mutual funds?',
            'answer': 'Riskometer is a 6-level risk classification mandated by SEBI: Low, Low to Moderate, Moderate, Moderately High, High, and Very High. It indicates the level of risk associated with a mutual fund scheme based on factors like asset allocation, market capitalization, credit quality, and duration. Risk levels are reviewed monthly.',
            'category': 'Risk and Returns',
            'source': 'Standard FAQ'
        },
        {
            'question': 'Are mutual fund returns guaranteed?',
            'answer': 'No, mutual fund returns are not guaranteed as they are market-linked investments. Past performance does not guarantee future results. Returns depend on market conditions, fund manager decisions, and economic factors. However, historical data shows that equity funds have generated inflation-beating returns over long periods (7+ years).',
            'category': 'Risk and Returns',
            'source': 'Standard FAQ'
        },
        {
            'question': 'What is the difference between absolute and CAGR returns?',
            'answer': 'Absolute return is the total percentage gain/loss on an investment without considering time. CAGR (Compound Annual Growth Rate) is the annualized return that shows growth rate per year accounting for compounding. For periods over 1 year, CAGR is more meaningful. Example: 50% absolute return over 3 years = 14.47% CAGR.',
            'category': 'Risk and Returns',
            'source': 'Standard FAQ'
        },

        # Taxation
        {
            'question': 'How are equity mutual funds taxed?',
            'answer': 'For equity funds (65%+ in equity): Short-term capital gains (holding period < 12 months) are taxed at 15%. Long-term capital gains (holding period > 12 months) are taxed at 10% on gains exceeding Rs 1 lakh per year. Dividends are added to income and taxed at applicable slab rates.',
            'category': 'Taxation',
            'source': 'Standard FAQ'
        },
        {
            'question': 'How are debt mutual funds taxed?',
            'answer': 'For debt funds (investments made after April 2023): All capital gains, regardless of holding period, are added to income and taxed at applicable slab rates. There is no indexation benefit. TDS of 10% applies if annual gains exceed Rs 5,000. This makes debt funds less tax-efficient than before.',
            'category': 'Taxation',
            'source': 'Standard FAQ'
        },
        {
            'question': 'What are the tax benefits of ELSS?',
            'answer': 'ELSS investments qualify for tax deduction under Section 80C up to Rs 1.5 lakh per year, potentially saving up to Rs 46,800 in taxes (at 30% slab + cess). After the 3-year lock-in, LTCG is taxed at 10% on gains exceeding Rs 1 lakh. ELSS has the shortest lock-in among 80C instruments.',
            'category': 'Taxation',
            'source': 'Standard FAQ'
        },

        # KYC and Account
        {
            'question': 'What documents are required to invest in mutual funds?',
            'answer': 'Required documents: PAN card (mandatory for investments above Rs 50,000), proof of address (Aadhaar, passport, utility bill), photograph, and bank account details. KYC must be completed through a KRA (KYC Registration Agency). Aadhaar-based e-KYC is available for quick verification.',
            'category': 'KYC and Account',
            'source': 'Standard FAQ'
        },
        {
            'question': 'How do I complete KYC for mutual funds?',
            'answer': 'KYC can be completed online (e-KYC using Aadhaar) or offline through AMC/distributor offices. Steps: 1) Fill KYC form, 2) Submit PAN, address proof, photograph, 3) Complete in-person verification if required (for investments above Rs 2 lakh), 4) Get KYC registered with KRA. KYC is one-time and valid across all AMCs.',
            'category': 'KYC and Account',
            'source': 'Standard FAQ'
        },
        {
            'question': 'Can NRIs invest in Indian mutual funds?',
            'answer': 'Yes, NRIs can invest in Indian mutual funds on a repatriable or non-repatriable basis. Requirements: NRE/NRO bank account in India, KYC compliance, FATCA declaration. Some AMCs may have restrictions on NRIs from certain countries (like USA, Canada) due to compliance requirements. Taxation follows India-country DTAA provisions.',
            'category': 'KYC and Account',
            'source': 'Standard FAQ'
        },
        {
            'question': 'What is nomination in mutual funds?',
            'answer': 'Nomination allows you to designate a person who will receive your mutual fund units in case of your death. SEBI has made nomination mandatory for individual investors (or opt-out declaration). Multiple nominees can be registered with percentage allocation. Nomination facilitates easy transmission without legal hassles.',
            'category': 'KYC and Account',
            'source': 'Standard FAQ'
        },

        # Transactions
        {
            'question': 'What is the cut-off time for mutual fund transactions?',
            'answer': 'Cut-off times determine which day NAV applies: Equity/Debt funds - 3:00 PM (same day NAV if amount received before cut-off). Liquid/Overnight funds - 1:30 PM. For purchases, both application and funds must reach AMC before cut-off. For redemptions, only application timing matters.',
            'category': 'Transactions',
            'source': 'Standard FAQ'
        },
        {
            'question': 'How long does it take to receive redemption proceeds?',
            'answer': 'Redemption timelines: Liquid/Overnight funds - T+1 working day. Other debt funds - T+2 working days. Equity funds - T+3 working days. T is the day of redemption request (before cut-off time). Proceeds are credited to registered bank account. Instant redemption available for some liquid funds up to Rs 50,000.',
            'category': 'Transactions',
            'source': 'Standard FAQ'
        },
        {
            'question': 'Can I switch between mutual fund schemes?',
            'answer': 'Yes, you can switch (transfer) from one scheme to another within the same AMC. It involves redemption from source scheme and purchase in target scheme. Switch is treated as redemption for tax purposes, so capital gains tax applies. No exit load if switching after the exit load period.',
            'category': 'Transactions',
            'source': 'Standard FAQ'
        },

        # Regulations
        {
            'question': 'Who regulates mutual funds in India?',
            'answer': 'SEBI (Securities and Exchange Board of India) regulates mutual funds under SEBI (Mutual Funds) Regulations, 1996. SEBI approves AMCs, mandates disclosures, sets expense ratio limits, defines fund categories, and protects investor interests. AMFI is the industry body representing all AMCs.',
            'category': 'Regulations',
            'source': 'Standard FAQ'
        },
        {
            'question': 'What is AMFI?',
            'answer': 'AMFI (Association of Mutual Funds in India) is the industry body representing all Asset Management Companies in India. It sets ethical standards, provides investor education through campaigns like "Mutual Funds Sahi Hai", maintains ARN (distributor registration), publishes NAV data, and promotes best practices in the industry.',
            'category': 'Regulations',
            'source': 'Standard FAQ'
        },
        {
            'question': 'How can I file a complaint against a mutual fund?',
            'answer': 'Steps to file complaint: 1) Contact AMC investor grievance cell first, 2) If unresolved within 30 days, escalate to SEBI through SCORES portal (scores.gov.in), 3) SEBI investigates and facilitates resolution. You can also approach consumer courts or arbitration. Always keep documentation of communications.',
            'category': 'Regulations',
            'source': 'Standard FAQ'
        },

        # Practical Questions
        {
            'question': 'How much should I invest in mutual funds?',
            'answer': 'Investment amount depends on your financial goals, income, expenses, and risk tolerance. General guidelines: Save at least 20-30% of income, maintain 6-month emergency fund in liquid assets, invest surplus in mutual funds based on goals. Start with what you can afford consistently, even Rs 500/month in SIP.',
            'category': 'Practical',
            'source': 'Standard FAQ'
        },
        {
            'question': 'Which mutual fund should I invest in?',
            'answer': 'Fund selection depends on: 1) Investment goal and time horizon, 2) Risk tolerance, 3) Tax situation. General guidance: Short-term (< 3 years) - debt funds; Medium-term (3-5 years) - hybrid funds; Long-term (5+ years) - equity funds. Within each category, look at consistent performance, expense ratio, and fund manager track record.',
            'category': 'Practical',
            'source': 'Standard FAQ'
        },
        {
            'question': 'Should I invest lumpsum or SIP?',
            'answer': 'Both have merits: SIP provides rupee cost averaging, disciplined investing, and reduces timing risk - ideal for regular income earners. Lumpsum can give better returns if markets are at reasonable valuations - ideal for windfall gains. For large amounts, consider investing via STP to reduce timing risk.',
            'category': 'Practical',
            'source': 'Standard FAQ'
        },
        {
            'question': 'When should I redeem my mutual fund investment?',
            'answer': 'Redeem when: 1) You have achieved your financial goal, 2) You need the money for planned expenses, 3) Fund consistently underperforms peers/benchmark for 2-3 years, 4) Your risk profile has changed. Avoid redeeming due to short-term market volatility or panic. Stay invested for long-term goals.',
            'category': 'Practical',
            'source': 'Standard FAQ'
        },
        {
            'question': 'How do I track my mutual fund investments?',
            'answer': 'Track investments through: 1) AMC website/app using folio number, 2) Consolidated Account Statement (CAS) from CAMS/KFintech, 3) MF Central portal (mfcentral.com) for all holdings, 4) Third-party apps like Groww, Kuvera, ET Money. Review portfolio quarterly and rebalance annually if needed.',
            'category': 'Practical',
            'source': 'Standard FAQ'
        },
    ]

    return faqs


def save_to_csv(data: List[Dict], filename: str):
    """Save scraped data to CSV file."""
    if not data:
        print(f"  No data to save to {filename}")
        return

    # Ensure data directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    fieldnames = ['question', 'answer', 'category', 'source']

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"  Saved {len(data)} records to {filename}")


def run():
    """Main function to run the FAQs scraper."""
    print("\n" + "="*60)
    print("MUTUAL FUND FAQs SCRAPER")
    print("="*60)

    all_data = []

    # Get static FAQs (comprehensive and reliable)
    print("\nLoading standard FAQs...")
    static_data = get_static_faqs()
    all_data.extend(static_data)
    print(f"  Loaded {len(static_data)} FAQs")

    # Scrape AMFI FAQs
    print("\nScraping AMFI website...")
    try:
        amfi_data = scrape_amfi_faqs()
        # Avoid duplicates based on question similarity
        existing_questions = {faq['question'].lower()[:50] for faq in all_data}
        new_faqs = [faq for faq in amfi_data if faq['question'].lower()[:50] not in existing_questions]
        all_data.extend(new_faqs)
        print(f"  Added {len(new_faqs)} new FAQs from AMFI")
    except Exception as e:
        print(f"  Failed to scrape AMFI FAQs: {e}")

    # Scrape Groww FAQs
    print("\nScraping Groww website...")
    try:
        groww_data = scrape_groww_faqs()
        existing_questions = {faq['question'].lower()[:50] for faq in all_data}
        new_faqs = [faq for faq in groww_data if faq['question'].lower()[:50] not in existing_questions]
        all_data.extend(new_faqs)
        print(f"  Added {len(new_faqs)} new FAQs from Groww")
    except Exception as e:
        print(f"  Failed to scrape Groww FAQs: {e}")

    # Save to CSV
    print("\nSaving data...")
    save_to_csv(all_data, OUTPUT_FILE)

    print(f"\nTotal FAQs: {len(all_data)}")
    print("="*60)

    return all_data


if __name__ == "__main__":
    run()
