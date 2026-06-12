# ============================================================
#  주식 분석기 v7 — RSI + 시장 스캐너 에디션
#  v6에서 바뀐 점:
#   - RSI(14) 지표 추가: 차트에 RSI 패널이 생기고,
#     과매수(70↑)/과매도(30↓) 진입 지점을 가격 차트에 마커로 표시
#   - 🚨 시장 스캐너 페이지: 시가총액 상위 N개 국내 종목을 훑어서
#     급등+과매수 / 최근 골든크로스 / 거래량 폭증 / 과매도 신호를 표로 정리
#   - 분석기/스캐너 화면에 은은한 네온 글로우 배경
#  홈 홀로그램, 한국식 캔들, 금별/보라 마커, 데이터 예비 체계는 그대로.
# ============================================================

import streamlit as st
import yfinance as yf
import pandas as pd
import warnings
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

warnings.filterwarnings("ignore")

# ---------- 색상표 ----------
BG      = "#131722"
PANEL   = "#1E222D"
BORDER  = "#2A2E39"
TEXT    = "#D1D4DC"
SUBTLE  = "#787B86"
UP      = "#F23645"   # 상승 (한국식 빨강)
DOWN    = "#3179F5"   # 하락 (한국식 파랑)
GOLD    = "#FFC107"   # 골든크로스
PURPLE  = "#A855F7"   # 데드크로스
MA_S_C  = "#26A69A"   # 단기 이동평균
MA_L_C  = "#E0E3EB"   # 장기 이동평균
OB_C    = "#FF6D00"   # 과매수 (주황)
OS_C    = "#00E5FF"   # 과매도 (하늘)
RSI_C   = "#FFA726"   # RSI 선

st.set_page_config(page_title="주식 분석기", page_icon="📈", layout="wide")

# ---------- 전체 스타일 + 애니메이션 ----------
st.markdown(f"""
<style>
@keyframes fadeUp {{
    from {{ opacity: 0; transform: translateY(16px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes gradientMove {{
    0%   {{ background-position: 0% 50%; }}
    50%  {{ background-position: 100% 50%; }}
    100% {{ background-position: 0% 50%; }}
}}
.hero-title {{
    font-size: 56px; font-weight: 800; letter-spacing: -1.5px;
    background: linear-gradient(90deg, {GOLD}, {UP}, {DOWN}, {GOLD});
    background-size: 300% 100%;
    -webkit-background-clip: text; background-clip: text;
    color: transparent;
    animation: gradientMove 7s ease infinite, fadeUp 0.7s ease;
    margin-bottom: 0;
}}
.hero-sub {{
    color: {SUBTLE}; font-size: 17px; margin-top: 6px;
    animation: fadeUp 0.7s ease 0.15s backwards;
}}
.chip-row {{ display: flex; gap: 10px; flex-wrap: wrap; margin: 22px 0 6px 0;
             animation: fadeUp 0.7s ease 0.3s backwards; }}
.chip {{
    background: {PANEL}; border: 1px solid {BORDER}; color: {TEXT};
    padding: 8px 14px; border-radius: 999px; font-size: 13.5px;
}}
.stat-row {{ display: flex; gap: 14px; flex-wrap: wrap; }}
.stat-card {{
    flex: 1; min-width: 180px;
    background: linear-gradient(160deg, {PANEL} 0%, #181C27 100%);
    border: 1px solid {BORDER}; border-radius: 14px;
    padding: 16px 20px;
    animation: fadeUp 0.55s ease backwards;
    transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
}}
.stat-card:hover {{
    transform: translateY(-3px);
    border-color: {GOLD};
    box-shadow: 0 8px 24px rgba(255, 193, 7, 0.10);
}}
.stat-card:nth-child(1) {{ animation-delay: .05s; }}
.stat-card:nth-child(2) {{ animation-delay: .12s; }}
.stat-card:nth-child(3) {{ animation-delay: .19s; }}
.stat-card:nth-child(4) {{ animation-delay: .26s; }}
.stat-label {{ color: {SUBTLE}; font-size: 13px; margin-bottom: 6px; }}
.stat-value {{ font-size: 26px; font-weight: 700; color: {TEXT}; }}
.stat-up   {{ color: {UP}; }}
.stat-down {{ color: {DOWN}; }}
.stButton > button {{
    transition: transform .15s ease, box-shadow .15s ease;
    border-radius: 10px;
}}
.stButton > button:hover {{
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(0,0,0,0.35);
}}
[data-testid="stPlotlyChart"], .stTabs {{ animation: fadeUp 0.6s ease; }}
h1 {{ letter-spacing: -0.5px; }}
</style>
""", unsafe_allow_html=True)

