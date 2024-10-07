from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

app = Flask(__name__)
import ollama
# 必須放上自己的Channel Access Token
line_bot_api = LineBotApi('Ywgpu0U7+ocxOFS5ROnbktgvOloqHwv7yc26vVf9Tj8UJPccLOjD7NDwDIWNYbSsS33pE48qWm1mboag2IC/sj5qxd9oZv5Z1SH8dKzCNrm0v1lmvtfa7TqUCSmiGOmPGX+azGqD9SkgKtwnTdCAdQdB04t89/1O/w1cDnyilFU=')
# 必須放上自己的Channel Secret
handler = WebhookHandler('9a7e7335e8dec2e26eefffcf29a3a2ce')

line_bot_api.push_message('U91779871a9dadda39c8f9e811cbb5b3f', TextSendMessage(text='你可以開始了'))


# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

 
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

 
#訊息傳遞區塊
##### 基本上程式編輯都在這個function #####
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text  # 获取用户发送的消息
    
    # 调试信息，确保收到用户消息
    print(f"User message: {user_message}")
    
    try:
        # 使用 LLaMA 模型生成回复
        response = ollama.generate(model="llama-3.1-8b", prompt=user_message)
        generated_text = response.get('text', '無法生成回應')  # 获取模型生成的文本
        print(f"Generated response: {generated_text}")  # 打印模型生成的回复，确认 LLaMA 响应
    except Exception as e:
        print(f"Error generating response: {str(e)}")  # 打印生成过程中可能发生的错误
        generated_text = "抱歉，無法生成回應。"

    # 将生成的文本发送回用户
    reply_message = TextSendMessage(text=generated_text)
    line_bot_api.reply_message(event.reply_token, reply_message)

#主程式
import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)