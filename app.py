from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from google import genai
from plotly.subplots import make_subplots


FMP_URL = "https://financialmodelingprep.com/stable/historical-price-eod/full"
FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"
DEFAULT_MODEL = "gemini-3.5-flash"
DEFAULT_SYMBOL = "AAPL"
MAX_ROWS_FOR_AI = 120
MAX_TABLE_ROWS = 10
VALID_SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9.\-]{1,10}$")
SETTINGS_FILE = Path(__file__).with_name(".app_settings.json")
RAINBOW_DIVIDER_HTML = (
    "<hr style='height:4px;border:none;"
    "background:linear-gradient(90deg,#ff4b4b,#ffa94d,#ffd43b,#69db7c,#4dabf7,#b197fc);'>"
)


@dataclass
class AnalysisSummary:
    start_price: float
    end_price: float
    price_change: float
    pct_change: float
    high_price: float
    low_price: float
    avg_volume: float
    latest_volume: float
    trading_days: int


def load_saved_settings() -> dict[str, str]:
    if not SETTINGS_FILE.exists():
        return {}

    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {}
    return {key: str(value) for key, value in data.items() if isinstance(value, str)}


def write_settings(settings: dict[str, str]) -> None:
    if settings:
        SETTINGS_FILE.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    elif SETTINGS_FILE.exists():
        SETTINGS_FILE.unlink()


def save_setting(key: str, value: str) -> None:
    settings = load_saved_settings()
    settings[key] = value
    write_settings(settings)


def clear_setting(key: str) -> None:
    settings = load_saved_settings()
    settings.pop(key, None)
    write_settings(settings)


def is_taiwan_symbol(symbol: str) -> bool:
    return symbol.isdigit()


def get_deployment_secret(key: str) -> str:
    try:
        value = st.secrets[key]
    except Exception:
        return ""
    return str(value).strip()


def require_access_gate() -> bool:
    access_password = get_deployment_secret("app_access_password")
    if not access_password:
        return True

    if st.session_state.get("app_authenticated"):
        return True

    st.subheader("網站進入密碼")
    st.info("這個網站只開放給收到密碼的親友使用。")
    entered_password = st.text_input("請輸入網站密碼", type="password")
    unlock_clicked = st.button("進入網站", type="primary")

    if unlock_clicked:
        if entered_password == access_password:
            st.session_state["app_authenticated"] = True
            st.rerun()
        st.error("密碼不正確，請再試一次。")

    return False


def setup_page() -> None:
    st.set_page_config(
        page_title="AI 股票趨勢分析系統",
        page_icon="📈",
        layout="wide",
    )
    st.title("AI 股票趨勢分析系統")
    st.markdown(RAINBOW_DIVIDER_HTML, unsafe_allow_html=True)


