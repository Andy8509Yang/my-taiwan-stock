from datetime import datetime
import pandas as pd
import streamlit as st
import yfinance as yf

# 網頁基本設定
st.set_page_config(
    page_title="台股多空技術面自動篩選器", page_icon="📈", layout="wide"
)

st.title("📈 台股多空技術面自動篩選器")
st.markdown(
    "根據台股傳統量價理論與均線流派，自動掃描並篩選目前市場上的**多頭爆量股**與**空頭下沉股**。"
)

# 預設追蹤的台股熱門權值股名單 (可自行修改或增加)
DEFAULT_STOCKS = {
    "2330.TW": "台積電",
    "2317.TW": "鴻海",
    "2454.TW": "聯發科",
    "2308.TW": "台達電",
    "2303.TW": "聯電",
    "2382.TW": "廣達",
    "2881.TW": "富邦金",
    "2882.TW": "國泰金",
    "2891.TW": "中信金",
    "2412.TW": "中華電",
    "1301.TW": "台塑",
    "2002.TW": "中鋼",
    "2603.TW": "長榮",
    "2609.TW": "陽明",
    "2357.TW": "華碩",
    "3008.TW": "大立光",
    "3231.TW": "緯創",
    "2324.TW": "仁寶",
    "2886.TW": "兆豐金",
    "5880.TW": "合庫金",
}


# 使用 Streamlit 快取機制，一小時內重複打開網頁不重新抓取，大幅提升速度
@st.cache_data(ttl=3600)
def fetch_and_analyze(stock_dict):
    bullish_list = []
    bearish_list = []
    neutral_list = []

    # 進度條設定
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, (ticker, name) in enumerate(stock_dict.items()):
        status_text.text(f"正在分析: {ticker} {name}...")
        progress_bar.progress((idx + 1) / len(stock_dict))

        try:
            # 獲取半年歷史數據
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo")

            if len(df) < 60:
                continue

            # 技術指標計算
            df["5MA"] = df["Close"].rolling(window=5).mean()
            df["20MA"] = df["Close"].rolling(window=20).mean()
            df["60MA"] = df["Close"].rolling(window=60).mean()
            df["5VMA"] = df["Volume"].rolling(window=5).mean()

            # 取得最新兩天的資料
            today = df.iloc[-1]
            yesterday = df.iloc[-2]

            current_price = round(today["Close"], 2)
            price_change = round(today["Close"] - yesterday["Close"], 2)
            pct_change = round((price_change / yesterday["Close"]) * 100, 2)

            stock_info = {
                "代號": ticker.split(".")[0],
                "股名": name,
                "現價": current_price,
                "漲跌": f"{price_change} ({pct_change}%)",
                "今日成交量": int(today["Volume"]),
                "5日均量": int(yesterday["5VMA"]),
            }

            # 判斷多頭邏輯
            is_bullish_ma = (
                today["Close"] > today["5MA"] > today["20MA"] > today["60MA"]
            )
            is_slope_up = (today["20MA"] > yesterday["20MA"]) and (
                today["60MA"] > yesterday["60MA"]
            )
            is_volume_up = today["Volume"] > (yesterday["5VMA"] * 1.5)

            # 判斷空頭邏輯
            is_bearish_ma = (
                today["Close"] < today["5MA"] < today["20MA"] < today["60MA"]
            )
            is_slope_down = (today["20MA"] < yesterday["20MA"]) and (
                today["60MA"] < yesterday["60MA"]
            )

            if is_bullish_ma and is_slope_up and is_volume_up:
                stock_info["狀態"] = "多頭爆量衝刺"
                bullish_list.append(stock_info)
            elif is_bearish_ma and is_slope_down:
                stock_info["狀態"] = "空頭下沉型態"
                bearish_list.append(stock_info)
            else:
                stock_info["狀態"] = "區間盤整"
                neutral_list.append(stock_info)

        except Exception as e:
            continue

    status_text.empty()
    progress_bar.empty()

    return (
        pd.DataFrame(bullish_list),
        pd.DataFrame(bearish_list),
        pd.DataFrame(neutral_list),
    )


# 執行按鈕
if st.button("🔄 立即掃描市場多空狀態", type="primary"):
    bullish_df, bearish_df, neutral_df = fetch_and_analyze(DEFAULT_STOCKS)

    # 建立分頁標籤
    tab1, tab2, tab3 = st.tabs(
        [
            f"🔥 多頭爆量衝刺股 ({len(bullish_df)})",
            f"⚠️ 空頭下沉型態股 ({len(bearish_df)})",
            f"⚖️ 盤整個股 ({len(neutral_df)})",
        ]
    )

    with tab1:
        st.subheader("📈 符合條件：價在均線上 ＋ 均線向上 ＋ 今日爆量")
        if not bullish_df.empty:
            st.dataframe(bullish_df, use_container_width=True, hide_index=True)
        else:
            st.info("目前追蹤名單中，沒有個股符合多頭爆量條件。")

    with tab2:
        st.subheader("📉 符合條件：價在均線下 ＋ 均線下彎 ＋ 趨勢走弱")
        if not bearish_df.empty:
            st.dataframe(bearish_df, use_container_width=True, hide_index=True)
        else:
            st.info("目前追蹤名單中，沒有個股符合空頭下沉條件。")

    with tab3:
        st.subheader("📋 橫盤整理或動能未連續之個股")
        if not neutral_df.empty:
            st.dataframe(neutral_df, use_container_width=True, hide_index=True)
        else:
            st.info("暫無資料。")
else:
    st.info("請點擊上方按鈕開始進行多空篩選。")
