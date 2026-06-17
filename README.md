# AI 股票趨勢分析系統

這是一個用 `Streamlit` 製作的網頁工具。你只要輸入股票代碼和對應的 API 金鑰，就能在瀏覽器看到：

- 歷史股價資料
- K 線圖與 MA5、MA10、MA20、MA60
- 基本價格統計
- Gemini 技術面分析
- 最近 10 筆交易資料表

資料來源會自動切換：

- 美股：使用 `FMP`
- 台股：使用 `FinMind`

## 需要準備

- Python
- FMP API Key
- FinMind API Token
- Gemini API Key

## 安裝

```powershell
python -m pip install -r requirements.txt
```

## 啟動

```powershell
python -m streamlit run app.py
```

啟動後，瀏覽器會開啟本系統頁面。

## 一鍵啟動

如果你不想自己輸入指令，可以直接雙擊：

`start_app.bat`

它會幫你做下面幾件事：

- 自動安裝需要的套件
- 自動啟動股票分析系統

之後大多數情況下，你只要再雙擊同一個檔案就能開啟。

## 使用方式

1. 左側輸入美股代碼，例如 `AAPL`
2. 如果是美股，輸入 `FMP API Key`
3. 如果是台股，輸入 `FinMind API Token`
4. 輸入 `Gemini API Key`
5. 視需要調整日期範圍
6. 按下 `分析`

## 注意

- 這個工具只做歷史資料整理與教育性技術分析，不提供投資建議。
- 台股請輸入純數字代碼，例如 `2330`、`2317`。
- 美股請輸入常見代碼，例如 `AAPL`、`MSFT`。
- FinMind API Token 可到 `https://finmindtrade.com/` 登入後，在使用者資訊頁面取得。
- Gemini API Key 可到 `https://aistudio.google.com/apikey` 建立或查看。
- 預設模型是 `gemini-3.5-flash`，如果你的帳號有別的可用 Gemini 模型，也可以自行改掉。

## 上網分享

如果你要把這個系統發布在網路上，最簡單的做法通常是：

1. 把這個專案上傳到 GitHub
2. 用 Streamlit Community Cloud 連接這個 GitHub 專案
3. 在部署平台的 Secrets 裡填入：
   - `fmp_api_key`
   - `finmind_api_token`
   - `gemini_api_key`
4. 發布後，把網址分享給親友

重要：

- 不要把 `.app_settings.json` 或 `.streamlit/secrets.toml` 上傳到 GitHub。
- 這個專案已經附上 `.gitignore`，會幫你避開這些敏感檔案。
- 如果你把 API Key 直接寫進公開程式碼，別人可能會盜用你的額度。