def render_sidebar() -> tuple[str, str, str, str, str, date, date, bool]:
    today = date.today()
    default_start = today - timedelta(days=90)
    saved_settings = load_saved_settings()

    saved_fmp_api_key = saved_settings.get("fmp_api_key", "")
    saved_finmind_api_token = saved_settings.get("finmind_api_token", "")
    saved_gemini_api_key = saved_settings.get("gemini_api_key", "")
    deployed_fmp_api_key = get_deployment_secret("fmp_api_key")
    deployed_finmind_api_token = get_deployment_secret("finmind_api_token")
    deployed_gemini_api_key = get_deployment_secret("gemini_api_key")

    with st.sidebar:
        st.header("分析設定")
        st.markdown(RAINBOW_DIVIDER_HTML, unsafe_allow_html=True)

        symbol = st.text_input(
            "股票代碼",
            value=DEFAULT_SYMBOL,
            help="美股可輸入 AAPL、MSFT、NVDA；台股可輸入 2330、2317 這種純數字代碼。",
        ).strip().upper()

        fmp_api_key = st.text_input(
            "FMP API Key",
            type="password",
            value="" if deployed_fmp_api_key else saved_fmp_api_key,
            help="美股查詢會用到。可到 https://financialmodelingprep.com/developer/docs 申請。",
        ).strip()
        if deployed_fmp_api_key:
            st.caption("這個版本已內建 FMP API Key，朋友不用自己輸入。")
        elif saved_fmp_api_key:
            st.caption("已記住這台電腦上的 FMP API Key。")
            if st.button("清除已記住的 FMP API Key", use_container_width=True):
                clear_setting("fmp_api_key")
                st.rerun()

        finmind_api_token = st.text_input(
            "FinMind API Token",
            type="password",
            value="" if deployed_finmind_api_token else saved_finmind_api_token,
            help="台股查詢會用到。可到 https://finmindtrade.com/ 登入後，在使用者資訊頁面取得 token。",
        ).strip()
        if deployed_finmind_api_token:
            st.caption("這個版本已內建 FinMind API Token，朋友不用自己輸入。")
        elif saved_finmind_api_token:
            st.caption("已記住這台電腦上的 FinMind API Token。")
            if st.button("清除已記住的 FinMind API Token", use_container_width=True):
                clear_setting("finmind_api_token")
                st.rerun()

        gemini_api_key = st.text_input(
            "Gemini API Key",
            type="password",
            value="" if deployed_gemini_api_key else saved_gemini_api_key,
            help="可到 https://aistudio.google.com/apikey 建立或查看。",
        ).strip()
        if deployed_gemini_api_key:
            st.caption("這個版本已內建 Gemini API Key，朋友不用自己輸入。")
        elif saved_gemini_api_key:
            st.caption("已記住這台電腦上的 Gemini API Key。")
            if st.button("清除已記住的 Gemini API Key", use_container_width=True):
                clear_setting("gemini_api_key")
                st.rerun()

        model_name = st.text_input(
            "Gemini 模型",
            value=DEFAULT_MODEL,
            help="預設使用 Gemini 3.5 Flash。可改成你帳號可用的其他 Gemini 模型。",
        ).strip()

        start_date = st.date_input(
            "起始日期",
            value=default_start,
            min_value=date(2000, 1, 1),
            max_value=today,
            help="預設為今天往前 90 天。",
        )

        end_date = st.date_input(
            "結束日期",
            value=today,
            min_value=date(2000, 1, 1),
            max_value=today,
            help="預設為今天。",
        )

        remember_keys_clicked = st.button("儲存目前金鑰", use_container_width=True)
        if remember_keys_clicked:
            try:
                if fmp_api_key:
                    save_setting("fmp_api_key", fmp_api_key)
                if finmind_api_token:
                    save_setting("finmind_api_token", finmind_api_token)
                if gemini_api_key:
                    save_setting("gemini_api_key", gemini_api_key)
                st.success("已儲存目前已輸入的金鑰。")
            except OSError:
                st.warning("這次暫時無法把金鑰記住到本機。")

        submitted = st.button("分析", type="primary", use_container_width=True)

        st.markdown("---")
        st.markdown(
            """
            ### 使用說明
            - 美股：輸入 `AAPL`、`MSFT` 這種代碼，系統會走 `FMP`。
            - 台股：輸入 `2330`、`2317` 這種純數字代碼，系統會走 `FinMind`。

            ### 免責聲明
            本系統僅根據歷史資料做技術面整理與教育性說明，不提供投資建議，也不預測未來走勢。
            歷史表現不代表未來結果，請勿把本頁內容當成買賣依據。
            """
        )

    return (
        symbol,
        fmp_api_key,
        finmind_api_token,
        gemini_api_key,
        model_name,
        start_date,
        end_date,
        submitted,
    )