# 분석기/스캐너 화면용: 모서리에서 천천히 숨쉬는 네온 글로우 (아주 은은하게)
AMBIENT_BG = f"""
<style>
.block-container {{ position: relative; z-index: 1; }}
@keyframes breathe {{
    0%,100% {{ opacity: .35; }}
    50%     {{ opacity: .75; }}
}}
.ambient-bg {{ position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }}
.glow {{
    position: absolute; width: 55vw; height: 55vw; border-radius: 50%;
    filter: blur(140px); animation: breathe 9s ease-in-out infinite;
}}
.glow-1 {{ top: -28vw; right: -22vw; background: rgba(77,217,232,0.10); }}
.glow-2 {{ bottom: -30vw; left: -24vw; background: rgba(255,193,7,0.07); animation-delay: 4.5s; }}
</style>
<div class="ambient-bg"><div class="glow glow-1"></div><div class="glow glow-2"></div></div>
"""

PERIOD_DAYS = {"6mo": 182, "1y": 365, "2y": 730, "5y": 1825}
PERIOD_LABEL = {"6mo": "6개월", "1y": "1년", "2y": "2년", "5y": "5년"}


# ---------- 지표 계산 ----------
def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """RSI: 최근 N일간 오른 힘과 내린 힘의 비율을 0~100으로.
    70 이상이면 과매수(단기 과열), 30 이하면 과매도로 보는 게 일반적."""
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss
    return 100 - 100 / (1 + rs)


# ---------- 데이터 가져오기 (3단 예비 체계) ----------
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ohlc(ticker: str, period: str):
    """시가/고가/저가/종가/거래량 데이터와 출처 이름을 돌려준다. 실패하면 (None, None)."""
    t = ticker.upper().strip()
    start = datetime.today() - timedelta(days=PERIOD_DAYS[period])

    # --- 1차 시도: 야후 파이낸스 ---
    try:
        df = yf.download(t, period=period, progress=False)
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df.dropna(subset=["Close"]), "야후 파이낸스"
    except Exception:
        pass

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


# ---------- 스캐너용 함수들 ----------
@st.cache_data(ttl=3600, show_spinner=False)
def load_krx_top(n: int):
    """국내(코스피+코스닥) 종목을 시가총액 순으로 정렬해 상위 n개 목록을 돌려준다."""
    import FinanceDataReader as fdr
    df = fdr.StockListing("KRX")
    df = df[df["Market"].isin(["KOSPI", "KOSDAQ"])]
    df = df[~df["Name"].str.contains("스팩", na=False)]  # 스팩 제외
    df = df.sort_values("Marcap", ascending=False).head(n)
    return df[["Code", "Name", "Market"]].reset_index(drop=True)


@st.cache_data(ttl=3600, show_spinner=False)
def load_sp500(n: int):
    """미국 S&P 500 명단에서 앞쪽 n개를 돌려준다. (전부 대형주라 순서는 큰 의미 없음)"""
    import FinanceDataReader as fdr
    df = fdr.StockListing("S&P500")
    df = df.head(n).copy()
    df["Market"] = "S&P500"
    df = df.rename(columns={"Symbol": "Code"})
    return df[["Code", "Name", "Market"]].reset_index(drop=True)


def compute_signals(c: pd.Series, v):
    """종가(c)와 거래량(v)으로 신호를 계산한다. 국내/미국 공용."""
    r_now = float(rsi(c).iloc[-1])
    ret5 = float((c.iloc[-1] / c.iloc[-6] - 1) * 100) if len(c) > 6 else 0.0

    vol_ratio = 0.0
    if v is not None and len(v) > 21:
        base = v.iloc[-21:-1].mean()
        if base > 0:
            vol_ratio = float(v.iloc[-1] / base)

    ma20 = c.rolling(20).mean()
    ma60 = c.rolling(60).mean()
    ab = ma20 > ma60
    pr = ab.shift(1)
    recent_golden = bool(((ab == True) & (pr == False)).iloc[-5:].any())

    signals = []
    if ret5 >= 10 and r_now >= 70:
        signals.append("🔥 급등+과매수")
    if recent_golden:
        signals.append("⭐ 골든크로스(5일 내)")
    if vol_ratio >= 3:
        signals.append("📊 거래량 급증")
    if r_now <= 30:
        signals.append("🧊 과매도")

    if not signals:
        return None  # 신호 없는 종목은 표에서 제외

    return {
        "현재가": float(c.iloc[-1]),
        "5일 수익률(%)": round(ret5, 1),
        "RSI": round(r_now, 1),
        "거래량배수": round(vol_ratio, 1),
        "신호": " · ".join(signals),
    }


