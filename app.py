import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# =====================================================================
# 🌐 1. 雲端同步全台股「上市+上櫃」字典 (內建 24 小時快取)
# =====================================================================
@st.cache_data(ttl=86400)
def load_all_taiwan_stocks():
    stock_dict = {}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    # 抓取上市清單
    try:
        res = requests.get("https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", headers=headers, timeout=5)
        res.encoding = 'big5'
        dfs = pd.read_html(res.text)
        if dfs:
            for val in dfs[0][0]:
                if pd.isna(val): continue
                parts = str(val).split()
                if len(parts) >= 2 and parts[0].isdigit() and len(parts[0]) in [4, 6]:
                    stock_dict[parts[0]] = parts[1]
    except Exception:
        pass
        
    # 抓取上櫃清單
    try:
        res = requests.get("https://isin.twse.com.tw/isin/C_public.jsp?strMode=4", headers=headers, timeout=5)
        res.encoding = 'big5'
        dfs = pd.read_html(res.text)
        if dfs:
            for val in dfs[0][0]:
                if pd.isna(val): continue
                parts = str(val).split()
                if len(parts) >= 2 and parts[0].isdigit() and len(parts[0]) in [4, 6]:
                    stock_dict[parts[0]] = parts[1]
    except Exception:
        pass
        
    # 保底內建核心熱門股（防止證交所網站突發性斷線維護）
    backup = {
        "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2308": "台達電",
        "2881": "富邦金", "2882": "國泰金", "0050": "元大台灣50", "0056": "元大高股息",
        "2603": "長榮", "2382": "廣達"
    }
    for k, v in backup.items():
        if k not in stock_dict:
            stock_dict[k] = v
            
    return stock_dict

all_stocks = load_all_taiwan_stocks()


# =====================================================================
# 🔮 2. 多空技術面診斷核心邏輯
# =====================================================================
def diagnose_trend(current_price, ma5, ma20):
    try:
        c_p, m5, m20 = float(current_price), float(ma5), float(ma20)
    except Exception:
        return "盤整格局", "🔄 資料計算異常，短線方向不明確。"

    if pd.isna(c_p) or pd.isna(m5) or pd.isna(m20):
        return "盤整格局", "🔄 資料不足，無法判斷。"
        
    if c_p >= m5 and m5 >= m20:
        return "多頭排列", f"📈 **【強勢多頭排列】** 目前股價（{c_p:.2f}）踩在 5MA 與 20MA 之上，且均線黃金交叉向上，屬於強勢進攻格局！"
    elif c_p < m5 and m5 >= m20:
        return "多頭震盪", f"⚠️ **【多頭高檔震盪】** 雖然中期還是多頭（5MA > 20MA），但短期股價已跌破 5MA，需注意高檔洗盤或獲利回吐壓力。"
    elif c_p <= m5 and m5 < m20:
        return "空頭排列", f"📉 **【弱勢空頭排列】** 目前均線呈現死亡交叉，股價壓在 20MA 下方，短期內操作建議保守、注意風險！"
    elif c_p > m5 and m5 < m20:
        return "空頭反彈", f"🔄 **【空頭低檔反彈】** 目前整體雖然還是空頭格局（5MA < 20MA），但股價已經站上 5MA 展開反彈，可觀察能否進一步站穩月線築底。"
    return "盤整格局", "🔄 **【盤整格局】** 均線糾結，短線方向不明確。"


# =====================================================================
# 🌐 3. 網頁主介面配置
# =====================================================================
st.set_page_config(page_title="台股自製看盤系統", layout="wide")
st.title("📊 台灣股市智能 K 線與多空選股系統")

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

tab1, tab2 = st.tabs(["📈 個股看盤與診斷", "📋 綜合多空分類清單"])


