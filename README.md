
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
| `Dockerfile`             | 定義如何建構 Docker 映像檔，便於部署。 |

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
   - 下載或克隆此專案到本地：
     ```bash
     git clone https://github.com/luboblu/III_NTPU_AIAgent.git
     ```

3. **安裝依賴項**
   - 使用 pip 安裝依賴項：
     ```bash
     pip install -r requirements.txt
     ```

4. **配置環境變數**

- **如果需要 交通部 TDX 密鑰，請在環境中配置：**
    ```bash
    export TOKEN_URL="[https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token](https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token)"
    export CLIENT_ID="bob223590-ba7b60b8-d55c-4d51"
    export CLIENT_SECRET="********-****-****-****-************"
    export API_URL="[https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/News/City/NewTaipei?%24top=1000&%24format=JSON](https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/News/City/NewTaipei?%24top=1000&%24format=JSON)"
    ```

- **如果需要 Line API 密鑰，請在環境中配置：**
    ```bash
    export LINE_CHANNEL_SECRET=********************************
    export LINE_CHANNEL_ACCESS_TOKEN=********************************************************************************************************************************************
    ```

---

> [!CAUTION]
> **安全提醒：**
> 這些 Secret 與 Access Token 屬於敏感資訊，**請勿將其直接寫入程式碼或上傳至公開的 GitHub 儲存庫**。建議使用 `.env` 檔案管理，並確保該檔案已加入 `.gitignore`。

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

## Docker 部署

### Dockerfile 說明

Dockerfile 定義了如何建構 Docker 映像檔，方便將應用程式封裝並部署到任何支援 Docker 的環境中。

### 建構 Docker 映像檔

在包含 Dockerfile 的目錄下執行以下命令，建構 Docker 映像檔：

```bash
docker build -t gcr.io/iii-ntpu-ai-agent/line-bot-app .
```

### 部署至 Google Cloud Run

使用以下指令將應用程式部署至 Google Cloud Run：

```bash
gcloud run deploy line-bot-app --image gcr.io/iii-ntpu-ai-agent/line-bot-app --platform managed --region asia-southeast1 --allow-unauthenticated
```

---

## 雲端部署解說

### 使用 Google Cloud Run 部署

本專案已透過 Google Cloud Run 成功部署，以下為步驟簡要說明：

1. **進入 Google Cloud Console**
   - 登入 [Google Cloud Console](https://console.cloud.google.com/)，選擇您的專案。

2. **進入 Cloud Run**
   - 在左側選單中點擊「Cloud Run」。

3. **檢視已部署的服務**
   - 在 Cloud Run 的服務頁面，可以看到已部署的服務名稱，例如 `line-bot-app`。

4. **服務詳細資訊**
   - 點擊服務名稱進入詳細資訊頁面，可查看：
     - 部署的容器映像檔資訊。
     - 部署的地區（如 `asia-southeast1`）。
     - 服務的 URL，該 URL 即為公開的 Webhook URL。

5. **允許未經身份驗證的訪問**
   - 確保該服務已設定為「允許未經身份驗證的訪問」，以便 LINE Bot 可以正常接收訊息。

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
