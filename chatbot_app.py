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

# Global variables for loaded data
knowledge_base = {
    'faqs': [],
    'schemes': [],
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
        'schemes': ['data/extracted_schemes.csv', 'data/nippon_schemes.csv'],
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


def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for relevant context."""
    query_lower = query.lower()
    relevant_context = []

    # Search FAQs
    for faq in knowledge_base['faqs']:
        question = faq.get('question', '').lower()
        answer = faq.get('answer', '')
        if any(word in question for word in query_lower.split()):
            relevant_context.append(f"Q: {faq.get('question', '')}\nA: {answer}")

    # Search basics/concepts
    for basic in knowledge_base['basics']:
        topic = basic.get('topic', '').lower()
        content = basic.get('content', '')
        if any(word in topic or word in content.lower() for word in query_lower.split()):
            relevant_context.append(f"Topic: {basic.get('topic', '')}\n{content}")

    # Search schemes
    for scheme in knowledge_base['schemes']:
        name = scheme.get('scheme_name', '').lower()
        if any(word in name for word in query_lower.split()):
            scheme_info = f"Scheme: {scheme.get('scheme_name', '')}\n"
            scheme_info += f"Category: {scheme.get('category', 'N/A')}\n"
            scheme_info += f"NAV: {scheme.get('nav', 'N/A')}\n"
            scheme_info += f"Expense Ratio: {scheme.get('expense_ratio', 'N/A')}\n"
            scheme_info += f"Risk: {scheme.get('riskometer', 'N/A')}\n"
            scheme_info += f"Objective: {scheme.get('scheme_objective', 'N/A')}"
            relevant_context.append(scheme_info)

    # Search guidelines
    for guideline in knowledge_base['guidelines']:
        title = guideline.get('title', '').lower()
        desc = guideline.get('description', '')
        if any(word in title or word in desc.lower() for word in query_lower.split()):
            relevant_context.append(f"Guideline: {guideline.get('title', '')}\n{desc}")

    # Limit context size
    context = "\n\n---\n\n".join(relevant_context[:10])
    return context[:8000] if context else ""


def generate_response(query: str) -> str:
    """Generate a response using Gemini with RAG context."""
    global model

    if not model:
        return "Error: AI model not initialized. Please check your API key."

    # Get relevant context from knowledge base
    context = search_knowledge_base(query)

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
        return response.text
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

    context = search_knowledge_base(query)
    return jsonify({'results': context})


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

if __name__ == '__main__':
    main()
