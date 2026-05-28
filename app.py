import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# =====================================================================
# 🌐 0. 雲端即時抓取全台股「上市+上櫃」股票與 ETF 清單
# =====================================================================
@st.cache_data(ttl=86400)  # 💡 快取 24 小時，每天只會偷偷下載一次，完全不影響網頁速度
def load_all_taiwan_stocks():
    """
    直接連線台灣證券交易所(TWSE)官方對應表，抓取全台灣所有最新股票與 ETF 代號名稱
    """
    stock_dict = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # 1. 抓取上市股票與 ETF (含 0050, 0056 等)
    try:
        res = requests.get("https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", headers=headers, timeout=10)
        res.encoding = 'big5'  # 證交所舊網站使用 Big5 編碼
        dfs = pd.read_html(res.text)
        if dfs:
            df = dfs[0]
            for val in df[0]:
                if pd.isna(val): continue
                parts = str(val).split() # 自動拆開 "2330　台積電"
                if len(parts) >= 2:
                    code, name = parts[0], parts[1]
                    # 篩選標準台股代碼 (4碼或6碼純數字，過濾權證與特別股)
                    if code.isdigit() and (len(code) == 4 or len(code) == 6):
                        stock_dict[code] = name
    except Exception:
        pass # 若網路異常則跳過
        
    # 2. 抓取上櫃股票與 ETF
    try:
        res = requests.get("https://isin.twse.com.tw/isin/C_public.jsp?strMode=4", headers=headers, timeout=10)
        res.encoding = 'big5'
        dfs = pd.read_html(res.text)
        if dfs:
            df = dfs[0]
            for val in df[0]:
                if pd.isna(val): continue
                parts = str(val).split()
                if len(parts) >= 2:
                    code, name = parts[0], parts[1]
                    if code.isdigit() and (len(code) == 4 or len(code) == 6):
                        stock_dict[code] = name
    except Exception:
        pass
        
    # 3. 終極防護保底：如果政府網站剛好斷線維修，啟用這份備用名單防止網頁壞掉
    if not stock_dict:
        stock_dict = {
            "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2308": "台達電",
            "2881": "富邦金", "2882": "國泰金", "0050": "元大台灣50", "0056": "元大高股息",
            "2603": "長榮", "2382": "廣達"
        }
    return stock_dict

# 立即啟動全台股資料庫載入
all_stocks = load_all_taiwan_stocks()


# =====================================================================
# 🔮 1. 獨立的多空技術面診斷 Function
# =====================================================================
def diagnose_trend(current_price, ma5, ma20):
    try:
        c_p = float(current_price)
        m5 = float(ma5)
        m20 = float(ma20)
    except Exception:
        return "盤整格局", "🔄 資料計算異常，短線方向不明確。"

    if pd.isna(c_p) or pd.isna(m5) or pd.isna(m20):
        return "盤整格局", "🔄 資料不足，無法判斷。"
        
    if c_p >= m5 and m5 >= m20:
        return "多頭排列", f"📈 **【強勢多頭排列】** 目前股價（{c_p:.2f}）踩在 5MA 與 20MA 之上，且均線黃金交叉向上，屬於強勢進攻格局！"
    elif c_p < m5 and m5 >= m20:
        return "多頭震盪", f"⚠️ **【多頭高檔震盪】** 雖然中期還是多頭（5MA > 20MA），但短期股價已跌破 5MA，需注意高檔洗盤或獲利回吐壓力。"
    elif c_p <= m5 and m5 < m20:
        return "空頭排列", f"📉 **【弱勢空頭排列】** 目前均線呈現死亡交叉，股價壓在 20MA（月線）下方，短期內操作建議保守、注意風險！"
    elif c_p > m5 and m5 < m20:
        return "空頭反彈", f"🔄 **【空頭低檔反彈】** 目前整體雖然還是空頭格局（5MA < 20MA），但股價已經站上 5MA 展開反彈，可觀察能否進一步站穩月線築底。"
    else:
        return "盤整格局", "🔄 **【盤整格局】** 均線糾結，短線方向不明確。"


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
# 📈 頁籤一：個股看盤與診斷 (🔥 升級：智慧聯想搜尋輸入框)
# =====================================================================
with tab1:
    st.sidebar.header("⚙️ 個股看盤參數")
    
    # 💡 將全台股字典打包成 "代號 - 名稱" 的格式，例如 "2330 - 台積電"
    stock_options = [f"{code} - {name}" for code, name in all_stocks.items()]
    
    # 自動尋找「2330 - 台積電」在清單中的位置作為初始預設值
    default_index = 0
    for i, option in enumerate(stock_options):
        if option.startswith("2330"):
            default_index = i
            break
            
    # 🔥 關鍵改良：改用 selectbox，Streamlit 網頁上只要對它打字，就會啟動像 Google 一樣的即時聯想過濾
    selected_stock = st.sidebar.selectbox(
        "請輸入股票代號或名稱：",
        options=stock_options,
        index=default_index,
        key="cool_search_box"
    )
    
    # 從選中的文字中切出真正的股票代號 (例如從 "2330 - 台積電" 拿取 "2330")
    stock_id = selected_stock.split(" - ")[0]
    
    period = st.sidebar.selectbox("請選擇時間區間：", ["1個月","3個月", "6個月", "1年","5年"], key="single_period")
    period_map = {"1個月": "1mo", "3個月": "3mo", "6個月": "6mo", "1年": "1y", "5年": "5y"}

    if not stock_id.endswith(".TW") and not stock_id.endswith(".TWO"):
        # 簡單區分上市上櫃後綴 (大部分上櫃是數字較大或特定代號，這裡用全方位測試防錯)
        target_id = f"{stock_id}.TW"
    else:
        target_id = stock_id

    try:
        # 單股查詢
        ticker_obj = yf.Ticker(target_id, session=session)
        df = ticker_obj.history(period=period_map[period])
        
        # 如果用 .TW 找不到，自動切換成 .TWO (上櫃市場) 再試一次
        if df.empty:
            target_id = f"{stock_id}.TWO"
            df = yf.Ticker(target_id, session=session).history(period=period_map[period])

        if df.empty:
            st.error("⚠️ 找不到該股票資料，請確認代號是否正確。")
        else:
            # 計算均線
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            
            latest = df.iloc[-1]
            c_p = float(latest['Close'])
            m5 = float(latest['MA5'])
            m20 = float(latest['MA20'])
            
            # 顯示當前看盤的股票完整名稱
            st.subheader(f"🔮 {selected_stock} - 智慧多空技術面診斷")
            status, alert_message = diagnose_trend(c_p, m5, m20)
            
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
            fig.update_layout(title=f"📈 {selected_stock} - 歷史技術線圖", xaxis_rangeslider_visible=False, height=600, template="plotly_dark", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"個股讀取資料時發生錯誤：{e}")


