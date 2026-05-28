import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests  # 新增：用來幫我們做瀏覽器偽裝

# 網頁標題與設定
st.set_page_config(page_title="台股自製看盤系統", layout="wide")
st.title("📊 台灣股市互動 K 線與智能多空診斷系統")
st.write("輸入股票代號，自動產生含均線、成交量的專業 K 線圖，並提供智慧多空技術面診斷。")

# 側邊欄：使用者輸入區
st.sidebar.header("⚙️ 設定參數")
stock_id = st.sidebar.text_input("請輸入台股代號：", "2330")
period = st.sidebar.selectbox("請選擇時間區間：", ["1個月","3個月", "6個月", "1年","5年"])

# 轉換時間格式給 yfinance
period_map = {"1個月": "1mo", "3個月": "3mo", "6個月": "6mo", "1年": "1y", "5年": "5y"}

# 自動處理台灣股票代號後綴
if not stock_id.endswith(".TW") and not stock_id.endswith(".TWO"):
    target_id = f"{stock_id}.TW"
else:
    target_id = stock_id

try:
    # 🔥 核心修正：建立一個帶有安全瀏覽器標頭 (User-Agent) 的連線會話
    # 這樣 Yahoo Finance 就會以為是真人在看網頁，不會隨便阻擋你
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    })
    
    # 將偽裝好的連線會話餵給 yfinance
    ticker = yf.Ticker(target_id, session=session)
    df = ticker.history(period=period_map[period])
    
    if df.empty:
        st.error("⚠️ 找不到該股票資料，請確認代號是否正確（例如台積電輸入 2330）。")
    else:
        # 計算技術指標：5MA、20MA
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()

        # ------------------ 🔮 智能多空診斷邏輯 ------------------
        # 取得最新一天的數據來做多空診斷
        latest = df.iloc[-1]
        current_price = latest['Close']
        ma5_val = latest['MA5']
        ma20_val = latest['MA20']
        
        st.subheader("🔮 智慧多空技術面診斷")
        
        # 判斷邏輯（根據 5MA 與 20MA 的相對位置）
        if current_price >= ma5_val and ma5_val >= ma20_val:
            st.success(f"📈 **【強勢多頭排列】** 目前股價（{current_price:.2f}）踩在 5MA 與 20MA 之上，且均線黃金交叉向上，屬於強勢進攻格局！")
        elif current_price < ma5_val and ma5_val >= ma20_val:
            st.warning(f"⚠️ **【多頭高檔震盪】** 雖然中期還是多頭（5MA > 20MA），但短期股價已跌破 5MA，需注意高檔洗盤或獲利回吐壓力。")
        elif current_price <= ma5_val and ma5_val < ma20_val:
            st.error(f"📉 **【弱勢空頭排列】** 目前均線呈現死亡交叉，股價壓在 20MA（月線）下方，短期內操作建議保守、注意風險！")
        elif current_price > ma5_val and ma5_val < ma20_val:
            st.info(f"🔄 **【空頭低檔反彈】** 目前整體雖然還是空頭格局（5MA < 20MA），但股價已經站上 5MA 展開反彈，可觀察能否進一步站穩月線築底。")
        # ------------------------------------------------------

        # 建立雙子圖 (上面畫K線，下面畫成交量)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.08, row_heights=[0.7, 0.3])

        # 1. 主圖：繪製 K 線 (符合台股習慣：紅漲綠跌)
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="K線",
            increasing_line_color='#FF3333',  # 上漲紅
            increasing_fillcolor='#FF3333',
            decreasing_line_color='#00AA00',  # 下跌綠
            decreasing_fillcolor='#00AA00'
        ), row=1, col=1)

        # 2. 主圖：疊加 5MA 與 20MA 均線
        fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5MA (週線)', line=dict(color='orange', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20MA (月線)', line=dict(color='deepskyblue', width=1.5)), row=1, col=1)

        # 3. 副圖：繪製成交量
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='dimgray'), row=2, col=1)

        # 調整圖表整體外觀（使用高質感暗色系主題）
        fig.update_layout(
            title=f"📈 {stock_id} - 歷史技術線圖",
            xaxis_rangeslider_visible=False,  # 隱藏下方預設的滑塊以保持乾淨
            height=650,
            template="plotly_dark",
            hovermode="x unified"
        )
        
        # 秀出圖表
        st.plotly_chart(fig, use_container_width=True)
        
        # 下方數據表格
        st.subheader("📋 近期歷史詳細數據 (最前線)")
        st.dataframe(df.tail(10).style.format("{:.2f}"))

except Exception as e:
    st.error(f"讀取資料時發生錯誤：{e}")
