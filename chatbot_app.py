#!/usr/bin/env python3
"""
RAG Chatbot Backend
Flask-based API that answers questions about mutual funds using extracted data.
"""

import os
import csv
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Try to import Google Generative AI
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    print("Warning: google-generativeai not installed")

app = Flask(__name__, static_folder='static')
CORS(app)

# Configuration
MODEL_NAME = "gemini-2.0-flash"
DATA_DIR = "data"
CHAT_HISTORY_FILE = "data/chat_history.json"
RATINGS_FILE = "data/ratings.json"

# Fallback sample data for demonstration
SAMPLE_FUNDS = [
    {'scheme_name': 'Nippon India Large Cap Fund', 'category': 'Large Cap', 'nav': '52.30', 'expense_ratio': '1.98%', 'riskometer': 'Moderately High'},
    {'scheme_name': 'Nippon India Small Cap Fund', 'category': 'Small Cap', 'nav': '98.75', 'expense_ratio': '2.10%', 'riskometer': 'Very High'},
    {'scheme_name': 'Nippon India Flexi Cap Fund', 'category': 'Flexi Cap', 'nav': '65.20', 'expense_ratio': '1.85%', 'riskometer': 'Very High'},
    {'scheme_name': 'Nippon India Multi Cap Fund', 'category': 'Multi Cap', 'nav': '145.80', 'expense_ratio': '1.95%', 'riskometer': 'Very High'},
    {'scheme_name': 'Nippon India Balanced Advantage Fund', 'category': 'Hybrid', 'nav': '42.15', 'expense_ratio': '1.05%', 'riskometer': 'Moderate'},
    {'scheme_name': 'Nippon India Liquid Fund', 'category': 'Liquid', 'nav': '5180.25', 'expense_ratio': '0.25%', 'riskometer': 'Low'},
    {'scheme_name': 'Nippon India Tax Saver (ELSS) Fund', 'category': 'ELSS', 'nav': '76.45', 'expense_ratio': '1.80%', 'riskometer': 'Very High'},
    {'scheme_name': 'Nippon India Index Fund - Sensex Plan', 'category': 'Index', 'nav': '68.90', 'expense_ratio': '0.75%', 'riskometer': 'Very High'},
]

SAMPLE_FAQS = [
    {'question': 'What is a mutual fund?', 'answer': 'A mutual fund is a professionally managed investment vehicle that pools money from multiple investors to invest in securities like stocks, bonds, and other assets.', 'category': 'Basics', 'source': 'AMFI'},
    {'question': 'What is NAV?', 'answer': 'Net Asset Value (NAV) is the per-unit market value of a mutual fund scheme. It is calculated by dividing the total value of all assets in the portfolio minus liabilities by the number of outstanding units.', 'category': 'Basics', 'source': 'SEBI'},
    {'question': 'What is SIP?', 'answer': 'Systematic Investment Plan (SIP) is a method of investing a fixed sum regularly in a mutual fund scheme. It helps in rupee cost averaging and builds investment discipline.', 'category': 'Investment', 'source': 'AMFI'},
    {'question': 'What is expense ratio?', 'answer': 'Expense ratio is the annual fee charged by mutual funds to manage your money. It includes management fees, administrative costs, and other operational expenses, expressed as a percentage of assets.', 'category': 'Costs', 'source': 'SEBI'},
    {'question': 'What are ELSS funds?', 'answer': 'Equity Linked Savings Scheme (ELSS) are tax-saving mutual funds with a lock-in period of 3 years. Investments up to ₹1.5 lakh per year qualify for tax deduction under Section 80C.', 'category': 'Tax', 'source': 'Income Tax Act'},
    {'question': 'What is the difference between growth and dividend options?', 'answer': 'In growth option, profits are reinvested and reflected in NAV appreciation. In dividend option, profits are distributed periodically to investors, reducing the NAV accordingly.', 'category': 'Investment', 'source': 'AMFI'},
    {'question': 'What is exit load?', 'answer': 'Exit load is a fee charged when you redeem your mutual fund units before a specified period. It discourages early withdrawals and is typically 1% if redeemed within one year.', 'category': 'Costs', 'source': 'SEBI'},
    {'question': 'How are mutual funds taxed?', 'answer': 'Equity funds: LTCG (>1 year) taxed at 10% above ₹1 lakh, STCG at 15%. Debt funds: LTCG (>3 years) at 20% with indexation, STCG at slab rates.', 'category': 'Tax', 'source': 'Income Tax Act'},
]

# Global variables for loaded data
knowledge_base = {
    'faqs': SAMPLE_FAQS.copy(),
    'schemes': SAMPLE_FUNDS.copy(),
    'guidelines': [],
    'basics': []
}
model = None
chat_history = []  # Store chat sessions
ratings = []  # Store conversation ratings