# =====================================================================
# 📋 頁籤二：綜合多空分類清單 (🔥 升級：共用全台股中文大字典)
# =====================================================================
with tab2:
    st.subheader("📋 追蹤個股多空狀態大盤點")
    st.write("系統會自動抓取下方清單中所有股票的最新收盤價與均線，並自動分門別類。")

    default_stocks = "2330, 2317, 2454, 2308, 2881, 2882, 0050, 0056, 2603, 2382"
    stock_input = st.text_area("✍️ 編輯你要偵測的股票代號清單（請用逗號隔開）：", default_stocks)
    
    if st.button("🚀 開始全面多空大掃描"):
        pool_list = [s.strip() for s in stock_input.split(",") if s.strip()]
        
        list_bull = []       
        list_shake = []      
        list_bear = []       
        list_rebound = []    
        list_unknown = []    
        
        with st.spinner("🚀 全台股大數據比對中..."):
            # 建立雙重測試後綴，確保不論上市上櫃都能一網打盡
            target_ids = []
            for sid in pool_list:
                if not sid.endswith(".TW") and not sid.endswith(".TWO"):
                    target_ids.extend([f"{sid}.TW", f"{sid}.TWO"])
                else:
                    target_ids.append(sid)
            
            try:
                # 批次一鍵下載
                all_data = yf.download(tickers=target_ids, period="1mo", session=session, progress=False)
                
                for sid in pool_list:
                    try:
                        t_df = pd.DataFrame()
                        # 先測試是不是上市 (.TW)
                        t_id = f"{sid}.TW" if not sid.endswith(".TW") and not sid.endswith(".TWO") else sid
                        
                        if isinstance(all_data.columns, pd.MultiIndex):
                            if ('Close', t_id) in all_data.columns and not all_data[('Close', t_id)].dropna().empty:
                                t_df = pd.DataFrame({'Close': all_data[('Close', t_id)]})
                            else:
                                # 如果上市沒資料，嘗試切換上櫃 (.TWO)
                                t_id = f"{sid}.TWO"
                                if ('Close', t_id) in all_data.columns:
                                    t_df = pd.DataFrame({'Close': all_data[('Close', t_id)]})
                        else:
                            if 'Close' in all_data.columns:
                                t_df = pd.DataFrame({'Close': all_data['Close']})
                        
                        t_df = t_df.dropna()
                        
                        if not t_df.empty and len(t_df) >= 5:
                            t_df['MA5'] = t_df['Close'].rolling(window=5).mean()
                            if len(t_df) >= 20:
                                t_df['MA20'] = t_df['Close'].rolling(window=20).mean()
                            else:
                                t_df['MA20'] = t_df['Close'].expanding().mean()
                            
                            t_latest = t_df.iloc[-1]
                            c_price = float(t_latest['Close'])
                            m5 = float(t_latest['MA5'])
                            m20 = float(t_latest['MA20'])
                            
                            # 🔥 升級：直接從全台股雲端字典獲取最精準的中文名稱！
                            c_name =
