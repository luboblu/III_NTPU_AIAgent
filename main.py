import json
import torch
import torch.nn.functional as F
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.v3.messaging import MessagingApi, PushMessageRequest
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, util
import os
from langchain.text_splitter import TokenTextSplitter
import ollama
from linebot.exceptions import InvalidSignatureError

app = Flask(__name__)
load_dotenv()

# Initialize LINE bot and Webhook handler
line_bot_api = LineBotApi('KN80EFH9I1mPuRF+6iEvjw9ncCckrMzdADu6AipHmT2eZJkCov+Qjt8JvSc2HeNEmOfg/UZthe2zsxihgT6FcdB5HI3ruEG7stOqqatnp58k79wPhTlqoA41LDe5yAoYQAiDoMzD5XiR/Vgh5uI10gdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('1ff8185e27c640b535e2a214dbd1488f')
messaging_api = MessagingApi('KN80EFH9I1mPuRF+6iEvjw9ncCckrMzdADu6AipHmT2eZJkCov+Qjt8JvSc2HeNEmOfg/UZthe2zsxihgT6FcdB5HI3ruEG7stOqqatnp58k79wPhTlqoA41LDe5yAoYQAiDoMzD5XiR/Vgh5uI10gdB04t89/1O/w1cDnyilFU=')

# Initialize SentenceTransformer model
embed_model = SentenceTransformer('mixedbread-ai/mxbai-embed-large-v1')


# Load traffic data from JSON file
def load_traffic_data(json_file_path):
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading JSON data: {str(e)}")
        return None

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    print(f"User message: {user_message}")

    try:
        # Step 1: Use RAG approach with embed model to check if message is traffic-related
        if is_traffic_related_rag(user_message):
            print("Message is traffic-related, proceeding to search JSON.")
            # Step 2: Use LLAMA to fetch relevant information from JSON
            traffic_data = load_traffic_data(r"C:\\Users\\盧bob\\Desktop\\AI Agent\\sanxia_100_news_format.json")
            if traffic_data:
                relevant_info = search_traffic_data_llama(traffic_data, user_message)
                print(f"Relevant info found: {relevant_info}")
                
                response = generate_response_with_llama(relevant_info)
                print(f"Generated response: {response}")
                
                # Step 3: Adjust response with TokenTextSplitter
                response_chunks = chunk_text_with_overlap(response)
                final_response = '\n'.join(response_chunks)

                # Check and truncate if response exceeds 5000 characters
                if len(final_response) > 5000:
                    final_response = final_response[:5000] + '\n... (內容已截斷)'

                line_bot_api.push_message(
                    event.source.user_id,
                    TextSendMessage(text=final_response)
                )
            else:
                print("No traffic data available.")
                line_bot_api.push_message(
                    event.source.user_id,
                    TextSendMessage(text="No traffic data available.")
                )
        else:
            # Generate a social response
            response = generate_social_response(user_message)
            print(f"Generated social response: {response}")
            if len(response) > 5000:
                response = response[:5000] + '\n... (內容已截斷)'
            line_bot_api.push_message(
                event.source.user_id,
                TextSendMessage(text=response)
            )

    except Exception as e:
        print(f"Error: {str(e)}")
        line_bot_api.push_message(
            event.source.user_id,
            TextSendMessage(text="Unable to generate response.")
        )

# Helper function to check if the message is traffic-related using RAG approach
def is_traffic_related_rag(user_message):
    traffic_queries = [
        "交通狀況", "車禍", "道路施工", "路面狀況", "交通擁堵", "事故", "封路"
    ]
    user_embedding = embed_model.encode(user_message, convert_to_tensor=True)
    traffic_embeddings = embed_model.encode(traffic_queries, convert_to_tensor=True)
    similarity_scores = util.pytorch_cos_sim(user_embedding, traffic_embeddings)
    max_score = similarity_scores.max().item()
    print(f"Max similarity score for traffic check: {max_score}")
    return max_score > 0.5

# Use LLAMA to find relevant information in the traffic data
def search_traffic_data_llama(data, query):
    context = json.dumps(data, ensure_ascii=False)
    prompt = f"以下是一些交通事件的資料：\n\n{context}\n\n請根據這些資料回答與下列問題相關的資訊：\n{query}"  
    response = ollama.generate(model="llama3.2:3b", prompt=prompt)
    return response['response'].strip()

# Generate traffic response using LLaMA
def generate_response_with_llama(context):
    prompt = f"""
你是一個交通助手，專門負責台灣地區的交通事件回報。以下是一些關於交通事件的資料：

{context}

請你根據這些資料，使用繁體中文生成一個清晰且準確的回答，並確保所有提及的地點都是台灣的正確位置。你需要特別注意：
1. 回答中使用的地點應該對應到正確的縣市和區域。
2. 所有內容應該以繁體中文呈現，不要使用簡體中文或英文。
3. 針對提到的交通事件，提供詳細但簡明的資訊，包含事件的時間和位置。

請生成這些資料的完整回應。
"""
    response = ollama.generate(model="llama3.2:3b", prompt=prompt)
    if 'response' in response:
        return response['response'].strip()
    else:
        return "No response generated."

# Token chunking with TokenTextSplitter from LangChain
def chunk_text_with_overlap(text, chunk_size=800, chunk_overlap=200):
    text_splitter = TokenTextSplitter(
        encoding_name="cl100k_base",  
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = text_splitter.split_text(text)
    return chunks

def format_traffic_data(data):
    if data:
        result = "當前地區的交通事件如下：\n"
        for item in data.get('Newses', []):
            title = item.get('Title', '未知事件')
            description = item.get('Description', '無描述')
            publish_time = item.get('PublishTime', '未知發布時間')
            result += f"- 事件: {title}\n  描述: {description}\n  發布時間: {publish_time}\n\n"
        return result
    else:
        return "目前該地區沒有查詢到交通事件。"

# Generate social response
def generate_social_response(user_message):
    return "感謝您的訊息，我們將會處理您的問題。"

# 主程式
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
