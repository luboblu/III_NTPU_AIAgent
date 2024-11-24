import torch
import torch.nn.functional as F
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from transformers import pipeline
from dotenv import load_dotenv
import ollama
import os
from langchain.text_splitter import TokenTextSplitter
from linebot.exceptions import InvalidSignatureError
from sentence_transformers import SentenceTransformer, util
import tiktoken  # 用於 token 化

app = Flask(__name__)
load_dotenv()

# Initialize LINE bot and Webhook handler
line_bot_api = LineBotApi('KN80EFH9I1mPuRF+6iEvjw9ncCckrMzdADu6AipHmT2eZJkCov+Qjt8JvSc2HeNEmOfg/UZthe2zsxihgT6FcdB5HI3ruEG7stOqqatnp58k79wPhTlqoA41LDe5yAoYQAiDoMzD5XiR/Vgh5uI10gdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('1ff8185e27c640b535e2a214dbd1488f')

# Initialize SentenceTransformer model
embed_model = SentenceTransformer('mixedbread-ai/mxbai-embed-large-v1')

# TDX API credentials
TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
CLIENT_ID = "bob223590-ba7b60b8-d55c-4d51"
CLIENT_SECRET = "8c2f1ad1-9d79-4d5a-a8d6-a140a7331030"

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

def get_traffic_data_from_api(access_token, city="NewTaipei"):
    """Retrieve traffic data from TDX API."""
    api_url = f"https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/News/City/{city}"
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        print(f"TDX API Response: {response.json()}")  # Added logging
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling TDX API: {str(e)}")
        return None

# Token chunking with TokenTextSplitter from LangChain
def chunk_text_with_overlap(text, chunk_size=2048, chunk_overlap=200):
    encoding = tiktoken.get_encoding("cl100k_base")  
    text_splitter = TokenTextSplitter(
        encoding_name="cl100k_base",  
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = text_splitter.split_text(text)
    return chunks

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
        # Chunk the user's message with overlap
        chunks = chunk_text_with_overlap(user_message, chunk_size=512)
        
        # Print the chunked messages
        print(f"Chunked messages: {chunks}")
        
        # Embed each chunk using the SentenceTransformer model
        embeddings = [embed_model.encode(chunk) for chunk in chunks]
        
        # Convert embeddings to torch tensors
        embeddings = [torch.tensor(embedding) for embedding in embeddings]
        
        # Process the first chunk (you can customize this as needed)
        query_embedding = embeddings[0]
        
        # Check if it is traffic-related
        if is_traffic_related(query_embedding):
            access_token = get_access_token()
            if access_token is None:
                line_bot_api.push_message(event.source.user_id, TextSendMessage(text="Unable to fetch traffic data."))
                return

            # Call API to get traffic data
            city = "NewTaipei"
            traffic_data = get_traffic_data_from_api(access_token, city)
            if traffic_data:
                formatted_data = format_traffic_data(traffic_data)
                response = generate_response_with_llama(formatted_data)
                line_bot_api.push_message(event.source.user_id, TextSendMessage(text=response))
            else:
                line_bot_api.push_message(event.source.user_id, TextSendMessage(text="No traffic data available."))
        else:
            # Generate social response
            response = generate_social_response(user_message)
            line_bot_api.push_message(event.source.user_id, TextSendMessage(text=response))

    except Exception as e:
        print(f"Error: {str(e)}")
        line_bot_api.push_message(event.source.user_id, TextSendMessage(text="Unable to generate response."))

# Helper function to determine if the message is traffic-related
def is_traffic_related(query_embedding):
    traffic_queries = [
        "current traffic status", "will there be a traffic jam?", "road construction impact",
        "how is the road condition?", "traffic congestion", "road closure?", "any accidents?"
    ]
    
    # Embed the traffic queries
    traffic_embeddings = embed_model.encode(traffic_queries)
    
    # Convert to torch tensor
    traffic_embeddings = torch.tensor(traffic_embeddings)
    
    # Ensure both tensors have the same shape for cosine similarity
    query_embedding = query_embedding.unsqueeze(0) if query_embedding.dim() == 1 else query_embedding
    traffic_embeddings = traffic_embeddings.mean(dim=0, keepdim=True)
    
    # Compute cosine similarity
    similarities = F.cosine_similarity(query_embedding, traffic_embeddings).item()
    
    # Debugging: Print similarity score
    print(f"Similarity score for traffic-related query: {similarities}")

    return similarities > 0.5

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

def generate_social_response(user_message):
    prompt = f"針對以下使用者的問題進行自然且友好的回應：\n\n{user_message}\n\n使用繁體中文進行回應。"
    response = ollama.generate(model="llama3.2:3b", prompt=prompt)
    return response['response'].strip()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)