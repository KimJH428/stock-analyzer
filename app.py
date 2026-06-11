# ============================================================
#  주식 분석기 v2 — 웹사이트 버전 (Streamlit)
#  코랩에서 쓰던 분석기를 그대로 웹 화면으로 옮긴 것.
#  엔진(데이터, 이동평균, 크로스 감지, 백테스트)은 v1과 동일하고
#  st.으로 시작하는 줄들이 "화면에 보여주는" 부분이야.
# ============================================================

import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

# ---------- 페이지 기본 설정 ----------
st.set_page_config(page_title="주식 분석기", page_icon="📈", layout="wide")

st.title("📈 나만의 주식 분석기")
st.caption("이동평균 골든/데드크로스 신호 + 백테스트 | made by 제현 (with Claude)")

# ---------- 입력 (사이드바) ----------
# 코랩에서 ticker = "..." 으로 바꾸던 걸 입력창으로 바꾼 것
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

# ---------- 분석 시작 ----------
if not run:
    st.write("👈 왼쪽에서 종목 코드를 넣고 **분석 시작**을 눌러줘.")
    st.stop()

if short_win >= long_win:
    st.error("단기 이동평균이 장기보다 짧아야 해. (예: 20 / 60)")
    st.stop()

# ---------- 1. 데이터 가져오기 ----------
with st.spinner(f"{ticker} 데이터 가져오는 중..."):
    data = yf.download(ticker, period=period, progress=False)

if data.empty:
    st.error(f"'{ticker}' 데이터를 못 가져왔어. 종목 코드를 확인해줘.")
    st.stop()

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
first_price = float(close.dropna().iloc[0])
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

# (b) 차트
fig, ax = plt.subplots(figsize=(13, 5))
ax.plot(close, label="Close", linewidth=1.3)
ax.plot(ma_s, label=f"MA{short_win}", linewidth=1)
ax.plot(ma_l, label=f"MA{long_win}", linewidth=1)
ax.scatter(golden_days, close[golden_days], color="red", s=70, zorder=5, label="Golden Cross")
ax.scatter(dead_days, close[dead_days], color="blue", s=70, zorder=5, label="Dead Cross")
ax.set_title(f"{ticker}  ({period})")
ax.grid(True, alpha=0.3)
ax.legend()
st.pyplot(fig)

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
- **빨간 점(골든크로스)**: 단기({short_win}일) 평균이 장기({long_win}일) 평균을 **위로** 뚫은 날. 흔히 상승 신호로 불림.
- **파란 점(데드크로스)**: 반대로 **아래로** 뚫은 날.
- **전략 수익률 vs 기간 수익률**: 크로스 신호대로 사고팔았을 때와 그냥 처음부터 들고 있었을 때의 비교.
  전략이 항상 이기는 게 아니라는 걸 직접 확인하는 게 이 도구의 진짜 목적이야.
- 수수료·세금·슬리피지는 계산에 안 들어가 있어서 실제 수익률은 이것보다 낮아져.
"""
)
