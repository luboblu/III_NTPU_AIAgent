from flask import Flask, request, abort, jsonify, Response
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import ollama
app = Flask(__name__)
import json
from langchain_community.llms import HuggingFaceEndpoint
import torch
from transformers import AutoModel, AutoTokenizer
from linebot.exceptions import LineBotApiError
from sentence_transformers import util
import requests
# Initialize LINE bot and Webhook handler
line_bot_api = LineBotApi('KN80EFH9I1mPuRF+6iEvjw9ncCckrMzdADu6AipHmT2eZJkCov+Qjt8JvSc2HeNEmOfg/UZthe2zsxihgT6FcdB5HI3ruEG7stOqqatnp58k79wPhTlqoA41LDe5yAoYQAiDoMzD5XiR/Vgh5uI10gdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('1ff8185e27c640b535e2a214dbd1488f')
# TDX API credentials
TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
CLIENT_ID = "bob223590-ba7b60b8-d55c-4d51"
CLIENT_SECRET = "8c2f1ad1-9d79-4d5a-a8d6-a140a7331030"
def push_message():
    user_id = 'U58f17307e43efeb61bd4009f9daaaaa8'  
    try:
        # 發送歡迎訊息
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text="您好，我是您的交通小助手，想查詢哪裡的交通資訊呢？")
        )
        return "推播訊息已發送"
    except LineBotApiError as e:
        app.logger.error(f"推播訊息失敗: {e}")
        return "推播訊息失敗", 500
# 初始化 RAG 系統
def initialize_rag():
    # 1. 從 JSON 檔案中讀取數據
    file_path = 'C:\\Users\\盧bob\\Desktop\\AI Agent\\sanxia_100_news_format.json'
    json_segments = load_and_split_json(file_path)

    # 2. 從 API 中讀取數據
    api_segments = fetch_data_from_api()

    # 將 JSON 檔案和 API 的數據合併
    all_segments = json_segments + api_segments

    # 初始化模型
    model = SentenceTransformer('mixedbread-ai/mxbai-embed-large-v1')
    embeddings = []

    # 使用小批次編碼，避免內存不足
    for i in range(0, len(all_segments), 8):
        batch = [item['Description'] for item in all_segments[i:i+8]]
        batch_embeddings = model.encode(batch, batch_size=8)
        embeddings.extend(batch_embeddings)
        torch.cuda.empty_cache()

    # 建立 FAISS 索引
    dimension = embeddings[0].shape[0]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings))

    return model, index, all_segments

def load_and_split_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    segments = [item for item in data['Newses']]
    return segments

def get_access_token():
    """Fetch access token for TDX API."""
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'grant_type': 'client_credentials', 'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET}
    try:
        response = requests.post(TOKEN_URL, headers=headers, data=data)
        response.raise_for_status()
        return response.json()['access_token']
    except requests.exceptions.RequestException as e:
        print(f"Error fetching access token: {str(e)}")
        return None

def fetch_data_from_api():
    """Retrieve traffic data from TDX API and return as segments."""
    access_token = get_access_token()
    if not access_token:
        print("Failed to retrieve access token.")
        return []
    
    api_url = f"https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/News/City/NewTaipei"
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        
        api_segments = []
        api_data = response.json()

        # 假設 API 回應格式有 'Newses' 字段或類似字段
        if 'Newses' in api_data:
            api_segments = [item for item in api_data['Newses']]
        else:
            print("Unexpected API response format.")
        
        print(f"Fetched {len(api_segments)} items from TDX API.")
        return api_segments
    
    except requests.exceptions.RequestException as e:
        print(f"Error calling TDX API: {str(e)}")
        return []

# 查詢檢索系統
def query_rag_system(query, model, index, segments, k=10):
    query_embedding = model.encode([query])
    distances, indices = index.search(np.array(query_embedding), k=k)
    retrieved_segments = [segments[i] for i in indices[0]]

    # 提取查詢中的區域和路名
    area = "三峽區"
    specific_location = get_specific_location_from_query(query)

    # 過濾段落
    area_segments = [seg for seg in retrieved_segments if area in seg['Description']]
    if specific_location:
        relevant_segments = [seg for seg in area_segments if specific_location in seg['Description']]
        if relevant_segments:
            return relevant_segments

    return area_segments[:3] if area_segments else retrieved_segments[:3]

