# ============================================================
#  주식 분석기 v4 — 트레이딩뷰 스타일 (Streamlit + Plotly)
#  v3에서 바뀐 점:
#   - 차트가 matplotlib(정지 그림) → Plotly(인터랙티브 캔들차트)
#     마우스 올리면 값 표시, 드래그로 확대, 더블클릭으로 원위치
#   - 트레이딩뷰풍 다크 테마 색 (배경 #131722, 상승 초록/하락 빨강)
#   - 거래량 바 차트 추가
#  데이터 3단 예비 체계(야후 → 네이버/KRX → Stooq)는 v3 그대로.
# ============================================================

import streamlit as st
import yfinance as yf
import pandas as pd
import warnings
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

warnings.filterwarnings("ignore")

# ---------- 트레이딩뷰풍 색상표 ----------
BG      = "#131722"   # 차트 배경
PANEL   = "#1E222D"   # 카드/그리드
BORDER  = "#2A2E39"
TEXT    = "#D1D4DC"
UP      = "#26A69A"   # 상승 (초록)
DOWN    = "#EF5350"   # 하락 (빨강)
MA_S_C  = "#F9A825"   # 단기 이동평균 (노랑)
MA_L_C  = "#42A5F5"   # 장기 이동평균 (파랑)

# ---------- 페이지 기본 설정 ----------
st.set_page_config(page_title="주식 분석기", page_icon="📈", layout="wide")

# 숫자 카드 등을 다듬는 약간의 CSS
st.markdown(f"""
<style>
[data-testid="stMetric"] {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 14px 18px;
}}
[data-testid="stMetricLabel"] {{ opacity: 0.75; }}
h1 {{ letter-spacing: -0.5px; }}
</style>
""", unsafe_allow_html=True)

st.title("📈 나만의 주식 분석기")
st.caption("이동평균 골든/데드크로스 신호 + 백테스트 | made by 제현 (with Claude)")

# ---------- 입력 (사이드바) ----------
with st.sidebar:
    st.header("설정")
    ticker = st.text_input("종목 코드", value="005930.KS")
    st.caption(
        "예시) 삼성전자: 005930.KS · SK하이닉스: 000660.KS · "
        "엔비디아: NVDA · 테슬라: TSLA"
    )
    period = st.selectbox("기간", ["6mo", "1y", "2y", "5y"], index=1)
    short_win = st.number_input("단기 이동평균 (일)", value=20, min_value=2, max_value=120)
    long_win = st.number_input("장기 이동평균 (일)", value=60, min_value=5, max_value=240)
    run = st.button("분석 시작", type="primary", use_container_width=True)

st.sidebar.info(
    "이 도구는 **과거** 신호를 보여주는 거지 "
    "미래를 예측하거나 매수/매도를 추천하는 게 아니야."
)

PERIOD_DAYS = {"6mo": 182, "1y": 365, "2y": 730, "5y": 1825}


# ---------- 1. 데이터 가져오기 (3단 예비 체계) ----------
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ohlc(ticker: str, period: str):
    """시가/고가/저가/종가/거래량 데이터와 출처 이름을 돌려준다. 실패하면 (None, None)."""
    t = ticker.upper().strip()
    start = datetime.today() - timedelta(days=PERIOD_DAYS[period])

    # --- 1차 시도: 야후 파이낸스 ---
    try:
        df = yf.download(t, period=period, progress=False)
        if df is not None and not df.empty:
            # 최신 yfinance는 컬럼이 2층 구조로 올 때가 있어서 1층으로 펴줌
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df.dropna(subset=["Close"]), "야후 파이낸스"
    except Exception:
        pass  # 실패하면 조용히 다음 창고로

    is_korean = t.endswith(".KS") or t.endswith(".KQ") or (t.isdigit() and len(t) == 6)

    if is_korean:
        # --- 2차 시도: FinanceDataReader (네이버/KRX) ---
        try:
            import FinanceDataReader as fdr
            code = t.replace(".KS", "").replace(".KQ", "")
            df = fdr.DataReader(code, start)
            if df is not None and not df.empty:
                return df.dropna(subset=["Close"]), "FinanceDataReader (네이버/KRX)"
        except Exception:
            pass
    else:
        # --- 3차 시도: Stooq (미국 종목) ---
        try:
            url = f"https://stooq.com/q/d/l/?s={t.lower()}.us&i=d"
            df = pd.read_csv(url, parse_dates=["Date"], index_col="Date")
            df = df[df.index >= pd.Timestamp(start)]
            if not df.empty and "Close" in df.columns:
                return df.dropna(subset=["Close"]), "Stooq"
        except Exception:
            pass

    return None, None


