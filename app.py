import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# 💡 新增：內建熱門股名稱字典，徹底取代 .info 查詢，防止被 Yahoo 封鎖
STOCK_NAMES = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2308": "台達電",
    "2881": "富邦金", "2882": "國泰金", "0050": "元大台灣50", "0056": "元大高股息",
    "2603": "長榮", "2382": "廣達"
}

# =====================================================================
# 🔮 1. 獨立的多空技術面診斷 Function
# =====================================================================
def diagnose_trend(current_price, ma5, ma20):
    """
    根據最新股價、5MA、20MA 的相對位置，回傳狀態標籤與診斷詳細文字
    """
    if pd.isna(current_price) or pd.isna(ma5) or pd.isna(ma20):
        return "盤整格局", "🔄 資料計算不足，短線方向不明確。"
        
    if current_price >= ma5 and ma5 >= ma20:
        return "多頭排列", f"增溫"
    elif current_price < ma5 and ma5 >= ma20:
        return "多頭震盪", f"震盪"
    elif current_price <= ma5 and ma5 < ma20:
        return "空頭排列", f"警戒"
    elif current_price > ma5 and ma5 < ma20:
        return "空頭反彈", f"反彈"
    else:
        return "盤整格局", "🔄 均線糾結中。"


# =====================================================================
# 🌐 2. 網頁主介面設定
# =====================================================================
st.set_page_config(page_title="台股自製看盤系統", layout="wide")
st.title("📊 台灣股市智能 K 線與多空選股系統")

# 建立安全連線會話
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
})

# 運用分頁功能切換「個股看盤」與「多空清單」
tab1, tab2 = st.tabs(["📈 個股看盤與診斷", "📋 綜合多空分類清單"])