def load_csv_data(filepath: str) -> list:
    """Load data from a CSV file."""
    data = []
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                data = list(reader)
            print(f"  Loaded {len(data)} records from {filepath}")
        except Exception as e:
            print(f"  Error loading {filepath}: {e}")
    return data


def load_knowledge_base():
    """Load all extracted data into memory."""
    global knowledge_base

    print("\nLoading knowledge base...")

    # Try extracted files first (AI-processed), then fall back to scraped files
    files_to_load = {
        'faqs': ['data/extracted_faqs.csv', 'data/faqs.csv'],
        'schemes': ['data/comprehensive_schemes.csv', 'data/extracted_schemes.csv', 'data/nippon_schemes.csv'],
        'guidelines': ['data/extracted_guidelines.csv', 'data/sebi_guidelines.csv'],
        'basics': ['data/extracted_basics.csv', 'data/mutual_fund_basics.csv']
    }

    for key, file_options in files_to_load.items():
        for filepath in file_options:
            data = load_csv_data(filepath)
            if data:
                knowledge_base[key] = data
                break

    total = sum(len(v) for v in knowledge_base.values())
    print(f"\nTotal knowledge base records: {total}")
    return total > 0


def initialize_gemini():
    """Initialize the Gemini model."""
    global model

    api_key = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')

    if not api_key:
        print("Warning: No API key found. Set GOOGLE_API_KEY environment variable.")
        return False

    if not HAS_GEMINI:
        print("Warning: google-generativeai not installed")
        return False

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(MODEL_NAME)
        print(f"Gemini model initialized: {MODEL_NAME}")
        return True
    except Exception as e:
        print(f"Error initializing Gemini: {e}")
        return False


def search_knowledge_base(query: str) -> tuple:
    """Search the knowledge base for relevant context and return sources."""
    query_lower = query.lower()
    relevant_context = []
    sources = []

    # Search FAQs
    for faq in knowledge_base['faqs']:
        question = faq.get('question', '').lower()
        answer = faq.get('answer', '')
        if any(word in question for word in query_lower.split()):
            relevant_context.append(f"Q: {faq.get('question', '')}\nA: {answer}")
            source = faq.get('source', faq.get('category', 'Knowledge Base'))
            if source not in sources:
                sources.append(source)

    # Search basics/concepts
    for basic in knowledge_base['basics']:
        topic = basic.get('topic', '').lower()
        content = basic.get('content', '')
        if any(word in topic or word in content.lower() for word in query_lower.split()):
            relevant_context.append(f"Topic: {basic.get('topic', '')}\n{content}")
            source = basic.get('source', 'AMFI Knowledge Center')
            if source not in sources:
                sources.append(source)

    # Search schemes
    for scheme in knowledge_base['schemes']:
        name = scheme.get('scheme_name', '').lower()
        category = scheme.get('category', '').lower()
        fund_manager = scheme.get('fund_manager', '').lower()
        amc = scheme.get('amc', '').lower()

        # Check if query matches scheme name, category, fund manager, or AMC
        if any(word in name or word in category or word in fund_manager or word in amc for word in query_lower.split()):
            scheme_info = f"Scheme: {scheme.get('scheme_name', '')}\n"
            scheme_info += f"AMC: {scheme.get('amc', 'N/A')}\n"
            scheme_info += f"Category: {scheme.get('category', 'N/A')}\n"
            scheme_info += f"NAV: {scheme.get('nav', 'N/A')} (as on {scheme.get('nav_date', 'N/A')})\n"

            # Add fund manager if available
            if scheme.get('fund_manager'):
                scheme_info += f"Fund Manager: {scheme.get('fund_manager')}\n"

            # Add inception date and AUM if available
            if scheme.get('inception_date'):
                scheme_info += f"Inception Date: {scheme.get('inception_date')}\n"
            if scheme.get('aum'):
                scheme_info += f"AUM: {scheme.get('aum')}\n"

            # Add expense ratio and exit load
            if scheme.get('expense_ratio'):
                scheme_info += f"Expense Ratio: {scheme.get('expense_ratio')}\n"
            if scheme.get('exit_load'):
                scheme_info += f"Exit Load: {scheme.get('exit_load')}\n"

            # Add returns if available
            if scheme.get('returns_1y') or scheme.get('returns_3y') or scheme.get('returns_5y'):
                scheme_info += f"Returns: "
                returns_parts = []
                if scheme.get('returns_1y'):
                    returns_parts.append(f"1Y: {scheme.get('returns_1y')}")
                if scheme.get('returns_3y'):
                    returns_parts.append(f"3Y: {scheme.get('returns_3y')}")
                if scheme.get('returns_5y'):
                    returns_parts.append(f"5Y: {scheme.get('returns_5y')}")
                scheme_info += ", ".join(returns_parts) + "\n"

            # Add sector allocation if available
            if scheme.get('sector_allocation'):
                scheme_info += f"Sector Allocation: {scheme.get('sector_allocation')}\n"

            # Add top holdings if available
            if scheme.get('top_holdings'):
                scheme_info += f"Top Holdings: {scheme.get('top_holdings')}\n"

            # Add risk level if available
            if scheme.get('risk_level'):
                scheme_info += f"Risk Level: {scheme.get('risk_level')}\n"

            relevant_context.append(scheme_info)

            # Add source attribution
            if scheme.get('amc'):
                source = scheme.get('amc')
                if source not in sources:
                    sources.append(source)
            elif 'Nippon India' in scheme.get('scheme_name', ''):
                if 'Nippon India Mutual Fund' not in sources:
                    sources.append('Nippon India Mutual Fund')

    # Search guidelines
    for guideline in knowledge_base['guidelines']:
        title = guideline.get('title', '').lower()
        desc = guideline.get('description', '')
        if any(word in title or word in desc.lower() for word in query_lower.split()):
            relevant_context.append(f"Guideline: {guideline.get('title', '')}\n{desc}")
            if 'SEBI' not in sources:
                sources.append('SEBI Guidelines')

    # Limit context size
    context = "\n\n---\n\n".join(relevant_context[:10])
    return (context[:8000] if context else "", sources)