# ---------- 분석 시작 ----------
if not run:
    st.write("👈 왼쪽에서 종목 코드를 넣고 **분석 시작**을 눌러줘.")
    st.stop()

if short_win >= long_win:
    st.error("단기 이동평균이 장기보다 짧아야 해. (예: 20 / 60)")
    st.stop()

with st.spinner(f"{ticker} 데이터 가져오는 중..."):
    data, source = fetch_ohlc(ticker, period)

if data is None or len(data) == 0:
    st.error(
        f"'{ticker}' 데이터를 어느 창고에서도 못 가져왔어. "
        "종목 코드를 확인하고, 맞다면 잠시 후 다시 시도해줘."
    )
    st.stop()

st.caption(f"데이터 출처: {source}")
close = data["Close"].squeeze()

# ---------- 2. 이동평균선 계산 ----------
ma_s = close.rolling(short_win).mean()
ma_l = close.rolling(long_win).mean()

# ---------- 3. 골든크로스 / 데드크로스 감지 ----------
above = ma_s > ma_l
prev = above.shift(1)
golden_days = close.index[(above == True) & (prev == False)]
dead_days = close.index[(above == False) & (prev == True)]

# ---------- 4. 백테스트 ----------
# 규칙: 골든크로스에 매수, 데드크로스에 매도.
#       기간 끝까지 보유 중이면 마지막 가격으로 평가.
trades = []
holding = False
buy_price, buy_date = None, None

for day in close.index:
    if (not holding) and (day in golden_days):
        holding = True
        buy_price = float(close[day])
        buy_date = day
    elif holding and (day in dead_days):
        sell_price = float(close[day])
        trades.append((buy_date, day, buy_price, sell_price))
        holding = False

still_holding = holding
if holding:
    trades.append((buy_date, close.index[-1], buy_price, float(close.iloc[-1])))

# ---------- 5. 화면에 보여주기 ----------

# (a) 핵심 숫자 카드
first_price = float(close.iloc[0])
last_price = float(close.iloc[-1])
buy_hold_return = (last_price / first_price - 1) * 100

if trades:
    total = 1.0
    for _, _, b, s in trades:
        total *= s / b
    strategy_return = (total - 1) * 100
else:
    strategy_return = 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("현재가", f"{last_price:,.0f}")
c2.metric("기간 수익률 (그냥 들고 있었으면)", f"{buy_hold_return:+.1f}%")
c3.metric("전략 수익률 (크로스 매매했으면)", f"{strategy_return:+.1f}%")
c4.metric("거래 횟수", f"{len(trades)}회")

# (b) 트레이딩뷰풍 캔들차트 + 거래량
has_ohlc = all(col in data.columns for col in ["Open", "High", "Low"])
has_volume = "Volume" in data.columns

fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    row_heights=[0.78, 0.22], vertical_spacing=0.03,
)

if has_ohlc:
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data["Open"], high=data["High"],
        low=data["Low"], close=data["Close"],
        increasing_line_color=UP, increasing_fillcolor=UP,
        decreasing_line_color=DOWN, decreasing_fillcolor=DOWN,
        name="가격",
    ), row=1, col=1)
else:
    fig.add_trace(go.Scatter(
        x=close.index, y=close, name="종가",
        line=dict(color=TEXT, width=1.4),
    ), row=1, col=1)

