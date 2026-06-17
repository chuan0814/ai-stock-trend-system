# GitHub 上傳 + Streamlit 發布清單

這份清單是給「把這套 AI 股票趨勢分析系統發布到網路上，分享給親友」用的。

## 先準備

你需要先有：

- GitHub 帳號
- Streamlit Community Cloud 帳號
- 3 個金鑰
  - `FMP API Key`
  - `FinMind API Token`
  - `Gemini API Key`
- 1 組你自己決定的網站進入密碼

## 第 1 步：確認敏感資料不要上傳

這個專案已經有 `.gitignore`，會避開下面這些檔案：

- `.app_settings.json`
- `.streamlit/secrets.toml`
- `.venv`
- `.python_packages`

這些檔案不要放到公開 GitHub。

## 第 2 步：建立 GitHub repository

1. 登入 GitHub
2. 按右上角 `New repository`
3. 輸入專案名稱
   - 例如：`ai-stock-trend-system`
4. 選 `Private` 或 `Public`

建議：

- 如果只是先測試，選 `Private`
- 如果之後想公開展示，再改成 `Public`

## 第 3 步：把專案上傳到 GitHub

在這個專案資料夾執行：

```powershell
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin 你的GitHub倉庫網址
git push -u origin main
```

如果你的電腦還沒裝 Git，先安裝 Git 再做這一步。

## 第 4 步：到 Streamlit Community Cloud 建立部署

1. 打開 Streamlit Community Cloud
2. 登入
3. 選 `New app`
4. 連接你的 GitHub repository
5. 選：
   - Repository：你的專案
   - Branch：`main`
   - Main file path：`app.py`

## 第 5 步：設定 Secrets

在 Streamlit 的 app 設定裡，找到 `Secrets`，填入下面內容：

```toml
fmp_api_key = "你的FMP金鑰"
finmind_api_token = "你的FinMind token"
gemini_api_key = "你的Gemini金鑰"
app_access_password = "你要分享給親友的網站密碼"
```

這樣做完之後：

- 親友不用自己輸入 API Key
- 只有知道網站密碼的人才能進入

## 第 6 步：按下部署

Secrets 填好後，按 `Deploy`。

部署完成後，會得到一個公開網址。

## 第 7 步：把網址和密碼分享給親友

你只需要分享兩樣東西：

1. 網站網址
2. 網站進入密碼

不要分享 API Key 本身。

## 建議做法

- 先用 `Private repository` 測試
- 先自己打開網址確認正常
- 再分享給少量親友
- 如果之後人變多，再考慮加更多限制

## 如果你想再更安全

之後還可以再加：

- 每日使用次數限制
- 指定 email 才能登入
- 只開放特定朋友名單
- 隱藏某些高成本分析功能
