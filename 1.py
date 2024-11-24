from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import ollama
import os
import json

# Initialize Flask app
app = Flask(__name__)

# Initialize LINE bot and Webhook handler
line_bot_api = LineBotApi('KN80EFH9I1mPuRF+6iEvjw9ncCckrMzdADu6AipHmT2eZJkCov+Qjt8JvSc2HeNEmOfg/UZthe2zsxihgT6FcdB5HI3ruEG7stOqqatnp58k79wPhTlqoA41LDe5yAoYQAiDoMzD5XiR/Vgh5uI10gdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('1ff8185e27c640b535e2a214dbd1488f')

# Load the JSON data
file_path = 'C:\\Users\\盧bob\\Desktop\\AI Agent\\sanxia_100_news_format.json'
with open(file_path, 'r', encoding='utf-8') as file:
    traffic_data = json.load(file)

def format_traffic_data(data):
    if data:
        result = "當前地區的交通事件如下：\n"
        for item in data:
            title = item.get('Title', '未知事件')
            description = item.get('Description', '無描述')
            start_time = item.get('StartTime', '未知開始時間')
            end_time = item.get('EndTime', '未知結束時間')
            result += f"- 事件: {title}\n  描述: {description}\n  開始時間: {start_time}\n  結束時間: {end_time}\n\n"
        return result
    else:
        return "目前該地區沒有查詢到交通事件。"

def split_text_into_chunks(text, chunksize, overlap):
    """Split text into chunks with specified chunksize and overlap."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunksize
        chunks.append(text[start:end])
        start = end - overlap  # Move start back by the overlap amount
    return chunks

def find_relevant_traffic_info(user_message, traffic_data, chunksize=50, overlap=10):
    """Find relevant traffic information by keyword matching using chunks of the user message."""
    results = []
    # Split the user message into chunks
    chunks = split_text_into_chunks(user_message, chunksize, overlap)

    for chunk in chunks:
        for news in traffic_data.get('Newses', []):
            if chunk in news['Title'] or chunk in news['Description']:
                results.append(news)
                break  # Stop after finding a match for this chunk
    return results

def generate_response_with_llama(user_message, relevant_info, max_chars=700):
    """Generate a response using LLaMA model with a character limit."""
    if not relevant_info:
        return "抱歉，我無法根據您的查詢找到相關的交通事件資訊。"

    formatted_data = format_traffic_data(relevant_info)

    prompt = f"""
你是一個交通助手，專門負責台灣地區的交通事件回報。以下是一些關於交通事件的資料：

{formatted_data}

使用者的提問是："{user_message}"
請你根據使用者的提問和提供的資料，使用繁體中文生成一個清晰且準確的回答，並確保所有提及的地點都是台灣的正確位置。你需要特別注意：
1. 回答中使用的地點應該對應到正確的縣市和區域。
2. 所有內容應該以繁體中文呈現，不要使用簡體中文或英文。
3. 請按照提供的資料格式進行生成。
4. 每次回答開頭都以"以下為您所需的交通資訊"開始。
5. 請用羅馬數字列點回答並格式保持一致。
6. 請將標題都列出來。

請生成這些資料的完整回應，且限制回應長度在 {max_chars} 個字以內。
"""

    response = ollama.generate(model="llama3.2:3b", prompt=prompt)

    if 'response' in response:
        return response['response'].strip()[:max_chars]
    else:
        return "抱歉，我無法根據您的查詢找到相關的交通事件資訊。"

# Webhook route for LINE Bot
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    relevant_info = find_relevant_traffic_info(user_message, traffic_data)
    response_text = generate_response_with_llama(user_message, relevant_info)

    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response_text)
        )
    except LineBotApiError as e:
        app.logger.error(f"Error: {e}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
