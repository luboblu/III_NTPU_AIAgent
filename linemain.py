import requests
from flask import Flask, request, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import json
from ollama import chat
from ollama import ChatResponse
from datetime import datetime
import os
# TDX API credentials
TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
CLIENT_ID = "bob223590-ba7b60b8-d55c-4d51"
CLIENT_SECRET = "8c2f1ad1-9d79-4d5a-a8d6-a140a7331030"
API_URL = "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/News/City/NewTaipei?%24top=1000&%24format=JSON"

# Initialize LINE bot and Webhook handler
line_bot_api = LineBotApi('KN80EFH9I1mPuRF+6iEvjw9ncCckrMzdADu6AipHmT2eZJkCov+Qjt8JvSc2HeNEmOfg/UZthe2zsxihgT6FcdB5HI3ruEG7stOqqatnp58k79wPhTlqoA41LDe5yAoYQAiDoMzD5XiR/Vgh5uI10gdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('1ff8185e27c640b535e2a214dbd1488f')

app = Flask(__name__)

# Load JSON file for local traffic data
def load_local_traffic_data():
    try:
        with open('sanxia_100_news_format.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data.get('Newses', [])
    except FileNotFoundError:
        print("Error: 無法找到本地 JSON 檔案。")
        return []

# 使用 Ollama API 取得 Llama 模型的回應
def get_llama_response(input_text):
    llama_prompt = (
    f"請分析以下句子，提取其中的區域和路段名稱，按照指定格式輸出。\n\n"
    f"- **提取規則**：\n"
    f"  - 區域：句子中明確提及的行政區域名稱，如「台北市」、「三峽區」。若未提及，填寫 None。\n"
    f"  - 路段：句子中提及的道路名稱，如「中正路」、「學府路」。若未提及，填寫 None。\n"
    f"  - 注意：不要將路段名稱填入區域，區域和路段不可相同。\n\n"
    f"- **範例1**:\n"
    f"  「我想知道三峽區學府路的路況」\n"
    f"  輸出:\n"
    f"  區域: 三峽區\n"
    f"  路段: 學府路\n\n"
    f"- **範例2**:\n"
    f"  「中正路有塞車嗎」\n"
    f"  輸出:\n"
    f"  區域: None\n"
    f"  路段: 中正路\n\n"
    f"- **範例3**:\n"
    f"  「查詢和平路的交通狀況」\n"
    f"  輸出:\n"
    f"  區域: None\n"
    f"  路段: 和平路\n\n"
    f"請處理以下句子：\n"
    f"「{input_text}」"
)

    try:
        response = chat(
            model="llama3.2",
            messages=[{"role": "user", "content": llama_prompt}],
            api_url = os.getenv("OLLAMA_API_URL", "http://120.126.146.9:11434")
        )
        if isinstance(response, dict) and 'message' in response:
            return response['message']['content'].strip()
        else:
            print(f"Error: 無法解析 Ollama 回應: {response}")
            return "無法獲取 Ollama 的回應，請檢查配置。"
    except Exception as e:
        print(f"Error in get_llama_response: {e}")
        return "無法獲取 Ollama 的回應，請檢查配置。"

# 解析 Llama 輸出以提取區域和路段
def parse_area_and_road(llama_output):
    lines = llama_output.strip().split('\n')
    area, road = None, None

    for line in lines:
        line = line.strip()
        if "區域" in line and '：' in line:
            area = line.split('：', 1)[1].strip()
        elif "路段" in line and '：' in line:
            road = line.split('：', 1)[1].strip()
            if road.lower() == 'none':
                road = None

    return area, road

# 格式化日期
def format_datetime(dt_str):
    try:
        dt = datetime.fromisoformat(dt_str[:-6])
        return dt.strftime('%Y-%m-%d %H:%M')
    except ValueError:
        return "未知時間"

# 查詢交通資訊（本地 JSON 檔案或 API）
def get_traffic_info(area, road):
    news_list = load_local_traffic_data()
    matching_events = []

    # 查詢 API 以獲取最新的交通資訊
    data = {'grant_type': 'client_credentials', 'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET}
    try:
        response = requests.post(TOKEN_URL, data=data)
        response.raise_for_status()
        access_token = response.json().get('access_token')
    except requests.RequestException as e:
        print(f"取得存取權杖時發生錯誤：{e}")
        access_token = None

    if access_token:
        headers = {'authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(API_URL, headers=headers)
            response.raise_for_status()
            api_data = response.json()
            if isinstance(api_data, dict) and 'Newses' in api_data:
                news_list.extend(api_data['Newses'])
        except requests.RequestException as e:
            print(f"查詢 API 時發生錯誤：{e}")

    # 查詢結果匹配邏輯
    if area or road:
        for entry in news_list:
            title = entry.get('Title', '').lower().replace(' ', '')
            if area and area.lower().replace(' ', '') in title or road and road.lower().replace(' ', '') in title:
                matching_events.append(
                    f"{entry.get('Title')}\n時間：{format_datetime(entry.get('StartTime'))} - {format_datetime(entry.get('EndTime'))}"
                )

    return '\n'.join([f'{index + 1}. {event}' for index, event in enumerate(matching_events)]) if matching_events else "無法找到指定區域或路段的交通狀況。"

# 接收 LINE Bot 的消息
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return 'Invalid signature. Please check your channel access token/channel secret.', 400
    return 'OK'

# 處理 LINE 的文字消息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_input = event.message.text
    llama_output = get_llama_response(user_input)
    area, road = parse_area_and_road(llama_output)

    if area or road:
        traffic_info = get_traffic_info(area, road)
        response_message = f"我找到了與您提供的地區和路段有關的最新交通狀況：\n{traffic_info}" if traffic_info else "目前沒有找到相關的交通資訊，請稍後再查詢或提供更多細節。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response_message))
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="未能識別區域或路段，請輸入更清晰的地區或道路名稱，例如：台北市中正區信義路。"))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