def validate_inputs(
    symbol: str,
    fmp_api_key: str,
    finmind_api_token: str,
    gemini_api_key: str,
    model_name: str,
    start_date: date,
    end_date: date,
) -> bool:
    effective_fmp_api_key = fmp_api_key or get_deployment_secret("fmp_api_key")
    effective_finmind_api_token = finmind_api_token or get_deployment_secret("finmind_api_token")
    effective_gemini_api_key = gemini_api_key or get_deployment_secret("gemini_api_key")

    if not symbol:
        st.error("請先輸入股票代碼，例如 AAPL 或 2330。")
        return False
    if not VALID_SYMBOL_PATTERN.match(symbol):
        st.error("股票代碼格式看起來不正確。可用範例：AAPL、MSFT、2330。")
        return False
    if is_taiwan_symbol(symbol):
        if not effective_finmind_api_token:
            st.error("查台股時，請先輸入 FinMind API Token。")
            return False
    elif not effective_fmp_api_key:
        st.error("查美股時，請先輸入 FMP API Key。")
        return False
    if not effective_gemini_api_key:
        st.error("請先輸入 Gemini API Key。")
        return False
    if not model_name:
        st.error("請先輸入 Gemini 模型名稱。")
        return False
    if start_date > end_date:
        st.error("起始日期不能晚於結束日期。")
        return False
    return True


def fetch_us_stock_data(symbol: str, api_key: str) -> pd.DataFrame:
    params = {"symbol": symbol, "apikey": api_key}
    response = requests.get(FMP_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    if isinstance(payload, dict):
        if payload.get("Error Message"):
            raise ValueError(str(payload["Error Message"]))
        if isinstance(payload.get("historical"), list):
            payload = payload["historical"]

    if not isinstance(payload, list) or not payload:
        raise ValueError("FMP 沒有回傳可用的美股歷史價格資料。請檢查股票代碼和 API Key。")

    df = pd.DataFrame(payload)
    required_columns = ["date", "open", "high", "low", "close", "volume"]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"FMP 回傳資料缺少欄位：{', '.join(missing_columns)}")

    df = df[required_columns].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for column in ["open", "high", "low", "close", "volume"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna().sort_values("date").reset_index(drop=True)
    if df.empty:
        raise ValueError("整理後沒有剩下可分析的美股資料。")

    return df


def fetch_taiwan_stock_data(symbol: str, token: str, start_date: date, end_date: date) -> pd.DataFrame:
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": symbol,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
    }
    response = requests.get(FINMIND_URL, headers=headers, params=params, timeout=30)
    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code >= 400:
        message = payload.get("msg") if isinstance(payload, dict) else None
        raise requests.HTTPError(message or response.text or "FinMind request failed.", response=response)

    if not payload.get("status"):
        message = payload.get("msg") or "FinMind 沒有回傳可用的台股資料。"
        raise ValueError(str(message))

    rows = payload.get("data", [])
    if not isinstance(rows, list) or not rows:
        raise ValueError("FinMind 沒有回傳這檔台股的歷史價格資料。")

    df = pd.DataFrame(rows)
    required_columns = ["date", "open", "max", "min", "close", "Trading_Volume"]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"FinMind 回傳資料缺少欄位：{', '.join(missing_columns)}")

    df = df[required_columns].rename(
        columns={
            "max": "high",
            "min": "low",
            "Trading_Volume": "volume",
        }
    )
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for column in ["open", "high", "low", "close", "volume"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna().sort_values("date").reset_index(drop=True)
    if df.empty:
        raise ValueError("整理後沒有剩下可分析的台股資料。")

    return df


def filter_by_date_range(df: pd.DataFrame, start_date: date, end_date: date) -> pd.DataFrame:
    filtered = df.loc[
        (df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)
    ].copy()
    if filtered.empty:
        raise ValueError("這個日期範圍內沒有交易資料，請調整日期後再試一次。")
    return filtered.reset_index(drop=True)


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    enriched = df.copy()
    enriched = enriched.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)

    for period in [5, 10, 20, 60]:
        enriched[f"MA{period}"] = enriched["close"].rolling(window=period, min_periods=period).mean()

    enriched["daily_range"] = enriched["high"] - enriched["low"]
    enriched["return_pct"] = np.where(
        enriched["close"].shift(1).notna(),
        (enriched["close"] - enriched["close"].shift(1)) / enriched["close"].shift(1) * 100,
        np.nan,
    )
    return enriched


