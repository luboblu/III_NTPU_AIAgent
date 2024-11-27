from flask import Flask, request, abort
from linebot import LineBotApi
from linebot.v3.webhook import WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import LineBotApiError
from langchain.prompts import PromptTemplate
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_community.chat_models import ChatOllama
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import json
import logging

# 初始化 Flask 應用程式
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize LINE bot and Webhook handler
line_bot_api = LineBotApi('KN80EFH9I1mPuRF+6iEvjw9ncCckrMzdADu6AipHmT2eZJkCov+Qjt8JvSc2HeNEmOfg/UZthe2zsxihgT6FcdB5HI3ruEG7stOqqatnp58k79wPhTlqoA41LDe5yAoYQAiDoMzD5XiR/Vgh5uI10gdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('1ff8185e27c640b535e2a214dbd1488f')

# JSON 檔案路徑
JSON_FILE_PATH = "C:\\Users\\盧bob\\Desktop\\AI Agent\\sanxia_100_news_format.json"

# 自訂的嵌入類，用於封裝 SentenceTransformer
class SentenceTransformerEmbeddings:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, texts):
        """生成多個文檔的嵌入"""
        return self.model.encode(texts, convert_to_numpy=True)
    
    def embed_query(self, text):
        """生成單一查詢的嵌入"""
        return self.model.encode([text], convert_to_numpy=True)[0]

# 1. 從 JSON 文件載入資料並初始化向量存儲
def load_data():
    """載入 JSON 文件中的資料並初始化 FAISS 向量存儲"""
    try:
        # 讀取 JSON 文件
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # 提取 Newses 的數據
        texts = []
        metadatas = []
        for item in data.get("Newses", []):
            texts.append(item.get("Description", ""))
            metadatas.append({
                "title": item.get("Title", "未知"),
                "start_time": item.get("StartTime", "未知"),
                "end_time": item.get("EndTime", "未知"),
                "update_time": item.get("UpdateTime", "未知")
            })
        
        # 初始化 Sentence Transformer 模型
        embeddings = SentenceTransformerEmbeddings()

        # 使用 FAISS.from_texts 初始化向量存儲
        vector_store = FAISS.from_texts(texts=texts, embedding=embeddings, metadatas=metadatas)
        logging.info("向量存儲初始化成功")
        return vector_store

    except Exception as e:
        logging.error(f"向量存儲初始化失敗：{e}")
        raise e

# 2. 初始化檢索增強生成 (RAG) 系統
def create_retrieval_chain(vector_store):
    """初始化檢索增強生成 (RAG) 系統"""
    try:
        # 使用 Ollama 的 LLaMA 3.2 3B 作為生成模型
        llm = ChatOllama(model="llama3.2:3b")

        # 使用 RetrievalQA.from_chain_type 簡化初始化
        chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=vector_store.as_retriever(search_kwargs={"k": 5}),
            chain_type="stuff",  # 預設的 Chain Type，可根據需求調整
            return_source_documents=True  # 是否返回檢索到的資料
        )
        logging.info("檢索增強生成系統初始化成功")
        return chain

    except Exception as e:
        logging.error(f"檢索增強生成系統初始化失敗：{e}")
        raise e

# 初始化向量存儲與檢索系統
try:
    vector_store = load_data()
    retrieval_chain = create_retrieval_chain(vector_store)
except Exception as e:
    logging.error(f"系統初始化失敗：{e}")

# 處理 LINE Webhook 請求
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except LineBotApiError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text

    try:
        logging.info(f"接收到用戶訊息：{user_message}")
        
        # 檢索相關文件並生成回應
        response_message = retrieval_chain.run({"query": user_message})
        
        if not response_message:
            response_message = "抱歉，我無法找到相關資訊，請稍後再試。"

        # 回覆用戶訊息
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response_message)
        )

    except Exception as e:
        logging.error(f"處理用戶訊息時出錯：{e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="抱歉，我無法處理您的請求，請稍後再試。")
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
