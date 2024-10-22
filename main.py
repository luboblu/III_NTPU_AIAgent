import torch
import torch.nn.functional as F
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv
from linebot.exceptions import InvalidSignatureError
import ollama
import os
from transformers import pipeline
import re

app = Flask(__name__)
load_dotenv()

# Initialize the LineBot API and webhook
line_bot_api = LineBotApi('Ywgpu0U7+ocxOFS5ROnbktgvOloqHwv7yc26vF9Tj8UJPccLOjD7NDwDIWNYbSsS33pE48qWm1mboag2IC/sj5qxd9oZv5Z1SH8dKzCNrm0v1lmvtfa7TqUCSmiGOmPGX+azGqD9SkgKtwnTdCAdQdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('9a7e7335e8dec2e26eefffcf29a3a2ce')

# Initialize the NV-Embed-v2 pipeline
pipe = pipeline("feature-extraction", model="nvidia/NV-Embed-v2", trust_remote_code=True)

# TDX API 相關變數
TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
CLIENT_ID = "bob223590-ba7b60b8-d55c-4d51"  # 使用你的client_id
CLIENT_SECRET = "8c2f1ad1-9d79-4d5a-a8d6-a140a7331030"  # 使用你的client_secret

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
        # Check if the query is traffic-related using NV-Embed-v2
        is_traffic_related = detect_traffic_related(user_message)

        if is_traffic_related:
            # Fetch traffic data from TDX API
            access_token = get_access_token()
            traffic_data = get_traffic_data_from_api(access_token)

            if traffic_data:
                road_names, district_names = get_all_road_and_district_names_from_api(traffic_data)
                traffic_keywords, traffic_locations = extract_traffic_info(user_message, road_names, district_names)

                if traffic_keywords or traffic_locations:
                    formatted_data = format_traffic_data(traffic_data, traffic_locations)
                    response = generate_response_with_llama(formatted_data)
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))
                else:
                    response = generate_social_response(user_message)
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="抱歉，無法取得交通數據。"))
        else:
            # If not traffic-related, generate a social response
            response = generate_social_response(user_message)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

    except Exception as e:
        print(f"Error: {str(e)}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="抱歉，無法生成回應。"))

# Detect if the query is traffic-related using NV-Embed-v2 pipeline
def detect_traffic_related(user_message):
    traffic_terms = ["交通", "壅塞", "施工", "路況", "封路", "事故"]
    query_embeddings = torch.tensor(pipe(user_message))

    if query_embeddings is None:
        print("Failed to extract features for user_message")
        return False

    for term in traffic_terms:
        term_embedding = torch.tensor(pipe(term))
        if term_embedding is None:
            print(f"Failed to extract features for term: {term}")
            continue

        similarity = F.cosine_similarity(query_embeddings, term_embedding).item()
        if similarity > 0.7:
            return True
    return False

# Get access token from TDX API
def get_access_token():
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'grant_type': 'client_credentials', 'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET}
    try:
        response = requests.post(TOKEN_URL, headers=headers, data=data)
        response.raise_for_status()
        token_info = response.json()
        return token_info['access_token']
    except requests.exceptions.RequestException as e:
        print(f"Error fetching access token: {str(e)}")
        return None

# Fetch traffic data from TDX API
def get_traffic_data_from_api(access_token):
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    try:
        response = requests.get("https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/News/City/NewTaipei", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling TDX API: {str(e)}")
        return None

# Extract traffic-related locations and keywords
def extract_traffic_info(user_message, road_names, district_names):
    query_embeddings = torch.tensor(pipe(user_message))
    traffic_keywords, traffic_locations = [], []

    # Check for matches with road and district names
    for road in road_names:
        road_embedding = torch.tensor(pipe(road))
        similarity = F.cosine_similarity(query_embeddings, road_embedding).item()
        if similarity > 0.7:
            traffic_locations.append(road)

    for district in district_names:
        district_embedding = torch.tensor(pipe(district))
        similarity = F.cosine_similarity(query_embeddings, district_embedding).item()
        if similarity > 0.7:
            traffic_locations.append(district)

    return traffic_keywords, traffic_locations

# Extract road and district names from API traffic data
def get_all_road_and_district_names_from_api(traffic_data):
    road_names, district_names = set(), set()
    for item in traffic_data['Newses']:
        title = item.get('Title', '')
        description = item.get('Description', '')
        for name in extract_names_from_text(title + description):
            if '路' in name or '公路' in name:
                road_names.add(name)
            if '區' in name:
                district_names.add(name)
    return list(road_names), list(district_names)

# Use regex to extract road and district names
def extract_names_from_text(text):
    pattern = r"(\w+路|\w+公路|\w+區)"
    return re.findall(pattern, text)

# Format traffic data for LLaMA response
def format_traffic_data(data, traffic_locations):
    if data:
        result = "當前地區的交通事件如下：\n"
        for item in data['Newses']:
            title = item.get('Title', '未知事件')
            description = item.get('Description', '無描述')
            publish_time = item.get('PublishTime', '未知發布時間')
            if any(location in title for location in traffic_locations):
                result += f"- 事件: {title}\n  描述: {description}\n  發布時間: {publish_time}\n\n"
        return result
    else:
        return "目前該地區沒有查詢到交通事件。"

# Generate traffic-related response using LLaMA
def generate_response_with_llama(context):
    prompt = f"""
    你是一個交通助手，專門負責台灣地區的交通事件回報。以下是一些關於交通事件的資料：

    {context}

    請你根據這些資料，使用繁體中文生成一個清晰且準確的回答。
    """
    response = ollama.generate(model="llama3.2:3b", prompt=prompt)
    return response['response'].strip() if 'response' in response else "無法生成回應。"

# Generate general responses for non-traffic queries
def generate_social_response(user_message):
    prompt = f"針對以下使用者的問題進行自然且友好的回應：\n\n{user_message}\n\n使用繁體中文進行回應。"
    response = ollama.generate(model="llama3.2:3b", prompt=prompt)
    return response['response'].strip()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
