import ollama

response = ollama.generate(model="llama3.1:8b", prompt="今天天氣怎麼樣？")
print(response)
# # 處理圖片消息
# @handler.add(MessageEvent, message=ImageMessage)
# def handle_image(event):
#     message_content = line_bot_api.get_message_content(event.message.id)
    
#     # 將圖片保存到本地
#     image_path = f"received_image_{event.message.id}.jpg"
#     with open(image_path, "wb") as f:
#         for chunk in message_content.iter_content():
#             f.write(chunk)
    
#     # 進行圖片分析
#     analysis_result = analyze_image(image_path)
    
#     # 使用 LLaMA 根據圖片分析結果生成回應
#     try:
#         response = ollama.generate(model="llama3.1:8b", prompt=analysis_result)
#         if 'response' in response:
#             generated_text = response['response']
#         else:
#             generated_text = "無法生成回應，回應格式不正確。"
#     except Exception as e:
#         print(f"Error generating response from LLaMA: {str(e)}")
#         generated_text = "抱歉，無法生成回應。"

#     # 將分析結果與 LLaMA 回應發送回用戶
#     reply_message = TextSendMessage(text=generated_text)
#     line_bot_api.reply_message(event.reply_token, reply_message)

# # 自定義圖片分析邏輯
# def analyze_image(image_path):
#     # 初始化 Google Cloud Vision 客戶端
#     client = vision.ImageAnnotatorClient()

#     # 讀取圖片文件
#     with io.open(image_path, 'rb') as image_file:
#         content = image_file.read()
    
#     # 構建圖像對象
#     image = vision.Image(content=content)

#     # 調用 Vision API 進行標籤檢測（Label Detection）
#     response = client.label_detection(image=image)
#     labels = response.label_annotations

#     # 組織分析結果
#     if labels:
#         result = "圖片分析結果：\n"
#         for label in labels:
#             result += f"{label.description} (信心度: {label.score*100:.2f}%)\n"
#     else:
#         result = "圖片中未識別到明確內容。"

#     return result