# =====================================================================
# 📈 頁籤一：個股看盤與診斷
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
        # 單檔查詢也改用更穩定的 yf.download
        df = yf.download(target_id, period=period_map[period], session=session, progress=False)
        
        if df.empty:
            st.error("⚠️ 找不到該股票資料，請確認代號是否正確。")
        else:
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            latest = df.iloc[-1]
            
            c_p = float(latest['Close'])
            m5 = float(latest['MA5'])
            m20 = float(latest['MA20'])
            
            st.subheader("🔮 智慧多空技術面診斷")
            status, _ = diagnose_trend(c_p, m5, m20)
            
            # 個股頁面顯示詳細白話文說明
            if status == "多頭排列":
                st.success(f"📈 **【強勢多頭排列】** 目前股價（{c_p:.2f}）踩在 5MA 與 20MA 之上，且均線黃金交叉向上，屬於強勢進攻格局！")
            elif status == "多頭震盪":
                st.warning(f"⚠️ **【多頭高檔震盪】** 雖然中期還是多頭（5MA > 20MA），但短期股價已跌破 5MA，需注意高檔洗盤或獲利回吐壓力。")
            elif status == "空頭排列":
                st.error(f"📉 **【弱勢空頭排列】** 目前均線呈現死亡交叉，股價壓在 20MA（月線）下方，短期內操作建議保守、注意風險！")
            else:
                st.info(f"🔄 **【空頭低檔反彈】** 目前整體雖然還是空頭格局（5MA < 20MA），但股價已經站上 5MA 展開反彈，可觀察能否進一步站穩月線築底。")

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
# 📋 頁籤二：綜合多空分類清單 (🔥 安全速配改良版)
# =====================================================================
with tab2:
    st.subheader("📋 追蹤個股多空狀態大盤點")
    st.write("系統會自動抓取下方清單中所有股票的最新收盤價與均線，並自動分門別類。")

    default_stocks = "2330, 2317, 2454, 2308, 2881, 2882, 0050, 0056, 2603, 2382"
    stock_input = st.text_area("✍️ 編輯你要偵測的股票代號清單（請用逗號隔開）：", default_stocks)
    
    if st.button("🚀 開始全面多空大掃描"):
        pool_list = [s.strip() for s in stock_input.split(",") if s.strip()]
        
        list_bull = []       # 強勢多頭
        list_shake = []      # 多頭震盪
        list_bear = []       # 弱勢空頭
        list_rebound = []    # 空頭反彈
        list_unknown = []    # 其他/失敗
        
        with st.spinner("🚀 安全打包下載中（此新算法只需 1 次請求，絕不卡頓封鎖）..."):
            # 1. 先將所有代號轉換好後綴
            id_map = {sid: (f"{sid}.TW" if not sid.endswith(".TW") and not sid.endswith(".TWO") else sid) for sid in pool_list}
            target_ids = list(id_map.values())
            
            try:
                # 🔥 核心修正：用 yf.download 一口氣打包下載所有股票資料 (歷史資料拉 1 個月對計算 20MA 很夠用)
                all_data = yf.download(tickers=target_ids, period="1mo", group_by='ticker', session=session, progress=False)
                
                for sid in pool_list:
                    t_id = id_map[sid]
                    try:
                        # 從大資料包裡抽取單檔股票
                        if len(target_ids) == 1:
                            t_df = all_data.copy()
                        elif isinstance(all_data.columns, pd.MultiIndex) and t_id in all_data.columns.levels[0]:
                            t_df = all_data[t_id].dropna(subset=['Close'])
                        else:
                            t_df = pd.DataFrame()
                        
                        if not t_df.empty and len(t_df) >= 5:
                            # 計算均線 (如果天數不夠 20 天，則自動用現有天數 expanding 計算，避免報錯)
                            t_df['MA5'] = t_df['Close'].rolling(window=5).mean()
                            if len(t_df) >= 20:
                                t_df['MA20'] = t_df['Close'].rolling(window=20).mean()
                            else:
                                t_df['MA20'] = t_df['Close'].expanding().mean()
                            
                            t_latest = t_df.iloc[-1]
                            c_price = float(t_latest['Close'])
                            m5 = float(t_latest['MA5'])
                            m20 = float(t_latest['MA20'])
                            
                            # 從內建字典獲取中文名稱，沒有就留空
                            c_name = STOCK_NAMES.get(sid, "")
                            display_text = f"🔹 **{sid} {c_name}** (收盤: {c_price:.2f})"
                            
                            # 判定分類
                            status, _ = diagnose_trend(c_price, m5, m20)
                            
                            if status == "多頭排列": list_bull.append(display_text)
                            elif status == "多頭震盪": list_shake.append(display_text)
                            elif status == "空頭排列": list_bear.append(display_text)
                            elif status == "空頭反彈": list_rebound.append(display_text)
                            else: list_unknown.append(display_text)
                        else:
                            list_unknown.append(f"❌ {sid} (無足夠交易資料)")
                    except Exception as e:
                        list_unknown.append(f"❌ {sid} (解析錯誤)")
            except Exception as e:
                st.error(f"連線至伺服器大禮包失敗：{e}")
        
        st.success("✨ 全面掃描完成！以下是最新分類清單：")
        
        # 橫向排版展示結果
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("### 🟢 強勢多頭排列")
            if list_bull:
                for item in list_bull: st.write(item)
            else: st.write("（目前無股票符合）")
                
        with col2:
            st.markdown("### 🟡 多頭高檔震盪")
            if list_shake:
                for item in list_shake: st.write(item)
            else: st.write("（目前無股票符合）")
                
        with col3:
            st.markdown("### 🔵 空頭低檔反彈")
            if list_rebound:
                for item in list_rebound: st.write(item)
            else: st.write("（目前無股票符合）")
                
        with col4:
            st.markdown("### 🔴 弱勢空頭排列")
            if list_bear:
                for item in list_bear: st.write(item)
            else: st.write("（目前無股票符合）")

        if list_unknown:
            with st.expander("ℹ️ 未能成功分類或盤整個股"):
                for item in list_unknown: st.write(item)