@st.cache_data(ttl=1800, show_spinner=False)
def analyze_one(code: str, today_key: str):
    """국내 종목 하나의 신호 계산 (네이버/KRX 데이터). today_key는 캐시 갱신용."""
    import FinanceDataReader as fdr
    start = datetime.today() - timedelta(days=130)
    try:
        df = fdr.DataReader(code, start)
    except Exception:
        return None
    if df is None or len(df) < 40:
        return None
    c = df["Close"].astype(float)
    v = df["Volume"].astype(float) if "Volume" in df.columns else None
    return compute_signals(c, v)


@st.cache_data(ttl=1800, show_spinner=False)
def analyze_one_us(symbol: str, today_key: str):
    """미국 종목 하나의 신호 계산. 야후 먼저, 막히면 Stooq로 갈아탄다."""
    df = None
    # 1차: 야후
    try:
        tmp = yf.download(symbol, period="6mo", progress=False)
        if tmp is not None and not tmp.empty:
            if isinstance(tmp.columns, pd.MultiIndex):
                tmp.columns = tmp.columns.get_level_values(0)
            df = tmp
    except Exception:
        pass
    # 2차: Stooq
    if df is None or len(df) < 40:
        try:
            url = f"https://stooq.com/q/d/l/?s={symbol.lower()}.us&i=d"
            tmp = pd.read_csv(url, parse_dates=["Date"], index_col="Date")
            start = datetime.today() - timedelta(days=190)
            tmp = tmp[tmp.index >= pd.Timestamp(start)]
            if not tmp.empty and "Close" in tmp.columns:
                df = tmp
        except Exception:
            pass
    if df is None or len(df) < 40:
        return None
    c = df["Close"].astype(float).dropna()
    v = df["Volume"].astype(float) if "Volume" in df.columns else None
    return compute_signals(c, v)


# ---------- 페이지 이동 관리 ----------
if "page" not in st.session_state:
    st.session_state.page = "home"
if "query" not in st.session_state:
    st.session_state.query = None
if "scan_df" not in st.session_state:
    st.session_state.scan_df = None


def go_page(page_name: str):
    st.session_state.page = page_name


