from flask import Flask, request, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, LocationMessage, TextSendMessage
import requests
import ollama  # 使用ollama庫來串接LLaMA

app = Flask(__name__)

# 設定LINE和Google Maps API相關參數
GOOGLE_API_KEY = 'AIzaSyDkHH3UQ5tqzfwgX-GjyIOMUdtQLmSu8ow'

# 初始化LINE bot和Webhook處理器
line_bot_api = LineBotApi('KN80EFH9I1mPuRF+6iEvjw9ncCckrMzdADu6AipHmT2eZJkCov+Qjt8JvSc2HeNEmOfg/UZthe2zsxihgT6FcdB5HI3ruEG7stOqqatnp58k79wPhTlqoA41LDe5yAoYQAiDoMzD5XiR/Vgh5uI10gdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('1ff8185e27c640b535e2a214dbd1488f')

def generate_response_with_llama(full_address, max_chars=700):
    prompt = f"""
    請將以下英文格式的地址轉換為繁體中文格式，並按照「郵遞區號、市、區、路、號」的順序返回，且僅返回轉換後的地址。

    輸入地址：
    {full_address}

    請依據以下範例進行格式轉換：
    範例1：
    英文輸入：No. 80號, Zhongzheng Rd, Tucheng District, New Taipei City, Taiwan 236
    中文輸出：236新北市土城區中正路80號
    
    範例2：
    英文輸入：No. 10號, Renai Rd, Da’an District, Taipei City, Taiwan 106
    中文輸出：106台北市大安區仁愛路10號

    請直接輸出轉換後的中文地址（無需任何附加描述或其他範例），格式如下：
    「郵遞區號+市+區+路+號」
    """
    
    try:
        # 使用ollama庫生成LLaMA回應
        response = ollama.generate(model="llama3.2:3b", prompt=prompt)
        
        # 打印LLaMA的回應以便調試
        print(f"LLaMA 生成的回應：{response}")
        
        # 確認回應是否包含生成的描述
        if response and 'response' in response:
            return response['response'].strip()[:max_chars]
        else:
            return "抱歉，無法生成詳細地址描述。"
    
    except Exception as e:
        # 錯誤處理
        print(f"LLaMA 生成錯誤：{e}")
        return "抱歉，目前無法提供服務，請稍後再試。"

@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    # 取得使用者傳送的經緯度
    latitude = event.message.latitude
    longitude = event.message.longitude
    
    # 使用Google Maps Geocoding API進行反向地理編碼
    geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={latitude},{longitude}&key={GOOGLE_API_KEY}"
    response = requests.get(geocode_url)
    data = response.json()
    
    if data['status'] == 'OK' and data['results']:
        # 獲取完整地址
        full_address = data['results'][0]['formatted_address']
        
        # 打印獲取到的地址，以便調試
        print(f"抓取到的完整地址：{full_address}")
        
        # 使用LLaMA生成詳細描述
        detailed_address = generate_response_with_llama(full_address)
        
        # 打印LLaMA生成的詳細描述，以便調試
        print(f"LLaMA 生成的完整地址：{detailed_address}")
        
        # 回傳LLaMA的描述到使用者
        reply_message = TextSendMessage(text=f"完整地址：{detailed_address}")
        line_bot_api.reply_message(event.reply_token, reply_message)
    else:
        # 如果無法找到地址，回傳錯誤訊息
        error_message = TextSendMessage(text="無法找到該位置的詳細地址，請稍後再試。")
        line_bot_api.reply_message(event.reply_token, error_message)



@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    handler.handle(body, signature)
    return 'OK'



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
