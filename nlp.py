import subprocess
import requests

# TDX API credentials
TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
CLIENT_ID = "bob223590-ba7b60b8-d55c-4d51"
CLIENT_SECRET = "8c2f1ad1-9d79-4d5a-a8d6-a140a7331030"
API_URL = "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/News/City/NewTaipei"
HEADERS = {'content-type': 'application/x-www-form-urlencoded'}

# 使用 Ollama 取得 Llama 模型的回應
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

    command = ["ollama", "run", "llama3.2:3b"]
    try:
        result = subprocess.run(command, input=llama_prompt.encode('utf-8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return result.stdout.decode('utf-8')
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr.decode('utf-8')}")
        return ""
    except FileNotFoundError:
        print("Error: 無法找到 'ollama' 命令，請確認您是否正確安裝了 Ollama。")
        return ""

# 解析 Llama 輸出以提取區域和路段
def parse_area_and_road(llama_output):
    # 打印 Llama 的原始輸出，以便確認它是否有正確解析
    print("Llama Output:")
    print(llama_output)
    
    # 根據 Llama 模型的輸出來提取區域和路段
    lines = llama_output.strip().split('\n')  # 使用 strip() 去除多餘的空格和換行符
    area, road = None, None

    # 添加調試打印
    print("Parsed Lines:")
    print(lines)
    
    for line in lines:
        # 移除兩邊的空格，避免空格影響解析
        line = line.strip()
        if "區域" in line:
            if '：' in line:
                area = line.split('：', 1)[1].strip()
                print(f"提取到的區域：{area}")  # 調試打印
        elif "路段" in line:
            if '：' in line:
                road = line.split('：', 1)[1].strip()
                if road.lower() == 'none':
                    road = None
                print(f"提取到的路段：{road}")  # 調試打印
    
    return area, road


# 查詢交通部 API 的交通資訊（JSON 格式）
def get_traffic_info(area, road):
    # 取得存取權杖
    data = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    try:
        response = requests.post(TOKEN_URL, headers=HEADERS, data=data)
        response.raise_for_status()
        access_token = response.json().get('access_token')
    except requests.RequestException as e:
        print(f"取得存取權杖時發生錯誤：{e}")
        return "無法取得存取權杖，請檢查您的 Client ID 和 Client Secret。"

    # 查詢交通 API（JSON 格式）
    headers = {
        'authorization': f'Bearer {access_token}'
    }

    try:
        response = requests.get(API_URL, headers=headers)
        response.raise_for_status()
        data = response.json()

        # 檢查是否返回了有效的資料，並且確保資料是字典且有 'Newses' 鍵
        if isinstance(data, dict) and 'Newses' in data:
            news_list = data['Newses']
            matching_events = []

            # 當只有路段時，查詢所有與該路段相關的事件
            if road and not area:
                road_lower = road.lower().replace(' ', '')
                for entry in news_list:
                    title = entry.get('Title', '').lower().replace(' ', '')
                    description = entry.get('Description', '').lower().replace(' ', '')

                    # 檢查路段是否存在於標題或描述中
                    if road_lower in title or road_lower in description:
                        matching_events.append(f"交通事件：{entry.get('Title')}\n描述：{entry.get('Description')}\n")

            # 當有區域但沒有具體路段時，查詢所有與該區域相關的事件
            elif area and not road:
                area_lower = area.lower().replace(' ', '')
                for entry in news_list:
                    title = entry.get('Title', '').lower().replace(' ', '')
                    description = entry.get('Description', '').lower().replace(' ', '')

                    # 檢查區域是否存在於標題或描述中
                    if area_lower in title or area_lower in description:
                        matching_events.append(f"交通事件：{entry.get('Title')}\n描述：{entry.get('Description')}\n")

            # 當有區域和路段時，進一步過濾事件
            elif area and road:
                area_lower = area.lower().replace(' ', '')
                road_lower = road.lower().replace(' ', '')
                for entry in news_list:
                    title = entry.get('Title', '').lower().replace(' ', '')
                    description = entry.get('Description', '').lower().replace(' ', '')

                    # 檢查區域和路段是否都存在於標題或描述中
                    if area_lower in title or area_lower in description:
                        if road_lower in title or road_lower in description:
                            matching_events.append(f"交通事件：{entry.get('Title')}\n描述：{entry.get('Description')}\n")

            if matching_events:
                return "\n".join(matching_events)
            else:
                return "無法找到指定區域或路段的交通狀況。"
        else:
            return "無相關的交通資訊。"
    except requests.RequestException as e:
        return f"查詢失敗，錯誤訊息：{e}"


# 主程式
if __name__ == "__main__":
    # 使用者輸入
    user_input = input("請輸入您要查詢的道路事件信息（例如：今天三峽區大埔路有什麼道路事件嗎）：")

    # 呼叫 Llama 3.2 解析輸入
    llama_output = get_llama_response(user_input)

    # 解析 Llama 的輸出
    area, road = parse_area_and_road(llama_output)

    # 查詢交通資訊
    if area:
        print(f"解析結果：區域={area}, 路段={road}")
        traffic_info = get_traffic_info(area, road)
        print(f"路況回應：{traffic_info}")
    else:
        print("未能識別區域或路段，請輸入更清晰的地區或道路名稱，例如：台北市中正區信義路。")