def summarize_data(df: pd.DataFrame) -> AnalysisSummary:
    start_price = float(df["close"].iloc[0])
    end_price = float(df["close"].iloc[-1])
    price_change = end_price - start_price
    pct_change = (price_change / start_price * 100) if start_price else 0.0

    return AnalysisSummary(
        start_price=start_price,
        end_price=end_price,
        price_change=price_change,
        pct_change=pct_change,
        high_price=float(df["high"].max()),
        low_price=float(df["low"].min()),
        avg_volume=float(df["volume"].mean()),
        latest_volume=float(df["volume"].iloc[-1]),
        trading_days=int(len(df)),
    )


def create_price_chart(symbol: str, df: pd.DataFrame, start_date: date, end_date: date) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.75, 0.25],
    )

    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="K線",
            increasing_line_color="#d62728",
            decreasing_line_color="#2ca02c",
        ),
        row=1,
        col=1,
    )

    ma_colors = {
        "MA5": "#ff7f0e",
        "MA10": "#1f77b4",
        "MA20": "#9467bd",
        "MA60": "#8c564b",
    }
    for ma_name, color in ma_colors.items():
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df[ma_name],
                mode="lines",
                name=ma_name,
                line={"width": 2, "color": color},
            ),
            row=1,
            col=1,
        )

    volume_colors = np.where(df["close"] >= df["open"], "#d62728", "#2ca02c")
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["volume"],
            name="成交量",
            marker_color=volume_colors,
            opacity=0.7,
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        title=f"{symbol} 股價 K 線圖與移動平均線 ({start_date} 至 {end_date})",
        height=760,
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        margin=dict(l=20, r=20, t=70, b=20),
    )
    fig.update_yaxes(title_text="價格", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    fig.update_xaxes(title_text="日期", row=2, col=1)
    return fig


def render_metrics(summary: AnalysisSummary) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric("起始價格", f"{summary.start_price:,.2f}")
    col2.metric("結束價格", f"{summary.end_price:,.2f}")
    col3.metric(
        "價格變化",
        f"{summary.pct_change:,.2f}%",
        delta=f"{summary.price_change:,.2f}",
    )


def render_overview(summary: AnalysisSummary, market_label: str) -> None:
    st.markdown("### 基本統計資訊")
    st.write(
        f"這段期間共有 **{summary.trading_days}** 個交易日。"
        f" 最高價為 **{summary.high_price:,.2f}**，最低價為 **{summary.low_price:,.2f}**，"
        f" 平均成交量約 **{summary.avg_volume:,.0f}**。"
    )
    st.write(
        f"本次資料來源是 **{market_label}**。"
        f" 最新一天成交量約 **{summary.latest_volume:,.0f}**。"
    )


def render_indicator_notes() -> None:
    with st.expander("技術指標說明", expanded=False):
        st.markdown(
            """
            - `MA5`：最近 5 個交易日收盤價平均，常用來看很短期的價格節奏。
            - `MA10`：最近 10 個交易日收盤價平均，常用來看短期方向。
            - `MA20`：最近 20 個交易日收盤價平均，常用來看一個月左右的走勢。
            - `MA60`：最近 60 個交易日收盤價平均，常用來看較中期的趨勢。
            - `成交量`：反映每天交易熱度，常搭配價格變動一起觀察。
            """
        )


def build_ai_dataset(symbol: str, df: pd.DataFrame, summary: AnalysisSummary, market_label: str) -> tuple[str, dict[str, Any]]:
    trimmed = df.tail(MAX_ROWS_FOR_AI).copy()
    trimmed["date"] = trimmed["date"].dt.strftime("%Y-%m-%d")

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "MA5",
        "MA10",
        "MA20",
        "MA60",
        "daily_range",
        "return_pct",
    ]
    for column in numeric_columns:
        if column in trimmed.columns:
            trimmed[column] = trimmed[column].round(4)

    payload = {
        "symbol": symbol,
        "market_label": market_label,
        "first_date": trimmed["date"].iloc[0],
        "last_date": trimmed["date"].iloc[-1],
        "start_price_value": round(summary.start_price, 2),
        "end_price_value": round(summary.end_price, 2),
        "price_change_pct": round(summary.pct_change, 2),
        "data": trimmed.to_dict(orient="records"),
    }
    return json.dumps(payload["data"], ensure_ascii=False, indent=2), payload


