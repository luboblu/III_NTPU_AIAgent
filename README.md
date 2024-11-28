# 智慧城市大型語言模型代理人系統

本系統旨在為使用者提供交通數據，結合交通部開源API讓使用者可以得知即時路況資訊。

---

## 功能

- **智慧對話**：使用大型語言模型回應使用者查詢。
- **智慧城市數據查詢**：即時提供三峽地區的新聞或交通資訊。
- **LINE Bot 集成**：支持 LINE Messaging API，方便用戶以 LINE 進行互動。
- **本地開發與雲端部署**：支援 ngrok 本地測試以及雲端部署。

---

## 資料夾與檔案結構

| 檔案名稱                 | 說明                                  |
|--------------------------|---------------------------------------|
| `linemain.py`            | 主程式，包含 LINE Bot 與模型邏輯。      |
| `ngrok.exe`              | Ngrok 工具，用於本地測試。              |
| `requirements.txt`       | Python 依賴項列表。                    |
| `sanxia_100_news_format.json` | 新北市三峽地區的新聞數據樣本。          |

---

## 安裝與執行

### 系統需求

- **Python 版本**：3.12.4
- **操作系統**：Windows、MacOS、Linux
- **工具**：
  - Ngrok (用於本地開發)
### 使用編輯器
- **Visual Studio Code**
### 安裝步驟

1. **安裝 Python 與 pip**
   - 確保您的環境已安裝 Python 3.12.4 和 pip 工具。

2. **下載專案檔案**
   - 下載或clone此專案到本地：
     ```bash
     git clone https://github.com/luboblu/III_NTPU_AIAgent.git
     ```

3. **安裝依賴項**
   - 使用 pip 安裝依賴項：
     ```bash
     pip install -r requirements.txt
     ```

4. **配置環境變數**
   - 如果需要 交通部TDX 密鑰，請在環境中配置：
     ```bash
     export TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
     export CLIENT_ID = "bob223590-ba7b60b8-d55c-4d51"
     export CLIENT_SECRET = "8c2f1ad1-9d79-4d5a-a8d6-a140a7331030"
     export API_URL = "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/News/City/NewTaipei?%24top=1000&%24format=JSON"

     ```
   - 如果需要 Line API 密鑰，請在環境中配置：
     ```bash
     export LINE_CHANNEL_SECRET=1ff8185e27c640b535e2a214dbd1488f
     export LINE_CHANNEL_ACCESS_TOKEN=KN80EFH9I1mPuRF+6iEvjw9ncCckrMzdADu6AipHmT2eZJkCov+Qjt8JvSc2HeNEmOfg/UZthe2zsxihgT6FcdB5HI3ruEG7stOqqatnp58k79wPhTlqoA41LDe5yAoYQAiDoMzD5XiR/Vgh5uI10gdB04t89/1O/w1cDnyilFU=
     ```

5. **啟動本地服務**
   - 執行主程式：
     ```bash
     python linemain.py
     ```
   - 啟動 Ngrok，將本地端口暴露到公網：
     ```bash
     ngrok http 5000
     ```
   - 複製Ngrok於Forwarding欄位提供的網址，將其複製於Line Developers的Messaging API之Webhook URL欄位(例:https://9163-2001-b011-381a-75b9-40de-533-add0-ecfc.ngrok-free.app後面加/callback)
---



---

## 使用範例

啟動系統後，用戶可以向 LINE Bot 發送以下指令：

- **「交通」**：獲取當前交通資訊。
- **「最新新聞」**：獲取三峽或新北地區的即時新聞。
- **範例問題**：我想要查詢三峽區學府路路況。

---

## 系統依賴

- **Python 套件**
  - Flask 3.0.3：用於建構 Web 應用。
  - LINE Messaging API SDK：整合 LINE Bot 功能。
- **工具**
  - Ngrok：本地開發測試用。

---

