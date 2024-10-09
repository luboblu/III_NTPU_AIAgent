from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import json
import ollama
import os
import re
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

line_bot_api = LineBotApi('Ywgpu0U7+ocxOFS5ROnbktgvOloqHwv7yc26vVf9Tj8UJPccLOjD7NDwDIWNYbSsS33pE48qWm1mboag2IC/sj5qxd9oZv5Z1SH8dKzCNrm0v1lmvtfa7TqUCSmiGOmPGX+azGqD9SkgKtwnTdCAdQdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('9a7e7335e8dec2e26eefffcf29a3a2ce')

# 加載 JSON 資料
with open(r'C:\Users\盧bob\Desktop\AI Agent\response_1728401437388.json', 'r', encoding='utf-8') as f:
    traffic_data = json.load(f)
line_bot_api.push_message('U91779871a9dadda39c8f9e811cbb5b3f', TextSendMessage(text='您好，我是您的交通小助手請問您想查詢哪個地區的交通狀況?'))

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

# 處理文本消息
# 改進分詞提示詞
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    print(f"User message: {user_message}")

    generated_text = "抱歉，無法生成回應。"

    try:
        # 使用 LLaMA 進行分詞，並指導它僅返回分詞結果
        prompt = f"請對以下查詢進行分詞，僅返回詞語列表，每個詞之間用空格分開，請勿添加其他說明或解釋：'{user_message}'"
        response = ollama.generate(model="llama3.1:8b", prompt=prompt)

        # 提取 LLaMA 分詞結果
        if 'response' in response:
            keywords = response['response'].strip()
            print(f"Extracted keywords from LLaMA: {keywords}")
        else:
            generated_text = "無法生成回應，回應格式不正確。"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=generated_text))
            return

        # 對分詞結果進行優化處理
        optimized_keywords = optimize_keywords(keywords)
        print(f"Optimized keywords for search: {optimized_keywords}")

        # 使用優化後的分詞結果進行 JSON 搜索
        filtered_data = filter_traffic_data_by_keywords(optimized_keywords)

        # 格式化交通事件數據並返回
        if filtered_data:
            formatted_response = format_traffic_data(filtered_data)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=formatted_response))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"未查詢到與您的描述 '{user_message}' 相關的交通事件。"))

    except Exception as e:
        print(f"Error: {str(e)}")
        generated_text = "抱歉，無法生成回應。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=generated_text))


# 優化分詞結果，保留更相關的交通詞彙
def optimize_keywords(keywords):
    # 將 LLaMA 的分詞結果進行進一步處理
    words = keywords.split()
    optimized_keywords = []

    i = 0
    while i < len(words):
        # 合併常見的地名或交通詞
        combined = words[i]
        if i + 1 < len(words):
            combined += words[i + 1]
        if i + 2 < len(words):
            combined += words[i + 2]
        
        # 如果合併後的詞包含區、路、線等常見交通或地理標誌，則視為完整詞
        if "區" in combined or "路" in combined or "線" in combined:
            optimized_keywords.append(combined)
            i += 2  # 跳過已處理的詞
        else:
            optimized_keywords.append(words[i])
        i += 1

    print(f"Final optimized keywords: {optimized_keywords}")
    return " ".join(optimized_keywords)



def filter_traffic_data_by_keywords(keywords):
    filtered_data = []
    # 將分詞結果分割成關鍵字列表
    query_keywords = keywords.split()
    print(f"Filtering with optimized keywords: {query_keywords}")

    # 遍歷 JSON 資料中的每個事件，並根據查詢進行精確匹配
    for news in traffic_data.get('Newses', []):
        # 將標題和描述轉為小寫，以便不區分大小寫進行匹配
        text = (news.get('Title', '') + " " + news.get('Description', '')).lower()
        
        # 檢查是否有完整的地名匹配，例如「金山區」
        if any(keyword.lower() in text for keyword in query_keywords if len(keyword) > 1):
            # 確保關鍵字包含具體的地名
            if any(place.lower() in text for place in query_keywords if "區" in place or "路" in place or "線" in place):
                filtered_data.append(news)
    
    print(f"Filtered data: {filtered_data}")
    return filtered_data



# 格式化交通事件數據
def format_traffic_data(data):
    if data:
        result = "當前地區的交通事件如下：\n"
        for item in data:
            title = item.get('Title', '未知事件')
            start_time = item.get('StartTime', '未知開始時間')
            end_time = item.get('EndTime', '未知結束時間')
            result += f"- 事件: {title}\n  開始時間: {start_time}\n  結束時間: {end_time}\n\n"
        return result
    else:
        return "目前該地區沒有查詢到交通事件。"

# 主程式
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
