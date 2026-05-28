import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# =====================================================================
# 🔮 1. 獨立的多空技術面診斷 Function
# =====================================================================
def diagnose_trend(current_price, ma5, ma20):
    """
    根據最新股價、5MA、20MA 的相對位置，回傳狀態標籤與診斷詳細文字
    """
    if current_price >= ma5 and ma5 >= ma20:
        return "多頭排列", f"📈 **【強勢多頭排列】** 目前股價（{current_price:.2f}）踩在 5MA 與 20MA 之上，且均線黃金交叉向上，屬於強勢進攻格局！"
    elif current_price < ma5 and ma5 >= ma20:
        return "多頭震盪", f"⚠️ **【多頭高檔震盪】** 雖然中期還是多頭（5MA > 20MA），但短期股價已跌破 5MA，需注意高檔洗盤或獲利回吐壓力。"
    elif current_price <= ma5 and ma5 < ma20:
        return "空頭排列", f"📉 **【弱勢空頭排列】** 目前均線呈現死亡交叉，股價壓在 20MA（月線）下方，短期內操作建議保守、注意風險！"
    elif current_price > ma5 and ma5 < ma20:
        return "空頭反彈", f"🔄 **【空頭低檔反彈】** 目前整體雖然還是空頭格局（5MA < 20MA），但股價已經站上 5MA 展開反彈，可觀察能否進一步站穩月線築底。"
    else:
        return "盤整格局", "🔄 **【盤整格局】** 均線糾結，短線方向不明確。"


# =====================================================================
# 🌐 2. 網頁主介面設定
# =====================================================================
st.set_page_config(page_title="台股自製看盤系統", layout="wide")
st.title("📊 台灣股市智能 K 線與多空選股系統")

# 建立安全連線會話（防止 Yahoo Finance 阻擋）
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
})

# 運用分頁功能切換「個股看盤」與「多空清單」
tab1, tab2 = st.tabs(["📈 個股看盤與診斷", "📋 綜合多空分類清單"])


# =====================================================================
# 📈 頁籤一：個股看盤與診斷 (原功能保留並優化)
# =====================================================================
with tab1:
    st.sidebar.header("⚙️ 個股看盤參數")
    stock_id = st.sidebar.text_input("請輸入台股代號：", "2330", key="single_stock")
    period = st.sidebar.selectbox("請選擇時間區間：", ["1個月","3個月", "6個月", "1年","5年"], key="single_period")
    period_map = {"1個月": "1mo", "3個月": "3mo", "6個月": "6mo", "1年": "1y", "5年": "5y"}

    if not stock_id.endswith(".TW") and not stock_id.endswith(".TWO"):
        target_id = f"{stock_id}.TW"
    else:
        target_id = stock_id

    try:
        ticker = yf.Ticker(target_id, session=session)
        df = ticker.history(period=period_map[period])
        
        if df.empty:
            st.error("⚠️ 找不到該股票資料，請確認代號是否正確。")
        else:
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            latest = df.iloc[-1]
            
            st.subheader("🔮 智慧多空技術面診斷")
            status, alert_message = diagnose_trend(latest['Close'], latest['MA5'], latest['MA20'])
            
            if status == "多頭排列": st.success(alert_message)
            elif status == "多頭震盪": st.warning(alert_message)
            elif status == "空頭排列": st.error(alert_message)
            else: st.info(alert_message)

            # 繪製 K 線圖
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線",
                increasing_line_color='#FF3333', increasing_fillcolor='#FF3333',
                decreasing_line_color='#00AA00', decreasing_fillcolor='#00AA00'
            ), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5MA', line=dict(color='orange', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20MA', line=dict(color='deepskyblue', width=1.5)), row=1, col=1)
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='dimgray'), row=2, col=1)
            fig.update_layout(title=f"📈 {stock_id} - 歷史技術線圖", xaxis_rangeslider_visible=False, height=600, template="plotly_dark", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"讀取資料時發生錯誤：{e}")