def generate_ai_analysis(
    symbol: str,
    model_name: str,
    api_key: str,
    df: pd.DataFrame,
    summary: AnalysisSummary,
    market_label: str,
) -> str:
    client = genai.Client(api_key=api_key)
    data_json, payload = build_ai_dataset(symbol, df, summary, market_label)

    system_message = """
你是一位專業的技術分析師，專精於股票技術分析和歷史數據解讀。

重要原則：
- 僅提供歷史數據分析和技術指標解讀，絕不提供任何投資建議或預測
- 保持完全客觀中立的分析態度
- 使用專業術語但保持易懂
- 所有分析僅供教育和研究目的
- 強調技術分析的局限性和不確定性
- 使用繁體中文回答

嚴格的表達方式要求：
- 使用「歷史數據顯示」、「技術指標反映」、「過去走勢呈現」等客觀描述
- 避免「可能性」、「預期」、「建議」、「關注」等暗示性用詞
- 不提供任何操作建議
- 強調「歷史表現不代表未來結果」
""".strip()

    user_message = f"""
請基於以下股票歷史數據進行深度技術分析：

### 基本資訊
- 市場：{payload["market_label"]}
- 股票代號：{symbol}
- 分析期間：{payload["first_date"]} 至 {payload["last_date"]}
- 期間價格變化：{payload["price_change_pct"]:.2f}% (從 {payload["start_price_value"]:.2f} 變化到 {payload["end_price_value"]:.2f})

### 完整交易數據
{data_json}

### 分析方向
1. 趨勢分析
2. 移動平均線分析
3. 成交量與價格關係
4. 波動性與關鍵轉折
5. 風險提醒與歷史資料限制

### 輸出要求
- 分段清楚
- 盡量引用具體數字
- 結尾再次提醒這只是教育用途的歷史技術分析
""".strip()

    response = client.models.generate_content(
        model=model_name,
        contents=f"{system_message}\n\n{user_message}",
    )
    return (response.text or "").strip()


def render_data_table(df: pd.DataFrame) -> None:
    st.markdown("### 歷史數據表格")
    display_df = df.tail(MAX_TABLE_ROWS).sort_values("date", ascending=False).copy()
    display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")

    ordered_columns = ["date", "open", "high", "low", "close", "volume", "MA5", "MA10", "MA20", "MA60"]
    display_df = display_df[ordered_columns].rename(
        columns={
            "date": "日期",
            "open": "開盤",
            "high": "最高",
            "low": "最低",
            "close": "收盤",
            "volume": "成交量",
        }
    )
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def show_intro() -> None:
    st.info(
        "請在左側依序輸入股票代碼、對應市場的資料金鑰、Gemini API Key，再按下「分析」。"
        " 系統會自動判斷：純數字代碼走台股 FinMind，其他常見股票代碼走美股 FMP。"
    )


