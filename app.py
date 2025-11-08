import os
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv

# --- Load biến môi trường ---
load_dotenv()

app = Flask(__name__)

# --- Cấu hình CORS (hoạt động ổn định trên Render) ---
CORS(
    app,
    resources={r"/*": {"origins": ["https://e-book-for-me.web.app"]}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"]
)

# --- Sau mỗi phản hồi, tự thêm header CORS (đảm bảo không bị chặn OPTIONS) ---
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'https://e-book-for-me.web.app')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

# --- Cấu hình Gemini API ---
try:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("⚠️ GEMINI_API_KEY not found in environment variables.")
    
    genai.configure(api_key=gemini_api_key)
    print("✅ Gemini API key loaded successfully.")

    # Liệt kê các model có thể sử dụng để kiểm tra trên Render log
    print("📋 Available models:")
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            print(" -", m.name)

    # Dùng model mới, tương thích bản SDK hiện tại
    model = genai.GenerativeModel('gemini-flash-latest')

except Exception as e:
    print(f"❌ Error configuring Gemini API: {e}")
    model = None


# --- Hàm sinh phản hồi stream ---
def generate_response_stream(prompt):
    if not model:
        yield "data: [ERROR] Gemini model is not configured.\n\n"
        return

    try:
        chat_session = model.start_chat(history=[])
        response_stream = chat_session.send_message(prompt, stream=True)

        for chunk in response_stream:
            if chunk.text:
                yield f"data: {chunk.text}\n\n"

    except Exception as e:
        print(f"⚠️ Error during generation: {e}")
        yield f"data: [ERROR] Sorry, an error occurred: {str(e)}\n\n"


# --- API chính ---
@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json or {}
        user_message = data.get('message', '')
        conversation_history = data.get('conversation_history', [])
        document_content = data.get('document_content', '')
        dictionary_content = data.get('dictionary_content', '')
        language = data.get('language', 'vi')

        prompt = f"""
You are an AI assistant for an e-learning platform.
Respond in {'Vietnamese' if language == 'vi' else 'English'}.

Conversation history:
{conversation_history}

Document content:
--- DOCUMENT START ---
{document_content}
--- DOCUMENT END ---

Custom dictionary/glossary:
--- DICTIONARY START ---
{dictionary_content}
--- DICTIONARY END ---

User's latest message: "{user_message}"
"""

        return Response(generate_response_stream(prompt), mimetype='text/event-stream')

    except Exception as e:
        print(f"❌ Error in /chat endpoint: {e}")
        return jsonify({"error": "Internal server error occurred."}), 500


# --- Chạy local ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