# =====================================================================
# 📈 頁籤一：個股看盤與診斷
# =====================================================================
with tab1:
    st.sidebar.header("⚙️ 個股看盤參數")
    
    # 建立 "代號 - 名稱" 下拉選單格式
    stock_options = [f"{code} - {name}" for code, name in all_stocks.items()]
    
    # 預設選中台積電
    default_idx = next((i for i, opt in enumerate(stock_options) if opt.startswith("2330")), 0)
        
    selected_stock = st.sidebar.selectbox(
        "請輸入股票代號或名稱：",
        options=stock_options,
        index=default_idx,
        key="google_like_search"
    )
    
    # 切割代號
    stock_id = selected_stock.split(" - ")[0]
    
    period = st.sidebar.selectbox("請選擇時間區間：", ["1個月","3個月", "6個月", "1年","5年"], key="single_period")
    period_map = {"1個月": "1mo", "3個月": "3mo", "6個月": "6mo", "1年": "1y", "5年": "5y"}

    target_id = f"{stock_id}.TW"
    try:
        df = yf.Ticker(target_id, session=session).history(period=period_map[period])
        
        # 若上市找不到，自動切換至上櫃 (.TWO)
        if df.empty:
            target_id = f"{stock_id}.TWO"
            df = yf.Ticker(target_id, session=session).history(period=period_map[period])

        if df.empty:
            st.error("⚠️ 找不到該股票歷史交易資料。")
        else:
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            
            latest = df.iloc[-1]
            c_p, m5, m20 = float(latest['Close']), float(latest['MA5']), float(latest['MA20'])
            
            st.subheader(f"🔮 {selected_stock} - 智慧多空技術面診斷")
            status, alert_message = diagnose_trend(c_p, m5, m20)
            
            if status == "多頭排列": st.success(alert_message)
            elif status == "多頭震盪": st.warning(alert_message)
            elif status == "空頭排列": st.error(alert_message)
            else: st.info(alert_message)

            # 畫 K 線
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
# 📋 頁籤二：綜合多空分類清單
# =====================================================================
with tab2:
    st.subheader("📋 追蹤個股多空狀態大盤點")
    st.write("系統會自動抓取下方清單中所有股票的最新收盤價與均線，並自動分門別類。")

    default_stocks = "2330, 2317, 2454, 2308, 2881, 2882, 0050, 0056, 2603, 2382"
    stock_input = st.text_area("✍️ 編輯你要偵測的股票代號清單（請用逗號隔開）：", default_stocks)
    
    if st.button("🚀 開始全面多空大掃描"):
        pool_list = [s.strip() for s in stock_input.split(",") if s.strip()]
        list_bull, list_shake, list_bear, list_rebound, list_unknown = [], [], [], [], []
        
        with st.spinner("🚀 全台股大數據比對中..."):
            target_ids = []
            for sid in pool_list:
                target_ids.extend([f"{sid}.TW", f"{sid}.TWO"])
            
            try:
                all_data = yf.download(tickers=target_ids, period="1mo", session=session, progress=False)
                
                for sid in pool_list:
                    try:
                        t_df = pd.DataFrame()
                        t_id = f"{sid}.TW"
                        
                        if isinstance(all_data.columns, pd.MultiIndex):
                            if ('Close', t_id) in all_data.columns and not all_data[('Close', t_id)].dropna().empty:
                                t_df = pd.DataFrame({'Close': all_data[('Close', t_id)]})
                            else:
                                t_id = f"{sid}.TWO"
                                if ('Close', t_id) in all_data.columns:
                                    t_df = pd.DataFrame({'Close': all_data[('Close', t_id)]})
                        else:
                            if 'Close' in all_data.columns:
                                t_df = pd.DataFrame({'Close': all_data['Close']})
                        
                        t_df = t_df.dropna()
                        if not t_df.empty and len(t_df) >= 5:
                            t_df['MA5'] = t_df['Close'].rolling(window=5).mean()
                            t_df['MA20'] = t_df['Close'].rolling(window=20).mean() if len(t_df) >= 20 else t_df['Close'].expanding().mean()
                            
                            t_latest = t_df.iloc[-1]
                            c_price, m5, m20 = float(t_latest['Close']), float(t_latest['MA5']), float(t_latest['MA20'])
                            
                            c_name = all_stocks.get(sid, "(自訂個股)")
                            display_text = f"🔹 **{sid} {c_name}** (收盤: {c_price:.2f})"
                            
                            status, _ = diagnose_trend(c_price, m5, m20)
                            if status == "多頭排列": list_bull.append(display_text)
                            elif status == "多頭震盪": list_shake.append(display_text)
                            elif status == "空頭排列": list_bear.append(display_text)
                            elif status == "空頭反彈": list_rebound.append(display_text)
                            else: list_unknown.append(display_text)
                        else:
                            list_unknown.append(f"❌ {sid} (無足夠交易資料)")
                    except Exception:
                        list_unknown.append(f"❌ {sid} (解析錯誤)")
            except Exception as e:
                st.error(f"連線至大數據庫失敗：{e}")
        
        st.success("✨ 全面掃描完成！以下是最新分類清單：")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("### 🟢 強勢多頭排列")
            for item in list_bull: st.write(item)
            if not list_bull: st.write("（目前無股票符合）")
        with col2:
            st.markdown("### 🟡 多頭高檔震盪")
            for item in list_shake: st.write(item)
            if not list_shake: st.write("（目前無股票符合）")
        with col3:
            st.markdown("### 🔵 空頭低檔反彈")
            for item in list_rebound: st.write(item)
            if not list_rebound: st.write("（目前無股票符合）")
        with col4:
            st.markdown("### 🔴 弱勢空頭排列")
            for item in list_bear: st.write(item)
            if not list_bear: st.write("（目前無股票符合）")

        if list_unknown:
            with st.expander("ℹ️ 未能成功分類或盤整個股"):
                for item in list_unknown: st.write(item)
