import re
from llama_index.llms.openai import OpenAI
from llama_index.core.llms import ChatMessage
from llama_index.core import Settings

# 利用 GPT‑4 自動提取查詢中的主要關鍵字（讓模型自動處理贅字）
def extract_keyword(query):
    prompt = (
        "請將下面這句話簡化，只保留主要查詢關鍵字，移除所有不必要的贅字：\n"
        "【範例】\n"
        "使用者輸入：請問三峽區佳福路的路況為何？\n"
        "簡化後的結果：三峽區佳福路\n\n"
        "使用者輸入：請問台1高架交通資訊？\n"
        "簡化後的結果：台1高架\n\n"
        "使用者輸入：請問三峽區交通路況為何？\n"
        "簡化後的結果：三峽區\n\n"
        f"【原始查詢】\n{query}\n\n"
        "請回覆簡化後的查詢關鍵字："
    )
    messages = [ChatMessage(role="user", content=prompt)]
    response = Settings.llm.chat(model="gpt-4", messages=messages)
    return response.message.content.strip()

# 從合併後的資源內容中解析事件資訊，過濾出包含關鍵字的記錄
def extract_event_info(text, keyword):
    records = text.strip().split("\n\n")
    events = []
    for rec in records:
        if keyword in rec:
            title_match = re.search(r"title:\s*(.*)", rec)
            start_match = re.search(r"start_time:\s*(.*)", rec)
            end_match = re.search(r"end_time:\s*(.*)", rec)
            if title_match and start_match and end_match:
                event = {
                    "title": title_match.group(1).strip(),
                    "start_time": start_match.group(1).strip(),
                    "end_time": end_match.group(1).strip()
                }
                events.append(event)
    return events

# 利用 GPT‑4 生成以項目符號列點的回答，並在末尾附上警示訊息
def generate_bullet_answer(events):
    prompt = (
        "請根據下列所有事件資訊生成一個以項目符號列點的回答，回答格式必須嚴格遵守以下要求：\n\n"
        "格式：\n"
        "<序號>. <路段描述>，開始時間：<YYYY年MM月DD日HH:MM>，結束時間：<YYYY年MM月DD日HH:MM>，請注意行車安全。\n\n"
        "【所有事件資訊】\n"
    )
    for i, event in enumerate(events, start=1):
        prompt += (
            f"序號：{i}\n"
            f"路段描述：{event['title']}\n"
            f"開始時間：{event['start_time']}\n"
            f"結束時間：{event['end_time']}\n\n"
        )
    prompt += "請生成符合上述格式的回答，並在所有列點最後附上：請注意安全，小心駕駛。不要添加其他額外內容。"
    messages = [ChatMessage(role="user", content=prompt)]
    response = Settings.llm.chat(model="gpt-4", messages=messages)
    return response.message.content.strip()

def main():
    # 設定使用 OpenAI GPT 模型，這裡指定使用 GPT‑4，不使用向量檢索
    Settings.llm = OpenAI(api_key="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", model="gpt-4", request_timeout=360.0)
    
    # 設定資源文件路徑
    resource_path = r"C:\Users\盧bob\Desktop\test\data\resource.txt"
    traffic_data_path = r"C:\Users\盧bob\Desktop\test\data\traffic_data.txt"
    
    resource_text = ""
    traffic_text = ""
    
    try:
        with open(resource_path, "r", encoding="utf-8") as f:
            resource_text = f.read()
    except FileNotFoundError:
        print("找不到資源文件：", resource_path)
    
    try:
        with open(traffic_data_path, "r", encoding="utf-8") as f:
            traffic_text = f.read()
    except FileNotFoundError:
        print("找不到交通數據文件：", traffic_data_path)
    
    if not resource_text and not traffic_text:
        print("未讀取到任何資源檔案。")
        return
    
    # 將兩個文件內容合併
    combined_text = resource_text + "\n" + traffic_text
    
    # 使用者輸入查詢（可依需求動態改變）
    user_query = "請問三樹路交通狀況"
    
    # 利用 GPT‑4 自動提取查詢中的主要關鍵字
    keyword = extract_keyword(user_query)
    print("提取後的關鍵字：", keyword)
    
    # 從合併後的資源中搜尋所有符合關鍵字的事件資訊
    events = extract_event_info(combined_text, keyword)
    if not events:
        print("查無相關事件資訊。")
        return
    print("搜尋到的事件資訊：", events)
    
    # 利用 GPT‑4 生成以項目符號列點的最終回答，並在末尾附上警示訊息
    final_answer = generate_bullet_answer(events)
    print("最終回應：", final_answer)

if __name__ == "__main__":
    main()