# ============================================================
#  홈 화면
# ============================================================
if st.session_state.page == "home":
    st.markdown(f"""
<style>
.block-container {{ position: relative; z-index: 1; }}
.holo-bg {{ position: fixed; inset: 0; z-index: 0; overflow: hidden; pointer-events: none; }}
.holo-grid {{
    position: absolute; left: -50%; bottom: -24%; width: 200%; height: 72%;
    background-image:
        linear-gradient(rgba(77,217,232,0.16) 1px, transparent 1px),
        linear-gradient(90deg, rgba(77,217,232,0.16) 1px, transparent 1px);
    background-size: 46px 46px;
    transform: perspective(620px) rotateX(62deg);
    animation: gridScroll 8s linear infinite;
    -webkit-mask-image: linear-gradient(to top, rgba(0,0,0,.9), transparent 85%);
    mask-image: linear-gradient(to top, rgba(0,0,0,.9), transparent 85%);
}}
@keyframes gridScroll {{ from {{ background-position-y: 0; }} to {{ background-position-y: 46px; }} }}
.holo-card {{
    position: absolute; opacity: .45;
    filter: drop-shadow(0 0 14px rgba(77,217,232,.55));
    animation: holoFloat 8s ease-in-out infinite;
    transform-style: preserve-3d;
}}
.holo-gold   {{ filter: drop-shadow(0 0 14px rgba(255,193,7,.5)); }}
.holo-purple {{ filter: drop-shadow(0 0 12px rgba(168,85,247,.55)); }}
@keyframes holoFloat {{
    0%,100% {{ transform: perspective(800px) rotateY(-14deg) translateY(0); }}
    50%     {{ transform: perspective(800px) rotateY(-6deg)  translateY(-20px); }}
}}
.holo-line {{
    stroke-dasharray: 700; stroke-dashoffset: 700;
    animation: holoDraw 6s ease-in-out infinite;
}}
@keyframes holoDraw {{
    0%   {{ stroke-dashoffset: 700; opacity: .2; }}
    55%  {{ stroke-dashoffset: 0;   opacity: 1;  }}
    85%  {{ stroke-dashoffset: 0;   opacity: 1;  }}
    100% {{ stroke-dashoffset: 0;   opacity: 0;  }}
}}
.holo-candles rect {{
    transform-origin: center bottom; transform-box: fill-box;
    animation: candlePulse 3.2s ease-in-out infinite;
}}
.holo-candles rect:nth-child(odd)  {{ animation-delay: .6s; }}
.holo-candles rect:nth-child(3n)   {{ animation-delay: 1.3s; }}
@keyframes candlePulse {{
    0%,100% {{ transform: scaleY(1); }}
    50%     {{ transform: scaleY(1.35); }}
}}
</style>
<div class="holo-bg">
  <div class="holo-grid"></div>
  <svg class="holo-card" style="top:10%; right:5%; animation-delay:.2s"
       width="360" height="190" viewBox="0 0 360 190">
    <polyline class="holo-line" fill="none" stroke="#4DD9E8" stroke-width="2.2"
        points="0,160 35,128 60,142 95,95 125,112 160,64 190,86 225,48 260,66 300,30 360,42"/>
    <polyline fill="none" stroke="#4DD9E8" stroke-width="1" opacity="0.25"
        points="0,170 60,150 120,155 180,120 240,128 300,90 360,100"/>
  </svg>
  <svg class="holo-card holo-gold" style="bottom:14%; left:3%; animation-delay:1.4s"
       width="320" height="180" viewBox="0 0 320 180">
    <g class="holo-candles">
      <rect x="20"  y="100" width="12" height="58" fill="#F23645" opacity=".8"/>
      <rect x="55"  y="118" width="12" height="40" fill="#3179F5" opacity=".8"/>
      <rect x="90"  y="86"  width="12" height="72" fill="#F23645" opacity=".8"/>
      <rect x="125" y="104" width="12" height="54" fill="#F23645" opacity=".8"/>
      <rect x="160" y="124" width="12" height="34" fill="#3179F5" opacity=".8"/>
      <rect x="195" y="72"  width="12" height="86" fill="#F23645" opacity=".8"/>
      <rect x="230" y="92"  width="12" height="66" fill="#3179F5" opacity=".8"/>
      <rect x="265" y="56"  width="12" height="102" fill="#F23645" opacity=".8"/>
    </g>
    <polyline class="holo-line" fill="none" stroke="#FFC107" stroke-width="2"
        style="animation-delay:1s"
        points="10,130 50,118 90,100 130,112 170,88 210,96 250,62 300,44"/>
  </svg>
  <svg class="holo-card holo-purple" style="top:16%; left:34%; animation-delay:2.6s; opacity:.3"
       width="220" height="110" viewBox="0 0 220 110">
    <polyline class="holo-line" fill="none" stroke="#A855F7" stroke-width="2"
        style="animation-delay:2s"
        points="0,80 30,60 55,72 85,40 115,52 150,26 185,38 220,18"/>
  </svg>
</div>
""", unsafe_allow_html=True)

    st.markdown('<p class="hero-title">📈 나만의 주식 분석기</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-sub">이동평균 골든/데드크로스 신호와 백테스트를 한 화면에서. '
        'made by 제현 (with Claude)</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="chip-row">'
        '<span class="chip">🕯️ 인터랙티브 캔들차트</span>'
        '<span class="chip">⭐ 골든/데드크로스 감지</span>'
        '<span class="chip">🌡️ RSI 과매수/과매도</span>'
        '<span class="chip">🚨 급등 신호 스캐너</span>'
        '<span class="chip">🧪 전략 백테스트</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.write("")

    c1, c2, c3, _ = st.columns([1, 1, 1, 1])
    with c1:
        st.button("📊 분석기 열기", type="primary", use_container_width=True,
                  on_click=go_page, args=("app",))
    with c2:
        st.button("🚨 시장 스캐너", use_container_width=True,
                  on_click=go_page, args=("scanner",))
    with c3:
        st.button("📖 사용법 보기", use_container_width=True,
                  on_click=go_page, args=("guide",))

    st.write("")
    st.caption("⚠️ 이 도구는 과거 신호를 보여주는 거지 미래를 예측하거나 매수/매도를 추천하는 게 아니야.")

# ============================================================
#  사용법 화면
# ============================================================
elif st.session_state.page == "guide":
    st.button("← 홈으로", on_click=go_page, args=("home",))
    st.title("📖 사용법")
    st.markdown(f"""
1. **분석기**: 종목 코드와 기간을 고르고 **분석 시작**.
   - 한국 주식은 숫자 코드 + `.KS`(코스피)/`.KQ`(코스닥) — 예: 삼성전자 `005930.KS`
   - 미국 주식은 영문 티커 — 예: 엔비디아 `NVDA`, 테슬라 `TSLA`
2. **차트 조작**: 마우스 휠로 확대/축소, 드래그로 좌우 이동, 더블클릭하면 원위치.
3. **신호 읽는 법**
   - ⭐ <span style="color:{GOLD}">금색 별 = 골든크로스</span>: 단기 평균이 장기 평균을 위로 뚫은 날.
   - 🔻 <span style="color:{PURPLE}">보라 삼각형 = 데드크로스</span>: 반대로 아래로 뚫은 날.
   - 💠 <span style="color:{OB_C}">주황 다이아 = 과매수 진입</span>: RSI가 70을 넘은 날. 단기 과열 — 급등 중이라는 뜻이지만, 식으면서 조정이 올 수도 있다는 뜻이기도 해.
   - 💠 <span style="color:{OS_C}">하늘 다이아 = 과매도 진입</span>: RSI가 30 아래로 떨어진 날. 과하게 빠졌다는 신호.
4. **RSI 패널**: 차트 맨 아래 주황 선. 70 위 구간(과매수)과 30 아래 구간(과매도)이 색으로 칠해져 있어.
5. **시장 스캐너**: 시가총액 상위 종목들을 훑어서 🔥 급등+과매수, ⭐ 최근 골든크로스,
   📊 거래량 급증, 🧊 과매도 신호가 잡힌 종목만 추려줘.
6. **백테스트**: "골든크로스에 사서 데드크로스에 팔았다면?"을 과거 데이터로 계산한 것.
   전략이 항상 이기는 게 아니라는 걸 직접 확인하는 게 이 도구의 진짜 목적이야.
7. 모든 신호는 **참고용**이야. 수수료·세금·슬리피지도 계산에 없어.
""", unsafe_allow_html=True)

# ============================================================
#  시장 스캐너 화면
# ============================================================
elif st.session_state.page == "scanner":
    st.markdown(AMBIENT_BG, unsafe_allow_html=True)

    with st.sidebar:
        st.button("← 홈으로", on_click=go_page, args=("home",), use_container_width=True)
        st.header("스캐너 설정")
        market = st.radio("시장", ["🇰🇷 국내 (코스피+코스닥)", "🇺🇸 미국 (S&P 500)"])
        is_us = market.startswith("🇺🇸")
        top_n = st.slider("스캔할 종목 수", 30, 300, 100, step=10)
        st.caption("국내는 시가총액 상위 순. 많이 고를수록 오래 걸려 (100개 기준 1분 정도).")
        scan_btn = st.button("🚨 시장 스캔 시작", type="primary", use_container_width=True)
        if is_us:
            st.warning("미국 스캔은 데이터 통로(야후/Stooq) 사정에 따라 "
                       "일부 종목이 빠지거나 더 오래 걸릴 수 있어.")
        st.info("신호는 **참고용**이지 매수 추천이 아니야 — 특히 과매수는 "
                "'지금 뜨겁다'는 뜻이면서 동시에 '조정이 올 수 있다'는 뜻이기도 해.")

    st.title("🚨 시장 스캐너")
    st.caption("선택한 시장의 주요 종목 중 오늘 기준 신호가 잡힌 종목만 추려서 보여줘.")

    if scan_btn:
        today_key = datetime.today().strftime("%Y-%m-%d-%H")  # 시간 단위로 캐시 갱신
        try:
            listing = load_sp500(top_n) if is_us else load_krx_top(top_n)
        except Exception:
            listing = None

        if listing is None or len(listing) == 0:
            st.error("종목 목록을 못 가져왔어. 잠시 후 다시 시도해줘.")
        else:
            analyze_fn = analyze_one_us if is_us else analyze_one
            results = []
            prog = st.progress(0, text="스캔 준비 중...")
            for i, row in listing.iterrows():
                res = analyze_fn(row["Code"], today_key)
                if res is not None:
                    results.append({
                        "종목명": row["Name"],
                        "코드": row["Code"],
                        "시장": row["Market"],
                        **res,
                    })
                prog.progress((i + 1) / len(listing),
                              text=f"스캔 중... {i + 1}/{len(listing)} · {row['Name']}")
            prog.empty()

            if results:
                df = pd.DataFrame(results).sort_values("5일 수익률(%)", ascending=False)
                st.session_state.scan_df = df.reset_index(drop=True)
            else:
                st.session_state.scan_df = pd.DataFrame()

    if st.session_state.scan_df is None:
        st.write("👈 왼쪽에서 종목 수를 정하고 **시장 스캔 시작**을 눌러줘.")
    elif len(st.session_state.scan_df) == 0:
        st.write("이번 스캔에선 신호가 잡힌 종목이 없었어.")
    else:
        df = st.session_state.scan_df
        st.markdown(f"""
<div class="stat-row">
  <div class="stat-card">
    <div class="stat-label">신호 잡힌 종목</div>
    <div class="stat-value">{len(df)}개</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">🔥 급등+과매수</div>
    <div class="stat-value">{int(df["신호"].str.contains("급등").sum())}개</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">⭐ 최근 골든크로스</div>
    <div class="stat-value">{int(df["신호"].str.contains("골든").sum())}개</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">🧊 과매도</div>
    <div class="stat-value">{int(df["신호"].str.contains("과매도").sum())}개</div>
  </div>
</div>
""", unsafe_allow_html=True)
        st.write("")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption("표 제목을 누르면 정렬돼. 궁금한 종목은 코드를 복사해서 분석기에서 검색해봐 "
                   "(국내는 코드 뒤에 .KS 코스피 / .KQ 코스닥, 미국은 코드 그대로).")

# ============================================================
#  분석기 화면
# ============================================================
else:
    st.markdown(AMBIENT_BG, unsafe_allow_html=True)

    with st.sidebar:
        st.button("← 홈으로", on_click=go_page, args=("home",), use_container_width=True)
        st.header("설정")
        ticker = st.text_input("종목 코드", value="005930.KS")
        st.caption(
            "예시) 삼성전자: 005930.KS · SK하이닉스: 000660.KS · "
            "엔비디아: NVDA · 테슬라: TSLA"
        )
        period = st.selectbox("기간", ["6mo", "1y", "2y", "5y"], index=1,
                              format_func=lambda p: PERIOD_LABEL[p])
        short_win = st.number_input("단기 이동평균 (일)", value=20, min_value=2, max_value=120)
        long_win = st.number_input("장기 이동평균 (일)", value=60, min_value=5, max_value=240)
        run = st.button("분석 시작", type="primary", use_container_width=True)
        st.info("이 도구는 **과거** 신호를 보여주는 거지 "
                "미래를 예측하거나 매수/매도를 추천하는 게 아니야.")

    st.title("📊 분석기")

    if run:
        if short_win >= long_win:
            st.error("단기 이동평균이 장기보다 짧아야 해. (예: 20 / 60)")
            st.stop()
        st.session_state.query = {
            "ticker": ticker, "period": period,
            "short": int(short_win), "long": int(long_win),
        }

    q = st.session_state.query
    if q is None:
        st.write("👈 왼쪽에서 종목 코드를 넣고 **분석 시작**을 눌러줘.")
        st.stop()

    with st.spinner(f"{q['ticker']} 데이터 가져오는 중..."):
        data, source = fetch_ohlc(q["ticker"], q["period"])

    if data is None or len(data) == 0:
        st.error(
            f"'{q['ticker']}' 데이터를 어느 창고에서도 못 가져왔어. "
            "종목 코드를 확인하고, 맞다면 잠시 후 다시 시도해줘."
        )
        st.stop()

    close = data["Close"].squeeze()
    s_win, l_win = q["short"], q["long"]

    # ---------- 이동평균 / 크로스 감지 ----------
    ma_s = close.rolling(s_win).mean()
    ma_l = close.rolling(l_win).mean()
    above = ma_s > ma_l
    prev = above.shift(1)
    golden_days = close.index[(above == True) & (prev == False)]
    dead_days = close.index[(above == False) & (prev == True)]

    # ---------- RSI / 과매수·과매도 진입 지점 ----------
    rsi_line = rsi(close)
    ob_enter = (rsi_line >= 70) & (rsi_line.shift(1) < 70)   # 과매수 구간에 들어간 날
    os_enter = (rsi_line <= 30) & (rsi_line.shift(1) > 30)   # 과매도 구간에 들어간 날
    ob_days = close.index[ob_enter.fillna(False)]
    os_days = close.index[os_enter.fillna(False)]

    # ---------- 백테스트 ----------
    trades = []
    holding = False
    buy_price, buy_date = None, None
    for day in close.index:
        if (not holding) and (day in golden_days):
            holding = True
            buy_price = float(close[day])
            buy_date = day
        elif holding and (day in dead_days):
            trades.append((buy_date, day, buy_price, float(close[day])))
            holding = False
    still_holding = holding
    if holding:
        trades.append((buy_date, close.index[-1], buy_price, float(close.iloc[-1])))

    # ---------- 핵심 숫자 ----------
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

    rsi_now = float(rsi_line.iloc[-1]) if not pd.isna(rsi_line.iloc[-1]) else None
    if rsi_now is None:
        rsi_label, rsi_class = "-", ""
    elif rsi_now >= 70:
        rsi_label, rsi_class = f"{rsi_now:.0f} 과매수", "stat-up"
    elif rsi_now <= 30:
        rsi_label, rsi_class = f"{rsi_now:.0f} 과매도", "stat-down"
    else:
        rsi_label, rsi_class = f"{rsi_now:.0f} 중립", ""

    def ret_class(x):
        return "stat-up" if x > 0 else ("stat-down" if x < 0 else "")

    st.caption(f"데이터 출처: {source}")
    st.markdown(f"""
<div class="stat-row">
  <div class="stat-card">
    <div class="stat-label">현재가</div>
    <div class="stat-value">{last_price:,.0f}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">기간 수익률 (그냥 들고 있었으면)</div>
    <div class="stat-value {ret_class(buy_hold_return)}">{buy_hold_return:+.1f}%</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">전략 수익률 (크로스 매매했으면)</div>
    <div class="stat-value {ret_class(strategy_return)}">{strategy_return:+.1f}%</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">현재 RSI</div>
    <div class="stat-value {rsi_class}">{rsi_label}</div>
  </div>
</div>
""", unsafe_allow_html=True)
    st.write("")

    # ---------- 탭: 차트 / 매매 내역 / 읽는 법 ----------
    tab_chart, tab_trades, tab_guide = st.tabs(["🕯️ 차트", "📋 매매 내역", "📖 읽는 법"])

    with tab_chart:
        has_ohlc = all(c in data.columns for c in ["Open", "High", "Low"])
        has_volume = "Volume" in data.columns

        # 3단 구성: 가격(+신호) / 거래량 / RSI
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True,
            row_heights=[0.60, 0.17, 0.23], vertical_spacing=0.03,
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
            x=ma_s.index, y=ma_s, name=f"MA{s_win}",
            line=dict(color=MA_S_C, width=1.2),
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=ma_l.index, y=ma_l, name=f"MA{l_win}",
            line=dict(color=MA_L_C, width=1.0),
            opacity=0.85,
        ), row=1, col=1)

        low_ref = data["Low"] if has_ohlc else close
        high_ref = data["High"] if has_ohlc else close
        if len(golden_days) > 0:
            fig.add_trace(go.Scatter(
                x=golden_days, y=low_ref[golden_days] * 0.985,
                mode="markers", name="골든크로스 ⭐",
                marker=dict(symbol="star", size=15, color=GOLD,
                            line=dict(width=1, color=BG)),
            ), row=1, col=1)
        if len(dead_days) > 0:
            fig.add_trace(go.Scatter(
                x=dead_days, y=high_ref[dead_days] * 1.015,
                mode="markers", name="데드크로스 🔻",
                marker=dict(symbol="triangle-down", size=14, color=PURPLE,
                            line=dict(width=1, color=BG)),
            ), row=1, col=1)

        # 과매수/과매도 진입 마커 (다이아몬드)
        if len(ob_days) > 0:
            fig.add_trace(go.Scatter(
                x=ob_days, y=high_ref[ob_days] * 1.045,
                mode="markers", name="과매수 진입 💠",
                marker=dict(symbol="diamond", size=10, color=OB_C,
                            line=dict(width=1, color=BG)),
            ), row=1, col=1)
        if len(os_days) > 0:
            fig.add_trace(go.Scatter(
                x=os_days, y=low_ref[os_days] * 0.955,
                mode="markers", name="과매도 진입 💠",
                marker=dict(symbol="diamond", size=10, color=OS_C,
                            line=dict(width=1, color=BG)),
            ), row=1, col=1)

        if has_volume:
            open_ref = data["Open"] if has_ohlc else data["Close"]
            vol_colors = [UP if c >= o else DOWN
                          for c, o in zip(data["Close"], open_ref)]
            fig.add_trace(go.Bar(
                x=data.index, y=data["Volume"], name="거래량",
                marker_color=vol_colors, opacity=0.55,
            ), row=2, col=1)

        # RSI 패널: 70 위/30 아래 구간을 색으로 칠하고 기준선 표시
        fig.add_trace(go.Scatter(
            x=rsi_line.index, y=rsi_line, name="RSI(14)",
            line=dict(color=RSI_C, width=1.4),
        ), row=3, col=1)
        fig.add_hrect(y0=70, y1=100, fillcolor="rgba(255,109,0,0.10)",
                      line_width=0, row=3, col=1)
        fig.add_hrect(y0=0, y1=30, fillcolor="rgba(0,229,255,0.08)",
                      line_width=0, row=3, col=1)
        fig.add_hline(y=70, line=dict(color=OB_C, width=1, dash="dot"), row=3, col=1)
        fig.add_hline(y=30, line=dict(color=OS_C, width=1, dash="dot"), row=3, col=1)

        fig.update_layout(
            height=760,
            paper_bgcolor=BG, plot_bgcolor=BG,
            font=dict(color=TEXT, size=12),
            hovermode="x unified",
            dragmode="pan",
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0),
            margin=dict(l=10, r=10, t=30, b=10),
            title=dict(text=f"{q['ticker']}  ·  {PERIOD_LABEL[q['period']]}",
                       x=0.5, font=dict(size=15)),
        )
        fig.update_xaxes(gridcolor=PANEL, zeroline=False,
                         rangebreaks=[dict(bounds=["sat", "mon"])])
        fig.update_yaxes(gridcolor=PANEL, zeroline=False)
        fig.update_yaxes(range=[0, 100], row=3, col=1)

        st.plotly_chart(fig, use_container_width=True,
                        config={"scrollZoom": True, "displaylogo": False})
        st.caption("🖱️ 휠: 확대/축소 · 드래그: 이동 · 더블클릭: 원위치")
        st.toast("분석 완료!", icon="✅")

    with tab_trades:
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

    with tab_guide:
        st.markdown(f"""
- ⭐ <span style="color:{GOLD}">**금색 별 (골든크로스)**</span>: 단기({s_win}일) 평균이 장기({l_win}일) 평균을 **위로** 뚫은 날.
- 🔻 <span style="color:{PURPLE}">**보라 삼각형 (데드크로스)**</span>: 반대로 **아래로** 뚫은 날.
- 💠 <span style="color:{OB_C}">**주황 다이아 (과매수 진입)**</span>: RSI가 70을 넘은 날. 급등 중이라는 뜻이지만 과열이라 조정이 올 수도 있다는 뜻이기도 해.
- 💠 <span style="color:{OS_C}">**하늘 다이아 (과매도 진입)**</span>: RSI가 30 아래로 내려간 날. 과하게 빠졌다는 신호.
- **RSI 패널(맨 아래)**: 주황 선이 RSI(14). 주황 구간(70↑)이 과매수, 하늘 구간(30↓)이 과매도.
- **전략 수익률 vs 기간 수익률**: 크로스 신호대로 사고팔았을 때와 그냥 들고 있었을 때의 비교.
  전략이 항상 이기는 게 아니라는 걸 직접 확인하는 게 이 도구의 진짜 목적이야.
- 수수료·세금·슬리피지는 계산에 안 들어가 있어서 실제 수익률은 이것보다 낮아져.
""", unsafe_allow_html=True)
