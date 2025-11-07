import os
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv

# Tải các biến môi trường từ tệp .env
load_dotenv()

app = Flask(__name__)

# --- ĐÂY LÀ PHẦN SỬA LỖI CORS QUAN TRỌNG ---
# Dòng này cho phép trang web frontend của bạn được quyền gọi tới API /chat
CORS(app, resources={r"/chat": {"origins": "https://e-book-for-me.web.app"}})
# ---------------------------------------------

# Cấu hình API của Google Gemini
try:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-1.5-flash') # Hoặc 'gemini-1.5-pro'
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    model = None

def generate_response_stream(prompt):
    """Hàm tạo phản hồi dưới dạng stream."""
    if not model:
        yield "data: [ERROR] Gemini model is not configured.\n\n"
        return

    try:
        # Tạo một cuộc trò chuyện mới để có context
        chat_session = model.start_chat(history=[])
        response_stream = chat_session.send_message(prompt, stream=True)

        for chunk in response_stream:
            # Gửi từng phần của phản hồi về cho frontend
            # Định dạng Server-Sent Events (SSE) yêu cầu "data: " ở đầu và "\n\n" ở cuối
            yield f"data: {chunk.text}\n\n"

    except Exception as e:
        print(f"Error during generation: {e}")
        yield f"data: [ERROR] Sorry, an error occurred: {str(e)}\n\n"

@app.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        # Xử lý yêu cầu preflight của CORS
        return _build_cors_preflight_response()

    try:
        data = request.json
        user_message = data.get('message', '')
        conversation_history = data.get('conversation_history', [])
        document_content = data.get('document_content', '')
        dictionary_content = data.get('dictionary_content', '')
        language = data.get('language', 'vi')
        
        # Xây dựng một prompt hoàn chỉnh cho AI
        prompt = f"""You are an AI assistant for an e-learning platform. Your user is currently studying a document.
        Your primary language for response should be: {'Vietnamese' if language == 'vi' else 'English'}.

        Here is the user's conversation history (for context):
        {conversation_history}

        Here is the content of the document the user is viewing:
        --- DOCUMENT START ---
        {document_content}
        --- DOCUMENT END ---

        Here is a custom dictionary/glossary provided by the user:
        --- DICTIONARY START ---
        {dictionary_content}
        --- DICTIONARY END ---

        Based on all the information above, please respond to the user's latest message: "{user_message}"
        """

        # Trả về một Response object với generator function
        return Response(generate_response_stream(prompt), mimetype='text/event-stream')

    except Exception as e:
        print(f"Error in /chat endpoint: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "https://e-book-for-me.web.app")
    response.headers.add('Access-Control-Allow-Headers', "*")
    response.headers.add('Access-Control-Allow-Methods', "*")
    return response

if __name__ == '__main__':
    # Chạy server ở chế độ debug trên máy tính
    app.run(host='0.0.0.0', port=5000, debug=True)