# =====================================================================
# 📋 頁籤二：綜合多空分類清單 (✨ 全新開發功能)
# =====================================================================
with tab2:
    st.subheader("📋 追蹤個股多空狀態大盤點")
    st.write("系統會自動抓取下方清單中所有股票的最新收盤價與均線，並自動分門別類。")

    # 預設一組台灣熱門的股票清單，使用者也可以在網頁上自己修改增減
    default_stocks = "2330, 2317, 2454, 2308, 2881, 2882, 0050, 0056, 2603, 2382"
    stock_input = st.text_area("✍️ 編輯你要偵測的股票代號清單（請用逗號隔開）：", default_stocks)
    
    # 按下按鈕後才開始執行掃描，避免網頁一直重複載入
    if st.button("🚀 開始全面多空大掃描"):
        # 將輸入的字串拆解成獨立的代號清單
        pool_list = [s.strip() for s in stock_input.split(",") if s.strip()]
        
        # 準備四個狀況的空箱子（List）
        list_bull = []       # 強勢多頭
        list_shake = []      # 多頭震盪
        list_bear = []       # 弱勢空頭
        list_rebound = []    # 空頭反彈
        list_unknown = []    # 其他/盤整
        
        # 顯示進度條
        with st.spinner("正在安全下載各股數據並進行智慧分類中，請稍候..."):
            for sid in pool_list:
                # 處理台股後綴
                if not sid.endswith(".TW") and not sid.endswith(".TWO"):
                    t_id = f"{sid}.TW"
                else:
                    t_id = sid
                
                try:
                    # 抓取最近 1 個月的資料即可（計算20MA綽綽有餘，加快速度）
                    t_ticker = yf.Ticker(t_id, session=session)
                    t_df = t_ticker.history(period="1mo")
                    
                    if not t_df.empty and len(t_df) >= 20:
                        t_df['MA5'] = t_df['Close'].rolling(window=5).mean()
                        t_df['MA20'] = t_df['Close'].rolling(window=20).mean()
                        
                        t_latest = t_df.iloc[-1]
                        c_price = t_latest['Close']
                        m5 = t_latest['MA5']
                        m20 = t_latest['MA20']
                        
                        # 獲利股票中英文名稱（如果抓不到就顯示代號）
                        stock_name = t_ticker.info.get('shortName', sid)
                        display_text = f"🔹 **{sid} {stock_name}** (收盤價: {c_price:.2f})"
                        
                        # 呼叫診斷邏輯進行分類
                        status, _ = diagnose_trend(c_price, m5, m20)
                        
                        if status == "多頭排列": list_bull.append(display_text)
                        elif status == "多頭震盪": list_shake.append(display_text)
                        elif status == "空頭排列": list_bear.append(display_text)
                        elif status == "空頭反彈": list_rebound.append(display_text)
                        else: list_unknown.append(display_text)
                except:
                    # 萬一某一檔股票抓取失敗，自動跳過不讓整個程式當掉
                    list_unknown.append(f"❌ {sid} (讀取失敗)")
        
        st.success("✨ 全面掃描完成！以下是分類清單：")
        
        # 運用 Streamlit 的 4 個區塊（Columns）橫向排版展示結果
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("### 🟢 強勢多頭排列")
            if list_bull:
                for item in list_bull: st.write(item)
            else:
                st.write("（目前無股票符合）")
                
        with col2:
            st.markdown("### 🟡 多頭高檔震盪")
            if list_shake:
                for item in list_shake: st.write(item)
            else:
                st.write("（目前無股票符合）")
                
        with col3:
            st.markdown("### 🔵 空頭低檔反彈")
            if list_rebound:
                for item in list_rebound: st.write(item)
            else:
                st.write("（目前無股票符合）")
                
        with col4:
            st.markdown("### 🔴 弱勢空頭排列")
            if list_bear:
                for item in list_bear: st.write(item)
            else:
                st.write("（目前無股票符合）")

        # 如果有錯誤或未分類的顯示在最下方
        if list_unknown:
            with st.expander("ℹ️ 未能成功分類或盤整個股"):
                for item in list_unknown: st.write(item)