def main() -> None:
    setup_page()
    if not require_access_gate():
        return
    show_intro()
    (
        symbol,
        fmp_api_key,
        finmind_api_token,
        gemini_api_key,
        model_name,
        start_date,
        end_date,
        submitted,
    ) = render_sidebar()

    if not submitted:
        return

    if not validate_inputs(symbol, fmp_api_key, finmind_api_token, gemini_api_key, model_name, start_date, end_date):
        return

    fmp_api_key = fmp_api_key or get_deployment_secret("fmp_api_key")
    finmind_api_token = finmind_api_token or get_deployment_secret("finmind_api_token")
    gemini_api_key = gemini_api_key or get_deployment_secret("gemini_api_key")

    for key_name, key_value, label in [
        ("fmp_api_key", fmp_api_key, "FMP API Key"),
        ("finmind_api_token", finmind_api_token, "FinMind API Token"),
        ("gemini_api_key", gemini_api_key, "Gemini API Key"),
    ]:
        if key_value:
            try:
                save_setting(key_name, key_value)
            except OSError:
                st.warning(f"{label} 這次可正常使用，但暫時無法記住到本機。")

    market_label = "台股 FinMind" if is_taiwan_symbol(symbol) else "美股 FMP"

    try:
        if is_taiwan_symbol(symbol):
            st.info("正在向 FinMind 取得台股歷史股價資料...")
            raw_df = fetch_taiwan_stock_data(symbol, finmind_api_token, start_date, end_date)
        else:
            st.info("正在向 FMP 取得美股歷史股價資料...")
            raw_df = fetch_us_stock_data(symbol, fmp_api_key)

        st.info("正在依日期範圍整理資料並計算技術指標...")
        filtered_df = filter_by_date_range(raw_df, start_date, end_date)
        analysis_df = add_technical_indicators(filtered_df)
        summary = summarize_data(analysis_df)
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "未知"
        if is_taiwan_symbol(symbol):
            error_detail = ""
            try:
                payload = exc.response.json() if exc.response is not None else {}
                if isinstance(payload, dict) and payload.get("msg"):
                    error_detail = f" 系統訊息：{payload['msg']}"
            except Exception:
                error_detail = ""
            st.error(
                f"FinMind 連線失敗，錯誤代碼是 {status_code}。"
                " 請先檢查台股代碼和 FinMind API Token 是否正確。"
                f"{error_detail}"
            )
        else:
            st.error(
                f"FMP 連線失敗，錯誤代碼是 {status_code}。"
                " 請先檢查股票代碼和 FMP API Key 是否正確，或稍後再試。"
            )
        return
    except Exception as exc:
        st.error(f"資料處理失敗：{exc}")
        return

    if summary.trading_days < 60:
        st.warning("這段期間少於 60 個交易日，MA60 可能會有很多空白，這是正常現象。")
    if summary.trading_days > 365:
        st.warning("這次分析的資料筆數較多，AI 分析只會取最近 120 筆，避免等待太久。")

    st.success(f"資料已整理完成，來源：{market_label}")

    st.markdown("## 股價K線圖與技術指標")
    st.plotly_chart(
        create_price_chart(symbol, analysis_df, start_date, end_date),
        use_container_width=True,
    )

    render_metrics(summary)
    render_overview(summary, market_label)
    render_indicator_notes()

    st.markdown("## AI技術分析")
    st.info("AI 會根據這段歷史資料做客觀整理，只提供教育性說明，不提供買賣建議。")
    try:
        with st.spinner("Gemini 正在分析中..."):
            ai_analysis = generate_ai_analysis(
                symbol,
                model_name,
                gemini_api_key,
                analysis_df,
                summary,
                market_label,
            )
        st.markdown(ai_analysis)
    except Exception as exc:
        st.error(
            "AI 分析暫時無法完成。請先確認 Gemini API Key 和模型名稱是否可用。"
            f" 系統回報：{exc}"
        )

    render_data_table(analysis_df)


if __name__ == "__main__":
    main()
