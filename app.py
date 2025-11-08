import os
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv

# --- Load biến môi trường ---
load_dotenv()

app = Flask(__name__)

# --- Cấu hình CORS (Phiên bản đơn giản hóa) ---
# Cấu hình này đã đủ cho Render và test local
CORS(
    app,
    origins=["https://e-book-for-me.web.app", "http://localhost:3000", "http://127.0.0.1:5500"],
    supports_credentials=True
)

# --- Cấu hình Gemini API ---
try:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("⚠️ GEMINI_API_KEY not found in environment variables.")
    
    genai.configure(api_key=gemini_api_key)
    print("✅ Gemini API key loaded successfully.")

    # --- SỬA LỖI TÊN MODEL ---
    # Tên model này được lấy từ log của bạn
    model = genai.GenerativeModel('gemini-flash-latest')
    print(f"✅ Model '{model.model_name}' loaded successfully.")

    # (Đã ẩn đi) Đoạn code liệt kê model, bạn có thể bỏ comment nếu cần debug
    # print("📋 Available models:")
    # for m in genai.list_models():
    #     if "generateContent" in m.supported_generation_methods:
    #         print(" -", m.name)

except Exception as e:
    print(f"❌ Error configuring Gemini API: {e}")
    model = None


# --- SỬA LỖI KHỞI ĐỘNG CỦA RENDER ---
# Thêm route trang chủ (/) để Render kiểm tra sức khỏe (Health Check)
# Nó sẽ trả lời 200 OK, báo cho Render biết là "Tôi vẫn sống!"
@app.route('/')
def health_check():
    return "Backend is running and healthy!", 200


# --- Hàm sinh phản hồi stream ---
def generate_response_stream(prompt):
    if not model:
        print("❌ generate_response_stream failed: Model is None.")
        yield "data: [ERROR] Lỗi máy chủ: Model AI chưa được cấu hình.\n\n"
        return

    try:
        chat_session = model.start_chat(history=[])
        response_stream = chat_session.send_message(prompt, stream=True)

        for chunk in response_stream:
            if chunk.text:
                # Mã hóa lại văn bản để tránh lỗi hiển thị ký tự
                text_data = chunk.text.encode('utf-8').decode('utf-8')
                yield f"data: {text_data}\n\n"

    except Exception as e:
        print(f"⚠️ Error during generation: {e}")
        yield f"data: [ERROR] Xin lỗi, có lỗi xảy ra từ AI: {str(e)}\n\n"


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
Bạn là một trợ lý AI cho nền tảng e-learning.
Hãy trả lời bằng {'Tiếng Việt' if language == 'vi' else 'English'}.

Lịch sử trò chuyện (để tham khảo):
{conversation_history}

Nội dung tài liệu người dùng đang xem:
--- TÀI LIỆU ---
{document_content}
--- KẾT THÚC TÀI LIỆU ---

Từ điển/Thuật ngữ tùy chỉnh:
--- TỪ ĐIỂN ---
{dictionary_content}
--- KẾT THÚC TỪ ĐIỂN ---

Tin nhắn mới nhất của người dùng: "{user_message}"
"""
        # Trả về stream data
        return Response(generate_response_stream(prompt), mimetype='text/event-stream')

    except Exception as e:
        print(f"❌ Error in /chat endpoint: {e}")
        return jsonify({"error": "Lỗi máy chủ nội bộ."}), 500


# --- Chạy local (Render sẽ không dùng khối này) ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)