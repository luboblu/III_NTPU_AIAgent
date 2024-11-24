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

def preprocess_query(query):
    # Preprocess the user query to remove auxiliary words
    query = query.replace("我想知道", "").replace("請問", "").strip()
    return query

def find_traffic_info(query, file_path):
    # Load the JSON data from the file
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Iterate through each news item to find matches based on the query
    results = []
    for news in data['Newses']:
        if query in news['Title'] or query in news['Description']:
            result = {
                'Location': news['Title'],
                'Description': news['Description'],
                'StartTime': news['StartTime'],
                'EndTime': news['EndTime']
            }
            results.append(result)

    # Return the results or a message if no matches are found
    if results:
        return results
    else:
        return "No traffic information found for the given query."

# Generate traffic response using LLaMA
def generate_response_with_llama(context):
    prompt = f"""
你是一個交通助手，專門負責台灣地區的交通事件回報。以下是一些關於交通事件的資料：

{context}

請你根據這些資料，使用繁體中文生成一個清晰且準確的回答，並確保所有提及的地點都是台灣的正確位置。你需要特別注意：
1. 回答中使用的地點應該對應到正確的縣市和區域。
2. 所有內容應該以繁體中文呈現，不要使用簡體中文或英文。
5. 請直接將資料呈現不用講多餘的文字
6. 每次回答開頭都以"以下為您所需的交通資訊"
7. 請用羅馬數字列點回答並格式保持一致
8. 請把標題都列出來

請生成這些資料的完整回應。
"""
    
    # Use ollama to generate the response
    response = ollama.generate(model="llama3.2:3b", prompt=prompt)
    
    # Check if the response contains the 'response' key and return the output
    if 'response' in response:
        return response['response'].strip()
    else:
        return "No response generated."

# Webhook route for LINE Bot
@app.route("/callback", methods=['POST'])
def callback():
    # Get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # Get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # Handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = preprocess_query(event.message.text)

    # Search for traffic information in the JSON data
    traffic_info = find_traffic_info(user_message, file_path)

    if isinstance(traffic_info, str):
        response_text = traffic_info
    else:
        # Prepare context for LLaMA model
        context = "\n".join([
            f"地點: {info['Location']}\n描述: {info['Description']}\n開始時間: {info['StartTime']}\n結束時間: {info['EndTime']}" 
            for info in traffic_info
        ])
        response_text = generate_response_with_llama(context)

    # Reply to the user with the generated response
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