fig.add_trace(go.Scatter(
    x=ma_s.index, y=ma_s, name=f"MA{short_win}",
    line=dict(color=MA_S_C, width=1.2),
), row=1, col=1)
fig.add_trace(go.Scatter(
    x=ma_l.index, y=ma_l, name=f"MA{long_win}",
    line=dict(color=MA_L_C, width=1.2),
), row=1, col=1)

# 골든/데드크로스 마커 (캔들 위아래에 삼각형)
low_ref = data["Low"] if has_ohlc else close
high_ref = data["High"] if has_ohlc else close
if len(golden_days) > 0:
    fig.add_trace(go.Scatter(
        x=golden_days, y=low_ref[golden_days] * 0.985,
        mode="markers", name="골든크로스",
        marker=dict(symbol="triangle-up", size=13, color=UP,
                    line=dict(width=1, color=BG)),
    ), row=1, col=1)
if len(dead_days) > 0:
    fig.add_trace(go.Scatter(
        x=dead_days, y=high_ref[dead_days] * 1.015,
        mode="markers", name="데드크로스",
        marker=dict(symbol="triangle-down", size=13, color=DOWN,
                    line=dict(width=1, color=BG)),
    ), row=1, col=1)

# 거래량 바 (상승일 초록 / 하락일 빨강)
if has_volume:
    vol_colors = [
        UP if c >= o else DOWN
        for c, o in zip(data["Close"], data["Open"] if has_ohlc else data["Close"])
    ]
    fig.add_trace(go.Bar(
        x=data.index, y=data["Volume"], name="거래량",
        marker_color=vol_colors, opacity=0.55,
    ), row=2, col=1)

fig.update_layout(
    height=620,
    paper_bgcolor=BG, plot_bgcolor=BG,
    font=dict(color=TEXT, size=12),
    hovermode="x unified",
    xaxis_rangeslider_visible=False,
    legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0),
    margin=dict(l=10, r=10, t=30, b=10),
    title=dict(text=f"{ticker}  ·  {period}", x=0.5, font=dict(size=15)),
)
fig.update_xaxes(gridcolor=PANEL, zeroline=False,
                 rangebreaks=[dict(bounds=["sat", "mon"])])  # 주말 빈칸 제거
fig.update_yaxes(gridcolor=PANEL, zeroline=False)

st.plotly_chart(fig, use_container_width=True)

# (c) 매매 내역 표
st.subheader("백테스트 매매 내역")
if trades:
    rows = []
    for i, (bd, sd, b, s) in enumerate(trades, 1):
        note = "보유 중 (마지막 가격으로 평가)" if (still_holding and i == len(trades)) else ""
        rows.append({
            "번호": i,
            "매수일": bd.strftime("%Y-%m-%d"),
            "매도일": sd.strftime("%Y-%m-%d"),
            "매수가": round(b, 2),
            "매도가": round(s, 2),
            "수익률(%)": round((s / b - 1) * 100, 2),
            "비고": note,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.write("이 기간엔 골든크로스 매수 신호가 없었어.")

# (d) 해석 도우미
st.subheader("읽는 법")
st.markdown(
    f"""
- **▲ 초록 삼각형(골든크로스)**: 단기({short_win}일) 평균이 장기({long_win}일) 평균을 **위로** 뚫은 날. 흔히 상승 신호로 불림.
- **▼ 빨간 삼각형(데드크로스)**: 반대로 **아래로** 뚫은 날.
- **전략 수익률 vs 기간 수익률**: 크로스 신호대로 사고팔았을 때와 그냥 처음부터 들고 있었을 때의 비교.
  전략이 항상 이기는 게 아니라는 걸 직접 확인하는 게 이 도구의 진짜 목적이야.
- 수수료·세금·슬리피지는 계산에 안 들어가 있어서 실제 수익률은 이것보다 낮아져.
- 차트는 드래그로 확대, 더블클릭으로 원위치. 마우스를 올리면 그날 값이 떠.
"""
)