def get_specific_location_from_query(query):
    location_terms = ["路", "街", "巷", "大道", "段"]
    for term in location_terms:
        if term in query:
            start_index = query.find("三峽區") + len("三峽區")
            end_index = query.find(term) + len(term)
            return query[start_index:end_index].strip()
    return None



def format_traffic_data(data):
    if data:
        result = "以下為您所需的交通資訊：\n"
        for idx, item in enumerate(data, 1):
            title = item.get('Title', '未知事件')
            description = item.get('Description', '無描述')
            start_time = item.get('StartTime', '未知開始時間')
            end_time = item.get('EndTime', '未知結束時間')
            result += (
                f"\n{idx}.\n"
                f"事件：{title}\n"
                f"描述：{description}\n"
                f"開始時間：{start_time}\n"
                f"結束時間：{end_time}\n"
            )
        return result.strip()
    else:
        return "目前該地區沒有查詢到交通事件。"


def generate_response_with_llama(user_message, relevant_info, max_chars=700):
    """Generate a more conversational response using LLaMA model based on traffic data."""
    if relevant_info:
        # 生成包含交通資訊的 prompt，讓 LLaMA 自然地回答
        formatted_info = ""
        for idx, item in enumerate(relevant_info, 1):
            title = item.get('Title', '未知事件')
            description = item.get('Description', '無描述')
            start_time = item.get('StartTime', '未知開始時間')
            end_time = item.get('EndTime', '未知結束時間')
            formatted_info += (
                f"事件：{title}，描述：{description}，開始時間：{start_time}，結束時間：{end_time}。\n"
            )

        # 設計 prompt，使 LLaMA 更人性化地回答
        prompt = f"""
        您是一位交通助手，專門提供台灣地區的交通資訊。請根據以下的交通資訊，用簡單自然的語氣生成一個清晰的回應，讓使用者了解目前的狀況。請避免過於制式的回應，並保持輕鬆、友好的語氣。以下是交通資訊：

        {formatted_info}

        使用者詢問的問題是："{user_message}"
        
        請生成回應。
        """

        response = ollama.generate(model="llama3.2:3b", prompt=prompt)

        # 回傳截取字數範圍內的 LLaMA 回應
        if 'response' in response:
            return response['response'].strip()[:max_chars]
        else:
            return "抱歉，目前沒有相關的交通事件資訊。"
    else:
        # 如果沒有檢索到資訊，生成通用回應
        return "抱歉，目前沒有相關的交通事件資訊。"




# 初始化 RAG 系統
rag_model, rag_index, rag_segments = initialize_rag()

# 處理 LINE Webhook 請求
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
def generate_general_response(user_message):
    prompt = f"""
    你是一個智慧交通助手，負責回答各種問題。請用自然語言回答以下問題，並使用繁體中文回應：

    問題："{user_message}"
    """

    response = ollama.generate(model="llama3.2:3b", prompt=prompt)

    if 'response' in response:
        return response['response'].strip()
    else:
        return "抱歉，我無法處理您的問題，請稍後再試。"
traffic_examples = [
    "我想查詢交通狀況",
    "請問某某路的路況如何",
    "現在有沒有堵車",
    "某個地區的交通事件有哪些",
    "查詢交通事故情況"
]

def check_traffic_related(user_message, threshold=0.7):
    user_embedding = rag_model.encode([user_message])
    traffic_embeddings = rag_model.encode(traffic_examples)
    similarities = util.cos_sim(user_embedding, traffic_embeddings)
    max_similarity = similarities.max().item()
    return max_similarity >= threshold


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text

    # 判斷是否與交通相關
    is_traffic_related = check_traffic_related(user_message)

    if is_traffic_related:
        # 使用 RAG 系統嘗試檢索相關的交通資訊
        retrieved_segments = query_rag_system(user_message, rag_model, rag_index, rag_segments)
        
        if retrieved_segments:
            # 如果有檢索到相關資訊，生成 RAG 回應
            response_message = generate_response_with_llama(user_message, retrieved_segments)
        else:
            # 如果沒有檢索到，直接讓語言模型生成自然語言回應
            response_message = generate_general_response(user_message)
    else:
        # 不包含交通相關查詢，直接交給語言模型生成自然語言回應
        response_message = generate_general_response(user_message)

    # 回覆訊息給 LINE 用戶
    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response_message)
        )
    except LineBotApiError as e:
        app.logger.error(f"Failed to send reply: {e}")


if __name__ == "__main__":
    push_message()
    app.run(host="0.0.0.0", port=5000)
    