def generate_response(query: str) -> str:
    """Generate a response using Gemini with RAG context."""
    global model

    if not model:
        return "Error: AI model not initialized. Please check your API key."

    # Get relevant context from knowledge base
    context, sources = search_knowledge_base(query)

    # Create prompt with context
    if context:
        prompt = f"""You are a helpful mutual fund advisor chatbot. Answer the user's question based on the following knowledge base context.

KNOWLEDGE BASE CONTEXT:
{context}

USER QUESTION: {query}

Instructions:
- Answer based on the provided context
- Be accurate and helpful
- If the context doesn't contain relevant information, say so but try to provide general guidance
- Keep responses concise but informative
- Use bullet points for lists
- Mention specific scheme names, numbers, or percentages when available
- Do NOT include source citations in your response - they will be added automatically

RESPONSE:"""
    else:
        prompt = f"""You are a helpful mutual fund advisor chatbot. Answer the following question about mutual funds in India.

USER QUESTION: {query}

Instructions:
- Provide accurate information about Indian mutual funds
- Be helpful and informative
- Keep responses concise
- Mention that this is general information and users should consult a financial advisor for personalized advice

RESPONSE:"""

    try:
        response = model.generate_content(prompt)
        answer = response.text

        # Add source citations if sources were found
        if sources:
            answer += "\n\n---\n📚 **Sources:** " + ", ".join(sources)

        return answer
    except Exception as e:
        return f"Error generating response: {str(e)}"


