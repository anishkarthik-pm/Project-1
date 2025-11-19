# Mutual Fund Knowledge Base & RAG Chatbot

A complete solution for scraping, extracting, and querying mutual fund information in India using AI-powered RAG (Retrieval-Augmented Generation).

## Features

- **Web Scrapers**: Collect mutual fund data from AMFI, SEBI, and Nippon India
- **AI Extractor**: Use Google Gemini to intelligently extract structured data from local files
- **RAG Chatbot**: Interactive chat interface that answers questions using your knowledge base
- **Multiple Data Sources**: FAQs, scheme details, SEBI guidelines, and basic concepts

## Project Structure

```
Project-1/
├── chatbot_app.py              # Flask backend for RAG chatbot
├── extract_with_ai.py          # AI-powered data extraction (main entry)
├── process_local_files.py      # Simple file chunking for RAG
├── scrape_all.py               # Run all web scrapers
├── check_models.py             # Check available Gemini models
├── requirements.txt            # Python dependencies
├── static/
│   └── index.html              # Chat interface frontend
├── scrapers/
│   ├── __init__.py
│   ├── mutual_fund_basics.py   # Scrape MF definitions & concepts
│   ├── sebi_scraper.py         # Scrape SEBI guidelines
│   ├── nippon_scraper.py       # Scrape Nippon India MF schemes
│   ├── faqs_scraper.py         # Scrape FAQs
│   ├── local_file_processor.py # Process local files for RAG
│   └── ai_extractor.py         # Gemini-powered extraction
└── data/                       # Output CSV files
    ├── extracted_faqs.csv
    ├── extracted_schemes.csv
    ├── extracted_guidelines.csv
    └── extracted_basics.csv
```

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Project-1
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Google Gemini API Key

Get your API key from: https://aistudio.google.com/app/apikey

**Windows (Command Prompt):**
```cmd
set GOOGLE_API_KEY=your-api-key-here
```

**Windows (PowerShell):**
```powershell
$env:GOOGLE_API_KEY="your-api-key-here"
```

**Linux/Mac:**
```bash
export GOOGLE_API_KEY=your-api-key-here
```

## Usage

### Option 1: Extract Data from Local Files (Recommended)

If you have downloaded mutual fund documents (PDFs, HTML, TXT, DOCX):

```bash
# Place your files in a folder, then run:
python extract_with_ai.py --input "C:\path\to\your\files"

# Or use default path:
python extract_with_ai.py
```

This will:
- Read all supported files
- Use Gemini AI to identify content type
- Extract structured data into proper fields
- Save to CSV files in `data/` directory

### Option 2: Use Web Scrapers

```bash
# Run all scrapers (uses static data + attempts live scraping)
python scrape_all.py

# Run specific scrapers
python scrape_all.py --only basics sebi
python scrape_all.py --only nippon faqs
```

### Option 3: Simple File Chunking

For basic text chunking without AI extraction:

```bash
python process_local_files.py --input "C:\path\to\files" --strategy paragraph
```

## Running the Chatbot

### 1. Ensure Data is Available

Run either the AI extractor or web scrapers first to populate the `data/` directory.

### 2. Start the Server

```bash
python chatbot_app.py
```

### 3. Open in Browser

Navigate to: **http://localhost:5000**

### 4. Start Chatting!

Ask questions like:
- "What is NAV?"
- "How are equity funds taxed?"
- "Explain SIP benefits"
- "What is the expense ratio?"
- "Tell me about ELSS tax benefits"

## Output Files

| File | Description |
|------|-------------|
| `data/extracted_faqs.csv` | Question-answer pairs |
| `data/extracted_schemes.csv` | Mutual fund scheme details |
| `data/extracted_guidelines.csv` | SEBI regulations and circulars |
| `data/extracted_basics.csv` | Definitions and concepts |

## Configuration

### Changing the Gemini Model

Edit `scrapers/ai_extractor.py` line 45:

```python
MODEL_NAME = "gemini-2.0-flash"  # or "gemini-pro-latest"
```

To see available models:
```bash
python check_models.py
```

### Chunking Strategies

For `process_local_files.py`:

| Strategy | Best For |
|----------|----------|
| `fixed` | General purpose, consistent sizes |
| `paragraph` | FAQs, well-formatted text |
| `heading` | Structured documents with sections |

```bash
python process_local_files.py --strategy heading --chunk-size 1500
```

## Supported File Formats

- PDF (`.pdf`)
- HTML (`.html`, `.htm`, `.mhtml`)
- Text (`.txt`, `.md`)
- Word (`.docx`)
- Data (`.json`, `.csv`)

## API Endpoints

The chatbot backend provides these endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve chat interface |
| `/api/chat` | POST | Send message, get AI response |
| `/api/status` | GET | Check API and knowledge base status |
| `/api/search` | POST | Search knowledge base directly |

### Example API Usage

```python
import requests

# Send a chat message
response = requests.post('http://localhost:5000/api/chat',
    json={'message': 'What is NAV?'})
print(response.json()['response'])

# Check status
status = requests.get('http://localhost:5000/api/status').json()
print(f"Total records: {status['knowledge_base']['total']}")
```

## Troubleshooting

### "No API key provided"

Set the `GOOGLE_API_KEY` environment variable before running scripts.

### "Model not found" Error

Run `python check_models.py` to see available models, then update the model name in the script.

### "No data loaded" Warning

Run the AI extractor or web scrapers first:
```bash
python extract_with_ai.py
# or
python scrape_all.py
```

### Web Scraping Returns 403/404

Many websites block automated requests. The scrapers include comprehensive static data as fallback. Use the AI extractor with locally downloaded files for best results.

## Tech Stack

- **Backend**: Python, Flask
- **AI**: Google Gemini API
- **Scraping**: requests, BeautifulSoup4
- **File Processing**: PyPDF2, python-docx
- **Frontend**: HTML, CSS, JavaScript

## License

This project is for educational purposes. Please respect the terms of service of data sources when scraping.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Acknowledgments

- AMFI India for mutual fund education resources
- SEBI for regulatory guidelines
- Nippon India Mutual Fund for scheme information
- Google for the Gemini AI API