# API Routes
@app.route('/')
def index():
    """Serve the chat interface."""
    return send_from_directory('static', 'index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages."""
    data = request.json
    query = data.get('message', '')

    if not query:
        return jsonify({'error': 'No message provided'}), 400

    response = generate_response(query)
    return jsonify({'response': response})


@app.route('/api/status', methods=['GET'])
def status():
    """Check API status and knowledge base stats."""
    stats = {
        'status': 'ok',
        'model_initialized': model is not None,
        'knowledge_base': {
            'faqs': len(knowledge_base['faqs']),
            'schemes': len(knowledge_base['schemes']),
            'guidelines': len(knowledge_base['guidelines']),
            'basics': len(knowledge_base['basics']),
            'total': sum(len(v) for v in knowledge_base.values())
        }
    }
    return jsonify(stats)


@app.route('/api/search', methods=['POST'])
def search():
    """Search the knowledge base."""
    data = request.json
    query = data.get('query', '')

    if not query:
        return jsonify({'error': 'No query provided'}), 400

    context, sources = search_knowledge_base(query)
    return jsonify({'results': context, 'sources': sources})


@app.route('/api/funds', methods=['GET'])
def get_funds():
    """Get list of all fund names in the knowledge base."""
    fund_names = []
    for scheme in knowledge_base['schemes']:
        name = scheme.get('scheme_name', '')
        category = scheme.get('category', 'N/A')
        if name:
            fund_names.append({
                'name': name,
                'category': category
            })
    return jsonify({'funds': fund_names, 'total': len(fund_names)})


@app.route('/api/faqs', methods=['GET'])
def get_faqs():
    """Get list of FAQs with their categories."""
    faqs_list = []
    for faq in knowledge_base['faqs']:
        faqs_list.append({
            'question': faq.get('question', ''),
            'answer': faq.get('answer', '')[:200] + '...' if len(faq.get('answer', '')) > 200 else faq.get('answer', ''),
            'category': faq.get('category', 'General'),
            'source': faq.get('source_file', faq.get('source', 'Knowledge Base'))
        })
    return jsonify({'faqs': faqs_list, 'total': len(faqs_list)})


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get chat history."""
    return jsonify({'history': chat_history})


@app.route('/api/history', methods=['POST'])
def save_chat():
    """Save a chat session to history."""
    global chat_history
    data = request.json

    session = {
        'id': str(uuid.uuid4()),
        'title': data.get('title', 'New Chat'),
        'messages': data.get('messages', []),
        'timestamp': datetime.now().isoformat(),
        'rating': data.get('rating', None)
    }

    chat_history.insert(0, session)  # Add to beginning

    # Keep only last 50 sessions
    chat_history = chat_history[:50]

    # Save to file
    try:
        os.makedirs(os.path.dirname(CHAT_HISTORY_FILE), exist_ok=True)
        with open(CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(chat_history, f, indent=2)
    except Exception as e:
        print(f"Error saving chat history: {e}")

    return jsonify({'success': True, 'session_id': session['id']})


@app.route('/api/history/<session_id>', methods=['DELETE'])
def delete_chat(session_id):
    """Delete a chat session from history."""
    global chat_history
    chat_history = [s for s in chat_history if s['id'] != session_id]

    # Save to file
    try:
        with open(CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(chat_history, f, indent=2)
    except Exception as e:
        print(f"Error saving chat history: {e}")

    return jsonify({'success': True})


@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    """Clear all chat history."""
    global chat_history
    chat_history = []

    # Save to file
    try:
        with open(CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(chat_history, f, indent=2)
    except Exception as e:
        print(f"Error saving chat history: {e}")

    return jsonify({'success': True})


@app.route('/api/rate', methods=['POST'])
def rate_conversation():
    """Rate a conversation."""
    global ratings
    data = request.json

    rating_entry = {
        'id': str(uuid.uuid4()),
        'session_id': data.get('session_id', ''),
        'rating': data.get('rating', 0),  # 1-5 stars
        'feedback': data.get('feedback', ''),
        'timestamp': datetime.now().isoformat()
    }

    ratings.append(rating_entry)

    # Update session rating if exists
    for session in chat_history:
        if session['id'] == data.get('session_id'):
            session['rating'] = data.get('rating')
            break

    # Save ratings to file
    try:
        os.makedirs(os.path.dirname(RATINGS_FILE), exist_ok=True)
        with open(RATINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(ratings, f, indent=2)
    except Exception as e:
        print(f"Error saving ratings: {e}")

    return jsonify({'success': True, 'rating_id': rating_entry['id']})


@app.route('/api/ratings', methods=['GET'])
def get_ratings():
    """Get all ratings."""
    avg_rating = sum(r['rating'] for r in ratings) / len(ratings) if ratings else 0
    return jsonify({
        'ratings': ratings,
        'total': len(ratings),
        'average': round(avg_rating, 2)
    })


def load_chat_history():
    """Load chat history from file."""
    global chat_history
    if os.path.exists(CHAT_HISTORY_FILE):
        try:
            with open(CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                chat_history = json.load(f)
            print(f"  Loaded {len(chat_history)} chat sessions")
        except Exception as e:
            print(f"  Error loading chat history: {e}")
            chat_history = []


def load_ratings():
    """Load ratings from file."""
    global ratings
    if os.path.exists(RATINGS_FILE):
        try:
            with open(RATINGS_FILE, 'r', encoding='utf-8') as f:
                ratings = json.load(f)
            print(f"  Loaded {len(ratings)} ratings")
        except Exception as e:
            print(f"  Error loading ratings: {e}")
            ratings = []


def main():
    """Main function to run the chatbot."""
    print("\n" + "="*60)
    print("MUTUAL FUND RAG CHATBOT")
    print("="*60)

    # Load knowledge base
    if not load_knowledge_base():
        print("\nWarning: No data loaded. Run extract_with_ai.py first.")

    # Initialize Gemini
    if not initialize_gemini():
        print("\nWarning: Gemini not initialized. Chatbot will have limited functionality.")

    # Load chat history
    load_chat_history()

    # Load ratings
    load_ratings()

    # Get port from environment variable (for Railway/Heroku deployment)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'

    print("\n" + "="*60)
    print("Starting server...")
    print(f"Open http://localhost:{port} in your browser")
    print("="*60 + "\n")

    # Run Flask app
    app.run(host='0.0.0.0', port=port, debug=debug)


# Initialize on module load for serverless environments (Vercel)
load_knowledge_base()
initialize_gemini()
load_chat_history()
load_ratings()

if __name__ == '__main__':
    main()
