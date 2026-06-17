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

# 음성 입력 (선택적): 패키지가 없거나 설치 실패해도 사이트는 글자로 정상 작동
try:
    from streamlit_mic_recorder import speech_to_text
    MIC_AVAILABLE = True
except Exception:
    MIC_AVAILABLE = False

warnings.filterwarnings("ignore")

# ---------- 색상표 (다크 + 네온 그린 터미널 테마) ----------
BG      = "#0B0F0D"   # 거의 검정에 가까운 배경
PANEL   = "#121A16"
BORDER  = "#1F2D25"
TEXT    = "#D7E2DA"
SUBTLE  = "#6F7F76"
GREEN   = "#00FF88"   # 네온 그린 (포인트 색)
GREEN_D = "#00C46A"   # 어두운 그린
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
    background: linear-gradient(160deg, {PANEL} 0%, #0E1511 100%);
    border: 1px solid {BORDER}; border-radius: 14px;
    padding: 16px 20px;
    animation: fadeUp 0.55s ease backwards;
    transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
}}
.stat-card:hover {{
    transform: translateY(-3px);
    border-color: {GREEN};
    box-shadow: 0 8px 26px rgba(0, 255, 136, 0.12);
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
    border-color: {GREEN};
    box-shadow: 0 0 18px rgba(0, 255, 136, 0.22);
}}
[data-testid="stPlotlyChart"], .stTabs {{ animation: fadeUp 0.6s ease; }}
[data-testid="stHeader"] {{ background: transparent; }}
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
.glow-1 {{ top: -28vw; right: -22vw; background: rgba(0,255,136,0.07); }}
.glow-2 {{ bottom: -30vw; left: -24vw; background: rgba(0,196,106,0.06); animation-delay: 4.5s; }}
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


def atr_pct(high, low, close, window: int = 14):
    """ATR(평균 변동폭)을 '현재가 대비 몇 %' 로 돌려준다.
    그 종목이 평소 하루에 얼마나 출렁이는지의 척도. 고가/저가가 없으면 종가로 근사."""
    close = close.astype(float)
    if high is None or low is None:
        # 고가/저가가 없으면 전일 종가 대비 변동폭으로 근사
        tr = (close - close.shift(1)).abs()
    else:
        high = high.astype(float); low = low.astype(float)
        prev = close.shift(1)
        # True Range: 고저폭, 전일종가~고가, 전일종가~저가 중 최댓값
        tr = pd.concat([(high - low),
                        (high - prev).abs(),
                        (low - prev).abs()], axis=1).max(axis=1)
    atr = tr.rolling(window).mean().iloc[-1]
    cur = float(close.iloc[-1])
    if cur <= 0 or pd.isna(atr):
        return None
    return float(atr) / cur * 100  # 현재가 대비 %


# 종목 코드 → 그 종목이 속한 시장지수 티커
def index_ticker_for(ticker: str):
    t = ticker.upper().strip()
    if t.endswith(".KS"):
        return "^KS11", "코스피"
    if t.endswith(".KQ"):
        return "^KQ11", "코스닥"
    if t.isdigit() and len(t) == 6:
        return "^KS11", "코스피"   # 숫자 코드는 일단 코스피로
    # 미국 종목: 나스닥 기준 (대부분 우리 스캐너가 나스닥/S&P라)
    return "^IXIC", "나스닥"


@st.cache_data(ttl=1800, show_spinner=False)
def relative_strength(ticker: str, period: str):
    """상대강도: 이 종목이 같은 기간 시장지수보다 얼마나 더(덜) 올랐나.
    종목 상승률 - 지수 상승률. 양수면 시장을 이기는 '주도주', 음수면 시장보다 약함.
    지수 데이터를 못 받으면 (None, ...)로 우아하게 넘어간다."""
    idx_tk, idx_name = index_ticker_for(ticker)
    try:
        idx = yf.download(idx_tk, period=period, progress=False)
        if idx is None or idx.empty:
            return None, idx_name, None, None
        if isinstance(idx.columns, pd.MultiIndex):
            idx.columns = idx.columns.get_level_values(0)
        ic = idx["Close"].dropna()
        if len(ic) < 2:
            return None, idx_name, None, None
        idx_ret = (float(ic.iloc[-1]) / float(ic.iloc[0]) - 1) * 100
        return idx_ret, idx_name, idx_tk, ic
    except Exception:
        return None, idx_name, None, None


def overheat_score(close: pd.Series):
    """과열·위험 점수 (0~100). 높을수록 '이미 많이 올라서 지금 새로 들어가면 위험'.
    예측이 아니라 현재 과열 정도를 요약하는 것. 낮다고 매수 신호가 아니다.
    각 재료는 0~max점, 합쳐서 100점 만점으로 환산."""
    if len(close) < 25:
        return None, {}

    parts = {}

    # (1) RSI(6일) 과열: 70~85 구간을 0~25점으로
    r = float(rsi(close, 6).iloc[-1])
    parts["RSI 과열"] = max(0.0, min(25.0, (r - 70) / 15 * 25)) if r > 70 else 0.0

    # (2) 신고가 대비 위치: 최근 60일 고점에 얼마나 붙어있나 (95%↑부터 점수)
    hi = float(close.iloc[-60:].max()) if len(close) >= 60 else float(close.max())
    ratio = float(close.iloc[-1]) / hi if hi > 0 else 0
    parts["고점 근접"] = max(0.0, min(20.0, (ratio - 0.95) / 0.05 * 20)) if ratio > 0.95 else 0.0

    # (3) 이동평균 이격도: 현재가가 20일선보다 얼마나 위로 떠 있나 (10%↑부터)
    ma20 = float(close.rolling(20).mean().iloc[-1])
    disp = (float(close.iloc[-1]) / ma20 - 1) * 100 if ma20 > 0 else 0
    parts["이동평균 이격"] = max(0.0, min(20.0, (disp - 10) / 15 * 20)) if disp > 10 else 0.0

    # (4) 단기 급등폭: 최근 20일 상승률 (20%↑부터)
    ret20 = (float(close.iloc[-1]) / float(close.iloc[-21]) - 1) * 100 if len(close) > 21 else 0
    parts["단기 급등"] = max(0.0, min(20.0, (ret20 - 20) / 30 * 20)) if ret20 > 20 else 0.0

    # (5) 볼린저밴드 상단 돌파 정도
    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    up = float((mid + 2 * std).iloc[-1])
    midv = float(mid.iloc[-1])
    if up > midv:
        bb_pos = (float(close.iloc[-1]) - midv) / (up - midv)  # 1.0=상단, 0=중심
        parts["밴드 상단"] = max(0.0, min(15.0, (bb_pos - 0.8) / 0.4 * 15)) if bb_pos > 0.8 else 0.0
    else:
        parts["밴드 상단"] = 0.0

    total = round(sum(parts.values()))
    return total, {k: round(v, 1) for k, v in parts.items()}


def overheat_label(score):
    """점수 → 단계/색."""
    if score is None:
        return "-", ""
    if score >= 70:
        return f"{score} 매우 과열", "stat-up"
    if score >= 45:
        return f"{score} 과열", "stat-up"
    if score >= 25:
        return f"{score} 주의", ""
    return f"{score} 안전권", ""


# ---------- 공포·탐욕 온도계 (시장 전체) ----------
@st.cache_data(ttl=1800, show_spinner=False)
def breadth_one(market_key: str, code: str, today_key: str):
    """종목 하나의 시장폭 기여를 계산: (상승?, 20일선위?, 신고가근접?). 실패 시 None.
    종목 단위로 캐시되니까 스캐너/공포탐욕에서 같은 종목은 재사용된다."""
    try:
        if market_key == "KR":
            import FinanceDataReader as fdr
            df = fdr.DataReader(code, datetime.today() - timedelta(days=120))
        else:
            df = yf.download(code, period="4mo", progress=False)
            if df is not None and isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
    except Exception:
        return None
    if df is None or len(df) < 25:
        return None
    c = df["Close"].astype(float).dropna()
    if len(c) < 25:
        return None
    is_up = bool(c.iloc[-1] > c.iloc[-2])
    above_ma = bool(c.iloc[-1] > c.rolling(20).mean().iloc[-1])
    hi = c.iloc[-60:].max() if len(c) >= 60 else c.max()
    near_high = bool(hi > 0 and c.iloc[-1] / hi >= 0.97)
    return (is_up, above_ma, near_high)


@st.cache_data(ttl=3600, show_spinner=False)
def breadth_listing(market_key: str, n: int):
    """공포탐욕용 종목 명단."""
    if market_key == "KR":
        return load_krx_top(n)
    return load_us(market_key, n)


def fear_greed_label(score):
    """공포·탐욕 점수 → 단계/색/이모지."""
    if score is None:
        return "-", "", "⚪"
    if score >= 75:
        return "극단적 탐욕", "stat-up", "🔥"
    if score >= 55:
        return "탐욕", "stat-up", "😎"
    if score >= 45:
        return "중립", "", "😐"
    if score >= 25:
        return "공포", "stat-down", "😨"
    return "극단적 공포", "stat-down", "🥶"


# ============================================================
#  AI 비서 두뇌 (규칙 기반 — API 없이 데이터를 말로 풀어줌)
# ============================================================
def assistant_collect(ticker: str, period: str = "6mo"):
    """종목의 지표들을 한 번에 모은다. 비서가 이걸 보고 답을 만든다."""
    import time
    data, source = fetch_ohlc(ticker, period)
    # 야후가 일시적으로 막으면 잠깐 쉬고 한 번 더 (미국 종목에서 자주 발생)
    bad0 = (data is None or len(data) == 0 or "Close" not in getattr(data, "columns", []))
    if bad0:
        try:
            fetch_ohlc.clear()  # 캐시 비우고 재시도
        except Exception:
            pass
        time.sleep(1.2)
        data, source = fetch_ohlc(ticker, period)

    bad = (data is None or len(data) == 0 or "Close" not in getattr(data, "columns", []))
    if not bad:
        close = data["Close"].squeeze()
        if not isinstance(close, pd.Series) or close.dropna().shape[0] < 25:
            bad = True
    if bad:
        return None

    close = data["Close"].squeeze().dropna()
    cur = float(close.iloc[-1])
    info = {"ticker": ticker.upper(), "cur": cur, "_close": close}

    # 과열 점수
    oh, oh_parts = overheat_score(close)
    info["overheat"] = oh
    info["overheat_parts"] = oh_parts

    # RSI(6)
    try:
        info["rsi"] = float(rsi(close, 6).iloc[-1])
    except Exception:
        info["rsi"] = None

    # 상대강도
    idx_ret, idx_name, idx_tk, idx_close = relative_strength(ticker, period)
    info["idx_name"] = idx_name
    if idx_ret is not None:
        stock_ret = (cur / float(close.iloc[0]) - 1) * 100
        info["stock_ret"] = stock_ret
        info["idx_ret"] = idx_ret
        info["rel_strength"] = stock_ret - idx_ret
    else:
        info["rel_strength"] = None

    # ATR 기반 손절·익절
    hi = data["High"] if "High" in data.columns else None
    lo = data["Low"] if "Low" in data.columns else None
    atrp = atr_pct(hi, lo, close)
    info["atr_pct"] = atrp
    stop_pct = 8.0 if atrp is None else max(4.0, min(20.0, atrp * 2.0))
    info["stop_pct"] = stop_pct
    info["target_pct"] = stop_pct * 1.5
    info["stop_price"] = cur * (1 - stop_pct / 100)
    info["target_price"] = cur * (1 + stop_pct * 1.5 / 100)

    # 신고가 근접
    hi60 = float(close.iloc[-60:].max()) if len(close) >= 60 else float(close.max())
    info["to_high"] = (hi60 / cur - 1) * 100 if cur > 0 else 0.0

    # 이동평균 정배열 여부 (20 > 60)
    if len(close) >= 60:
        ma20 = float(close.rolling(20).mean().iloc[-1])
        ma60 = float(close.rolling(60).mean().iloc[-1])
        info["ma_aligned"] = ma20 > ma60
    else:
        info["ma_aligned"] = None

    return info


def assistant_answer(info: dict, question: str = "") -> str:
    """모은 지표 + 질문으로 한국어 답을 조립한다. 예측·추천은 절대 안 함."""
    q = question.strip()
    t = info["ticker"]
    oh = info.get("overheat")
    rs = info.get("rel_strength")
    rsi_v = info.get("rsi")

    # --- 질문 의도 파악 (키워드 기반) ---
    ask_danger = any(w in q for w in ["위험", "괜찮", "조심", "물려", "물릴"])
    ask_enter = any(w in q for w in ["들어가", "사도", "매수", "지금 사", "진입", "타이밍"])
    ask_strong = any(w in q for w in ["강", "주도", "잘 가", "센", "약"])
    ask_sell = any(w in q for w in ["팔", "매도", "익절", "손절"])

    lines = []

    # 과열 상태는 거의 모든 답에 깔아줌
    if oh is not None:
        if oh >= 70:
            lines.append(f"{t}는 지금 과열·위험 점수가 {oh}/100으로 **매우 과열** 상태야. 이미 단기적으로 많이 오른 자리라는 뜻이야.")
        elif oh >= 45:
            lines.append(f"{t}는 과열 점수 {oh}/100으로 **과열** 구간이야. 새로 들어가기엔 좀 부담스러운 자리야.")
        elif oh >= 25:
            lines.append(f"{t}는 과열 점수 {oh}/100으로 **주의** 정도야. 극단적으로 과열되진 않았어.")
        else:
            lines.append(f"{t}는 과열 점수 {oh}/100으로 **안전권**이야. 과열로 인한 위험은 낮은 편이야.")

    # 상대강도
    if rs is not None:
        if rs > 5:
            lines.append(f"상대강도는 시장({info['idx_name']})보다 {rs:+.1f}%p 강해 — 주도주 쪽이야. 시장을 이기고 있다는 뜻이지.")
        elif rs < -5:
            lines.append(f"상대강도는 시장보다 {rs:.1f}%p 약해. 같은 기간 시장이 더 잘 갔으니, 오르더라도 힘이 약한 상승이야.")
        else:
            lines.append(f"상대강도는 시장이랑 비슷한 수준이야. 특별히 강하지도 약하지도 않아.")

    # RSI
    if rsi_v is not None:
        if rsi_v >= 75:
            lines.append(f"단기 RSI가 {rsi_v:.0f}으로 과열(과매수) 구간이야 — 단기 조정이 올 수도 있어.")
        elif rsi_v <= 30:
            lines.append(f"단기 RSI가 {rsi_v:.0f}으로 과매도 구간이야 — 과하게 빠졌다는 신호일 수 있어.")

    # 질문별 결론 한 줄
    if ask_enter or ask_danger:
        if oh is not None and oh >= 45:
            lines.append("👉 종합하면, **지금 새로 진입하는 건 신중한 게 좋아.** 과열 구간이라 고점에서 물릴 위험이 있어. 꼭 들어가려면 손절선을 먼저 정해두고 분할로.")
        elif oh is not None and oh < 25 and (rs is None or rs > -5):
            lines.append("👉 종합하면, 과열로 인한 위험은 낮은 편이야. 다만 '안전 점수가 낮다 = 사도 좋다'는 절대 아니야 — 회사 실적이랑 시장 상황은 따로 봐야 해.")
        else:
            lines.append("👉 종합하면, 애매한 구간이야. 확신이 없으면 한 번에 들어가지 말고 나눠서, 손절선 정해두고 접근해.")
    elif ask_sell:
        lines.append(f"👉 손절선은 {info['stop_price']:,.0f}(-{info['stop_pct']:.0f}%), 익절목표는 {info['target_price']:,.0f}(+{info['target_pct']:.0f}%)로 잡아둘 만해. 단 이건 미리 정하는 규칙이지 '여기까지 온다'는 예측이 아니야.")
    elif ask_strong:
        pass  # 상대강도는 위에서 이미 말함

    # 마무리 경고
    lines.append("— 이건 현재 상태 요약이지 '사라/팔라'나 미래 예측이 아니야. 최종 판단은 네가 하는 거야.")

    return "\n\n".join(lines)


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
    """국내(코스피+코스닥) 종목을 시가총액 순으로 상위 n개 돌려준다.
    원래는 KRX 서버에서 명단을 받았는데, KRX가 해외 서버 요청을 막아서
    네이버 금융 시가총액 페이지를 읽는 방식으로 우회한다."""
    import requests, re
    from io import StringIO

    headers = {"User-Agent": "Mozilla/5.0"}
    frames = []
    pages = (n - 1) // 50 + 1  # 한 페이지에 50종목씩

    for sosok, mkt in [(0, "KOSPI"), (1, "KOSDAQ")]:
        for page in range(1, pages + 1):
            url = (f"https://finance.naver.com/sise/sise_market_sum.naver"
                   f"?sosok={sosok}&page={page}")
            r = requests.get(url, headers=headers, timeout=10)
            r.encoding = "euc-kr"
            html = r.text

            # 종목명 → 코드 짝을 링크에서 뽑아낸다
            code_map = {}
            for m in re.finditer(r'code=(\d{6})"\s*class="tltle">([^<]+)', html):
                code_map[m.group(2).strip()] = m.group(1)

            tables = pd.read_html(StringIO(html))
            df = max(tables, key=len)          # 페이지에서 제일 큰 표가 시총 순위표
            df = df.dropna(subset=["종목명"])
            df["Code"] = df["종목명"].map(code_map)
            df = df.dropna(subset=["Code"])
            df["Market"] = mkt
            frames.append(df[["Code", "종목명", "Market", "시가총액"]])

    out = pd.concat(frames).rename(columns={"종목명": "Name", "시가총액": "Marcap"})
    out["Marcap"] = pd.to_numeric(out["Marcap"], errors="coerce")
    out = out[~out["Name"].str.contains("스팩", na=False)]  # 스팩 제외
    out = (out.sort_values("Marcap", ascending=False)
              .drop_duplicates("Code").head(n))
    return out[["Code", "Name", "Market"]].reset_index(drop=True)


@st.cache_data(ttl=3600, show_spinner=False)
def load_us(market_name: str, n: int):
    """미국 종목 명단(S&P500 또는 NASDAQ)에서 n개를 돌려준다.
    시가총액 정보가 있으면 큰 순서대로, 없으면 명단 순서대로."""
    import FinanceDataReader as fdr
    df = fdr.StockListing(market_name)
    cap_col = next((c for c in ["Marcap", "MarketCap", "marketCap"] if c in df.columns), None)
    if cap_col:
        df = df.sort_values(cap_col, ascending=False)
    df = df.head(n).copy()
    df["Market"] = market_name
    if "Symbol" in df.columns:
        df = df.rename(columns={"Symbol": "Code"})
    return df[["Code", "Name", "Market"]].reset_index(drop=True)


def compute_signals(c: pd.Series, v, high=None, low=None):
    """종가(c)와 거래량(v)으로 신호를 계산한다. 국내/미국 공용.
    high/low가 있으면 ATR(종목 변동성)로 손절·익절 폭을 종목마다 다르게 계산."""
    ret5 = float((c.iloc[-1] / c.iloc[-6] - 1) * 100) if len(c) > 6 else 0.0
    day_ret = float((c.iloc[-1] / c.iloc[-2] - 1) * 100) if len(c) > 2 else 0.0

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
    # 거래량이 평소(20일 평균)의 3배 이상 터졌을 때:
    #  - 가격도 당일 +3% 이상 올랐으면 → 거래량 동반 급등 (시세 분출)
    #  - 가격은 아직 잠잠하면 → 거래량만 급증 (뭔가 꿈틀거리는 중)
    if vol_ratio >= 3 and day_ret >= 3:
        signals.append("🔥 거래량 급등+상승")
    elif vol_ratio >= 3:
        signals.append("📊 거래량 급증")
    if recent_golden:
        signals.append("⭐ 골든크로스(5일 내)")

    if not signals:
        return None  # 신호 없는 종목은 표에서 제외

    oh, _ = overheat_score(c)
    oh_mark = ""
    oh_val = oh if oh is not None else 999  # 정렬용 (점수 없으면 맨 뒤로)
    if oh is not None:
        if oh >= 70: oh_mark = f"🔴 매우과열 {oh}"
        elif oh >= 45: oh_mark = f"🟠 과열 {oh}"
        elif oh >= 25: oh_mark = f"🟡 주의 {oh}"
        else: oh_mark = f"🟢 {oh}"

    # 매매 가이드는 분석기의 '매매 플랜' 탭으로 옮겼음.
    # 스캐너는 다시 가볍게 — 신호와 과열도까지만 보여주고, 자세한 건 종목 클릭해서 보게.
    return {
        "현재가": round(float(c.iloc[-1]), 2),
        "당일(%)": round(day_ret, 1),
        "5일 수익률(%)": round(ret5, 1),
        "거래량배수": round(vol_ratio, 1),
        "신호": " · ".join(signals),
        "과열도": oh_mark,
        "_oh": oh_val,  # 정렬 전용 (표시 전 제거됨)
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
    h = df["High"].astype(float) if "High" in df.columns else None
    l = df["Low"].astype(float) if "Low" in df.columns else None
    return compute_signals(c, v, h, l)


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
    h = df["High"].astype(float) if "High" in df.columns else None
    l = df["Low"].astype(float) if "Low" in df.columns else None
    return compute_signals(c, v, h, l)


# ---------- 실시간 모드용 함수들 ----------
@st.cache_data(ttl=10, show_spinner=False)
def fetch_minute(ticker: str):
    """오늘 하루치 1분봉 데이터 (야후). 10초 동안만 저장해서 거의 매번 새로 받는다."""
    t = ticker.upper().strip()
    try:
        df = yf.download(t, period="1d", interval="1m", progress=False)
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df.dropna(subset=["Close"])
    except Exception:
        pass
    return None


@st.cache_data(ttl=10, show_spinner=False)
def fetch_quote_kr(code6: str):
    """네이버 실시간 시세 (국내 현재가 + 등락률). 분봉이 막혔을 때의 예비용."""
    import requests
    url = f"https://polling.finance.naver.com/api/realtime/domestic/stock/{code6}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
    d = r.json()["datas"][0]
    price = float(str(d["closePrice"]).replace(",", ""))
    rate = float(str(d.get("fluctuationsRatio", "0")).replace(",", ""))
    return price, rate


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
    # ---- 네온 그린 홀로그램 배경: 바닥+천장 그리드, 스캔 빔, 떠다니는 차트 ----
    st.markdown(f"""
<style>
.block-container {{ position: relative; z-index: 1; }}
.holo-bg {{ position: fixed; inset: 0; z-index: 0; overflow: hidden; pointer-events: none; }}

/* 바닥 그리드 (네온 그린) */
.holo-grid {{
    position: absolute; left: -50%; bottom: -24%; width: 200%; height: 64%;
    background-image:
        linear-gradient(rgba(0,255,136,0.14) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,136,0.14) 1px, transparent 1px);
    background-size: 48px 48px;
    transform: perspective(640px) rotateX(62deg);
    animation: gridScroll 8s linear infinite;
    -webkit-mask-image: linear-gradient(to top, rgba(0,0,0,.95), transparent 85%);
    mask-image: linear-gradient(to top, rgba(0,0,0,.95), transparent 85%);
}}
/* 천장 그리드 (더 옅게, 반대 방향) */
.holo-grid-top {{
    position: absolute; left: -50%; top: -26%; width: 200%; height: 50%;
    background-image:
        linear-gradient(rgba(0,255,136,0.07) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,136,0.07) 1px, transparent 1px);
    background-size: 48px 48px;
    transform: perspective(640px) rotateX(-62deg);
    animation: gridScroll 11s linear infinite reverse;
    -webkit-mask-image: linear-gradient(to bottom, rgba(0,0,0,.85), transparent 85%);
    mask-image: linear-gradient(to bottom, rgba(0,0,0,.85), transparent 85%);
}}
@keyframes gridScroll {{ from {{ background-position-y: 0; }} to {{ background-position-y: 48px; }} }}

/* 화면을 천천히 가로지르는 스캔 빔 */
.scan-beam {{
    position: absolute; top: 0; bottom: 0; width: 140px;
    background: linear-gradient(90deg, transparent,
                rgba(0,255,136,0.05) 40%, rgba(0,255,136,0.10) 50%,
                rgba(0,255,136,0.05) 60%, transparent);
    animation: beamSweep 13s linear infinite;
}}
@keyframes beamSweep {{ from {{ left: -12%; }} to {{ left: 108%; }} }}

/* 제목 뒤 은은한 초록 광원 */
.title-glow {{
    position: absolute; top: 6%; left: 50%; transform: translateX(-50%);
    width: 60vw; height: 34vh; border-radius: 50%;
    background: radial-gradient(ellipse, rgba(0,255,136,0.10), transparent 70%);
    animation: breatheGlow 6s ease-in-out infinite;
}}
@keyframes breatheGlow {{ 0%,100% {{ opacity: .55; }} 50% {{ opacity: 1; }} }}

/* 떠다니는 홀로그램 차트 */
.holo-card {{
    position: absolute; opacity: .5;
    filter: drop-shadow(0 0 16px rgba(0,255,136,.5));
    animation: holoFloat 9s ease-in-out infinite;
    transform-style: preserve-3d;
}}
@keyframes holoFloat {{
    0%,100% {{ transform: perspective(800px) rotateY(-12deg) translateY(0); }}
    50%     {{ transform: perspective(800px) rotateY(-5deg)  translateY(-22px); }}
}}
.holo-line {{
    stroke-dasharray: 900; stroke-dashoffset: 900;
    animation: holoDraw 7s ease-in-out infinite;
}}
@keyframes holoDraw {{
    0%   {{ stroke-dashoffset: 900; opacity: .15; }}
    55%  {{ stroke-dashoffset: 0;   opacity: 1;  }}
    85%  {{ stroke-dashoffset: 0;   opacity: 1;  }}
    100% {{ stroke-dashoffset: 0;   opacity: 0;  }}
}}
.holo-candles rect {{
    transform-origin: center bottom; transform-box: fill-box;
    animation: candlePulse 3.4s ease-in-out infinite;
}}
.holo-candles rect:nth-child(odd) {{ animation-delay: .7s; }}
.holo-candles rect:nth-child(3n)  {{ animation-delay: 1.4s; }}
@keyframes candlePulse {{
    0%,100% {{ transform: scaleY(1); }}
    50%     {{ transform: scaleY(1.3); }}
}}

/* 가운데 네온 제목 */
.hero-wrap {{ text-align: center; margin-top: 7vh; }}
.neon-title {{
    font-size: 76px; font-weight: 900; letter-spacing: 8px;
    color: #EAFFF3; margin-bottom: 4px;
    text-shadow:
        0 0 6px {GREEN}, 0 0 18px {GREEN},
        0 0 48px rgba(0,255,136,.55), 0 0 110px rgba(0,255,136,.3);
    animation: neonPulse 3.6s ease-in-out infinite, fadeUp .8s ease;
}}
@keyframes neonPulse {{
    0%,100% {{ text-shadow: 0 0 6px {GREEN}, 0 0 18px {GREEN},
               0 0 48px rgba(0,255,136,.55), 0 0 110px rgba(0,255,136,.3); }}
    50%     {{ text-shadow: 0 0 9px {GREEN}, 0 0 30px {GREEN},
               0 0 70px rgba(0,255,136,.75), 0 0 150px rgba(0,255,136,.4); }}
}}
.hero-sub2 {{
    color: {SUBTLE}; font-size: 16px; margin-top: 10px;
    animation: fadeUp .8s ease .15s backwards;
}}
.chip-row2 {{
    display: flex; gap: 10px; flex-wrap: wrap; justify-content: center;
    margin: 26px 0 10px 0; animation: fadeUp .8s ease .3s backwards;
}}
.chip2 {{
    background: rgba(0,255,136,0.05); border: 1px solid {BORDER};
    color: {TEXT}; padding: 8px 14px; border-radius: 999px; font-size: 13.5px;
}}
</style>
<div class="holo-bg">
  <div class="holo-grid-top"></div>
  <div class="holo-grid"></div>
  <div class="scan-beam"></div>
  <div class="title-glow"></div>

  <!-- 오른쪽: 큰 네온 라인차트 -->
  <svg class="holo-card" style="top:18%; right:3%; animation-delay:.2s"
       width="430" height="230" viewBox="0 0 430 230">
    <polyline class="holo-line" fill="none" stroke="#00FF88" stroke-width="2.4"
        points="0,200 40,160 70,178 110,120 145,140 190,84 225,108 270,60 310,82 360,38 430,52"/>
    <polyline fill="none" stroke="#00C46A" stroke-width="1" opacity="0.3"
        points="0,212 70,190 140,196 210,152 280,160 350,114 430,124"/>
    <circle cx="190" cy="84" r="4" fill="#00FF88"/>
    <circle cx="360" cy="38" r="4" fill="#00FF88"/>
  </svg>

  <!-- 왼쪽 아래: 캔들 + 라인 -->
  <svg class="holo-card" style="bottom:13%; left:2%; animation-delay:1.6s; opacity:.42"
       width="340" height="190" viewBox="0 0 340 190">
    <g class="holo-candles">
      <rect x="20"  y="106" width="12" height="60" fill="#F23645" opacity=".75"/>
      <rect x="55"  y="124" width="12" height="42" fill="#3179F5" opacity=".75"/>
      <rect x="90"  y="92"  width="12" height="74" fill="#F23645" opacity=".75"/>
      <rect x="125" y="110" width="12" height="56" fill="#F23645" opacity=".75"/>
      <rect x="160" y="130" width="12" height="36" fill="#3179F5" opacity=".75"/>
      <rect x="195" y="78"  width="12" height="88" fill="#F23645" opacity=".75"/>
      <rect x="230" y="98"  width="12" height="68" fill="#3179F5" opacity=".75"/>
      <rect x="265" y="60"  width="12" height="106" fill="#F23645" opacity=".75"/>
    </g>
    <polyline class="holo-line" fill="none" stroke="#00FF88" stroke-width="2"
        style="animation-delay:1.2s"
        points="10,136 50,124 90,106 130,118 170,92 210,100 250,66 320,46"/>
  </svg>

  <!-- 왼쪽 위: 작은 스파크라인 -->
  <svg class="holo-card" style="top:14%; left:6%; animation-delay:2.8s; opacity:.3"
       width="240" height="120" viewBox="0 0 240 120">
    <polyline class="holo-line" fill="none" stroke="#7CFFC4" stroke-width="2"
        style="animation-delay:2.2s"
        points="0,90 32,66 60,80 92,44 124,58 162,28 200,42 240,20"/>
  </svg>
</div>
""", unsafe_allow_html=True)

    # ---- 위쪽: 작은 타이틀 ----
    st.markdown(
        '<div class="hero-wrap">'
        '<p class="neon-title">STOCK&nbsp;ANALYZER</p>'
        '<p class="hero-sub2">이동평균 · RSI · 볼린저밴드 · 백테스트 · 시장 스캐너 — '
        'made by 제현 (with Claude)</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ---- 중앙: 초록 네온 코어 (AI 비서 진입) ----
    st.markdown("""
<style>
.core-wrap {
    display: flex; flex-direction: column; align-items: center;
    margin: 6px 0 2px;
}
.core {
    position: relative; width: 280px; height: 280px;
    display: flex; align-items: center; justify-content: center;
}
/* 가운데 빛나는 핵 */
.core-nucleus {
    position: absolute; width: 54px; height: 54px; border-radius: 50%;
    background: radial-gradient(circle at 40% 35%, #d6ffe9, #00ff88 45%, #00b865 75%);
    box-shadow: 0 0 30px #00ff88, 0 0 70px rgba(0,255,136,.7), 0 0 120px rgba(0,255,136,.4);
    animation: nucleusPulse 2.6s ease-in-out infinite;
    z-index: 3;
}
@keyframes nucleusPulse {
    0%,100% { transform: scale(1);    box-shadow: 0 0 30px #00ff88, 0 0 70px rgba(0,255,136,.7), 0 0 120px rgba(0,255,136,.4); }
    50%     { transform: scale(1.18); box-shadow: 0 0 40px #00ff88, 0 0 95px rgba(0,255,136,.85),0 0 160px rgba(0,255,136,.55); }
}
/* 회전하는 네온 링들 (비스듬히) */
.core-ring {
    position: absolute; border-radius: 50%;
    border: 1.5px solid rgba(0,255,136,.55);
    box-shadow: 0 0 12px rgba(0,255,136,.4), inset 0 0 12px rgba(0,255,136,.25);
}
.ring-1 { width: 130px; height: 130px; animation: spinA 7s linear infinite;  border-style: dashed; }
.ring-2 { width: 190px; height: 190px; animation: spinB 11s linear infinite reverse; border-top-color: rgba(0,255,136,.9); border-right-color: transparent; }
.ring-3 { width: 250px; height: 250px; animation: spinA 16s linear infinite; border-left-color: rgba(124,255,196,.9); border-bottom-color: transparent; }
/* 3D 느낌: 비스듬한 타원 링 (자전하는 적도처럼) */
.ring-eq {
    position: absolute; width: 240px; height: 92px; border-radius: 50%;
    border: 1.5px solid rgba(0,255,136,.45);
    box-shadow: 0 0 14px rgba(0,255,136,.3);
    animation: spinFlat 9s linear infinite;
}
.ring-eq2 {
    position: absolute; width: 92px; height: 240px; border-radius: 50%;
    border: 1.5px solid rgba(0,255,136,.35);
    box-shadow: 0 0 14px rgba(0,255,136,.25);
    animation: spinFlat 13s linear infinite reverse;
}
@keyframes spinA { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes spinB { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes spinFlat { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
/* 구 표면 점들 (별가루) */
.core-dots { position: absolute; width: 230px; height: 230px; animation: spinA 24s linear infinite; }
.core-dots span {
    position: absolute; width: 2.5px; height: 2.5px; border-radius: 50%;
    background: #7cffc4; box-shadow: 0 0 4px #00ff88;
}
/* 점들을 CSS로 직접 배치 (구 표면처럼) */
.core-dots span:nth-child(1){left:60px;top:40px;opacity:.7}
.core-dots span:nth-child(2){left:170px;top:55px;opacity:.5}
.core-dots span:nth-child(3){left:200px;top:120px;opacity:.8}
.core-dots span:nth-child(4){left:40px;top:110px;opacity:.6}
.core-dots span:nth-child(5){left:90px;top:30px;opacity:.5}
.core-dots span:nth-child(6){left:150px;top:190px;opacity:.7}
.core-dots span:nth-child(7){left:70px;top:180px;opacity:.6}
.core-dots span:nth-child(8){left:185px;top:160px;opacity:.5}
.core-dots span:nth-child(9){left:115px;top:50px;opacity:.8}
.core-dots span:nth-child(10){left:30px;top:140px;opacity:.5}
.core-dots span:nth-child(11){left:205px;top:90px;opacity:.6}
.core-dots span:nth-child(12){left:130px;top:200px;opacity:.7}
.core-dots span:nth-child(13){left:50px;top:75px;opacity:.5}
.core-dots span:nth-child(14){left:175px;top:30px;opacity:.6}
.core-dots span:nth-child(15){left:100px;top:195px;opacity:.5}
.core-dots span:nth-child(16){left:215px;top:140px;opacity:.7}
.core-dots span:nth-child(17){left:25px;top:100px;opacity:.6}
.core-dots span:nth-child(18){left:145px;top:35px;opacity:.5}
/* 바깥 후광 */
.core-halo {
    position: absolute; width: 300px; height: 300px; border-radius: 50%;
    background: radial-gradient(circle, rgba(0,255,136,.10), transparent 65%);
    animation: haloBreath 4s ease-in-out infinite;
}
@keyframes haloBreath { 0%,100% { opacity:.6; transform:scale(1);} 50%{opacity:1; transform:scale(1.08);} }
/* 클릭 유도 라벨 */
.core-label {
    margin-top: 6px; color: #7cffc4; font-size: 14px; letter-spacing: 3px;
    text-shadow: 0 0 8px rgba(0,255,136,.6); animation: haloBreath 3s ease-in-out infinite;
}
/* hover 시 살짝 커지고 빨라지는 느낌 */
.core:hover .core-nucleus { animation-duration: 1.1s; }
.core:hover .ring-1 { animation-duration: 2.5s; }
.core:hover .ring-2 { animation-duration: 4s; }
.core { cursor: default; transition: transform .25s; }
.core-wrap:hover .core { transform: scale(1.05); }

/* SVG 그물망 구 (위선/경선) */
.core-mesh { position:absolute; width:230px; height:230px; animation: spinA 30s linear infinite; opacity:.55; }
.core-mesh ellipse, .core-mesh circle { fill:none; stroke:#00ff88; stroke-width:.6; vector-effect:non-scaling-stroke; }
/* 중심에서 뻗는 빛줄기 */
.core-rays { position:absolute; width:260px; height:260px; animation: raySpin 40s linear infinite; }
.core-rays line { stroke:#7cffc4; stroke-width:.8; opacity:.25; }
@keyframes raySpin { from{transform:rotate(0)} to{transform:rotate(-360deg)} }
.ray-flash { animation: rayPulse 3s ease-in-out infinite; }
@keyframes rayPulse { 0%,100%{opacity:.12} 50%{opacity:.4} }
</style>
<div class="core-wrap">
  <div class="core" id="coreBtn">
    <div class="core-halo"></div>
    <!-- 빛줄기 (중심에서 방사형) -->
    <svg class="core-rays" viewBox="0 0 260 260">
      <g class="ray-flash">
        <line x1="130" y1="130" x2="130" y2="6"/>
        <line x1="130" y1="130" x2="254" y2="130"/>
        <line x1="130" y1="130" x2="130" y2="254"/>
        <line x1="130" y1="130" x2="6" y2="130"/>
        <line x1="130" y1="130" x2="218" y2="42"/>
        <line x1="130" y1="130" x2="42" y2="218"/>
        <line x1="130" y1="130" x2="218" y2="218"/>
        <line x1="130" y1="130" x2="42" y2="42"/>
        <line x1="130" y1="130" x2="190" y2="20"/>
        <line x1="130" y1="130" x2="70" y2="240"/>
        <line x1="130" y1="130" x2="240" y2="190"/>
        <line x1="130" y1="130" x2="20" y2="70"/>
      </g>
    </svg>
    <div class="core-halo"></div>
    <div class="core-ring ring-3"></div>
    <div class="core-ring ring-2"></div>
    <!-- 그물망 구 (위선 + 경선) -->
    <svg class="core-mesh" viewBox="0 0 230 230">
      <circle cx="115" cy="115" r="112"/>
      <!-- 위선 (가로 타원, 점점 납작) -->
      <ellipse cx="115" cy="115" rx="112" ry="38"/>
      <ellipse cx="115" cy="115" rx="112" ry="74"/>
      <ellipse cx="115" cy="115" rx="112" ry="104"/>
      <!-- 경선 (세로 타원) -->
      <ellipse cx="115" cy="115" rx="38" ry="112"/>
      <ellipse cx="115" cy="115" rx="74" ry="112"/>
      <ellipse cx="115" cy="115" rx="104" ry="112"/>
    </svg>
    <div class="ring-eq"></div>
    <div class="ring-eq2"></div>
    <div class="core-ring ring-1"></div>
    <div class="core-dots" id="coreDots"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>
    <div class="core-nucleus"></div>
  </div>
</div>
""", unsafe_allow_html=True)

    # 구 바로 아래에 딱 붙는 버튼 (구와 한 덩어리처럼) — 누르면 AI 페이지로
    bcol1, bcol2, bcol3 = st.columns([1, 1.6, 1])
    with bcol2:
        st.button("◆  코어 활성화 · AI 비서 깨우기  ◆", key="core_to_ai",
                  type="primary", use_container_width=True,
                  on_click=go_page, args=("ai",))

    st.write("")

    # ---- 아래: 기능 칩 ----
    st.markdown(
        '<div class="hero-wrap">'
        '<div class="chip-row2">'
        '<span class="chip2">🕯️ 인터랙티브 캔들차트</span>'
        '<span class="chip2">⭐ 골든/데드크로스</span>'
        '<span class="chip2">🌡️ RSI 과매수/과매도</span>'
        '<span class="chip2">🚨 급등 신호 스캐너</span>'
        '<span class="chip2">🧪 전략 백테스트</span>'
        '</div></div>',
        unsafe_allow_html=True,
    )
    st.write("")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.button("📊 분석기", use_container_width=True,
                  on_click=go_page, args=("app",))
    with c2:
        st.button("🚨 시장 스캐너", use_container_width=True,
                  on_click=go_page, args=("scanner",))
    with c3:
        st.button("🌡️ 공포·탐욕", use_container_width=True,
                  on_click=go_page, args=("feargreed",))
    with c4:
        st.button("📖 사용법", use_container_width=True,
                  on_click=go_page, args=("guide",))

    st.markdown(
        f'<p style="text-align:center; color:{SUBTLE}; font-size:13px; margin-top:14px;">'
        '⚠️ 이 도구는 과거 신호를 보여주는 거지 미래를 예측하거나 매수/매도를 추천하는 게 아니야.</p>',
        unsafe_allow_html=True,
    )

# ============================================================
#  AI 비서 화면
# ============================================================
elif st.session_state.page == "ai":
    st.markdown(AMBIENT_BG, unsafe_allow_html=True)
    st.button("← 홈으로", on_click=go_page, args=("home",))

    # 큰 코어 (AI 비서의 얼굴)
    st.markdown("""
<style>
.ai-core-wrap { display:flex; flex-direction:column; align-items:center; margin: 10px 0 4px;
    animation: warpIn 1.1s cubic-bezier(.2,.8,.2,1) both; }
/* 빨려들어온 듯 확 나타나는 등장: 작게 회전하며 시작 → 제자리 */
@keyframes warpIn {
    0%   { transform: scale(0.04) rotate(-220deg); opacity: 0; filter: blur(8px); }
    55%  { opacity: 1; filter: blur(0); }
    70%  { transform: scale(1.12) rotate(8deg); }
    100% { transform: scale(1) rotate(0deg); opacity: 1; }
}
.ai-core { position: relative; width: 340px; height: 340px; display:flex; align-items:center; justify-content:center; }
.ai-nucleus {
    position:absolute; width:70px; height:70px; border-radius:50%;
    background: radial-gradient(circle at 40% 35%, #d6ffe9, #00ff88 45%, #00b865 75%);
    box-shadow: 0 0 36px #00ff88, 0 0 90px rgba(0,255,136,.7), 0 0 150px rgba(0,255,136,.45);
    animation: aiPulse 2.4s ease-in-out infinite; z-index:3;
}
@keyframes aiPulse {
    0%,100%{ transform:scale(1);} 50%{ transform:scale(1.2);}
}
.ai-ring { position:absolute; border-radius:50%; border:1.5px solid rgba(0,255,136,.55);
    box-shadow:0 0 14px rgba(0,255,136,.4), inset 0 0 14px rgba(0,255,136,.25); }
.ai-r1 { width:160px; height:160px; animation: spinA 6s linear infinite; border-style:dashed; }
.ai-r2 { width:235px; height:235px; animation: spinB 10s linear infinite reverse; border-top-color:rgba(0,255,136,.9); border-right-color:transparent; }
.ai-r3 { width:310px; height:310px; animation: spinA 15s linear infinite; border-left-color:rgba(124,255,196,.9); border-bottom-color:transparent; }
.ai-eq { position:absolute; width:300px; height:115px; border-radius:50%; border:1.5px solid rgba(0,255,136,.45); box-shadow:0 0 16px rgba(0,255,136,.3); animation: spinFlat 8s linear infinite; }
.ai-eq2{ position:absolute; width:115px; height:300px; border-radius:50%; border:1.5px solid rgba(0,255,136,.35); box-shadow:0 0 16px rgba(0,255,136,.25); animation: spinFlat 12s linear infinite reverse; }
.ai-halo { position:absolute; width:380px; height:380px; border-radius:50%;
    background: radial-gradient(circle, rgba(0,255,136,.12), transparent 65%); animation: haloBreath 4s ease-in-out infinite; }
@keyframes spinA{from{transform:rotate(0)}to{transform:rotate(360deg)}}
@keyframes spinB{from{transform:rotate(0)}to{transform:rotate(360deg)}}
@keyframes spinFlat{from{transform:rotate(0)}to{transform:rotate(360deg)}}
@keyframes haloBreath{0%,100%{opacity:.6;transform:scale(1)}50%{opacity:1;transform:scale(1.08)}}
.ai-dots{ position:absolute; width:290px; height:290px; animation: spinA 22s linear infinite; }
.ai-dots span{ position:absolute; width:2.5px; height:2.5px; border-radius:50%; background:#7cffc4; box-shadow:0 0 4px #00ff88; }
.ai-dots span:nth-child(1){left:80px;top:50px;opacity:.7}
.ai-dots span:nth-child(2){left:210px;top:70px;opacity:.5}
.ai-dots span:nth-child(3){left:250px;top:150px;opacity:.8}
.ai-dots span:nth-child(4){left:55px;top:140px;opacity:.6}
.ai-dots span:nth-child(5){left:120px;top:40px;opacity:.5}
.ai-dots span:nth-child(6){left:190px;top:240px;opacity:.7}
.ai-dots span:nth-child(7){left:90px;top:230px;opacity:.6}
.ai-dots span:nth-child(8){left:235px;top:200px;opacity:.5}
.ai-dots span:nth-child(9){left:145px;top:60px;opacity:.8}
.ai-dots span:nth-child(10){left:40px;top:180px;opacity:.5}
.ai-dots span:nth-child(11){left:255px;top:110px;opacity:.6}
.ai-dots span:nth-child(12){left:165px;top:250px;opacity:.7}
.ai-dots span:nth-child(13){left:65px;top:95px;opacity:.5}
.ai-dots span:nth-child(14){left:220px;top:40px;opacity:.6}
.ai-dots span:nth-child(15){left:125px;top:245px;opacity:.5}
.ai-dots span:nth-child(16){left:265px;top:175px;opacity:.7}
.ai-dots span:nth-child(17){left:35px;top:125px;opacity:.6}
.ai-dots span:nth-child(18){left:180px;top:45px;opacity:.5}
.ai-dots span:nth-child(19){left:100px;top:265px;opacity:.6}
.ai-dots span:nth-child(20){left:245px;top:255px;opacity:.5}
.ai-mesh { position:absolute; width:290px; height:290px; animation: spinA 30s linear infinite; opacity:.5; }
.ai-mesh ellipse, .ai-mesh circle { fill:none; stroke:#00ff88; stroke-width:.6; vector-effect:non-scaling-stroke; }
.ai-rays { position:absolute; width:330px; height:330px; animation: raySpin 45s linear infinite; }
.ai-rays line { stroke:#7cffc4; stroke-width:.8; }
.ai-rays g { animation: rayPulse 3.5s ease-in-out infinite; }
@keyframes raySpin { from{transform:rotate(0)} to{transform:rotate(-360deg)} }
@keyframes rayPulse { 0%,100%{opacity:.12} 50%{opacity:.42} }
</style>
<div class="ai-core-wrap">
  <div class="ai-core">
    <div class="ai-halo"></div>
    <svg class="ai-rays" viewBox="0 0 330 330">
      <g>
        <line x1="165" y1="165" x2="165" y2="8"/>
        <line x1="165" y1="165" x2="322" y2="165"/>
        <line x1="165" y1="165" x2="165" y2="322"/>
        <line x1="165" y1="165" x2="8" y2="165"/>
        <line x1="165" y1="165" x2="276" y2="54"/>
        <line x1="165" y1="165" x2="54" y2="276"/>
        <line x1="165" y1="165" x2="276" y2="276"/>
        <line x1="165" y1="165" x2="54" y2="54"/>
        <line x1="165" y1="165" x2="240" y2="25"/>
        <line x1="165" y1="165" x2="90" y2="305"/>
        <line x1="165" y1="165" x2="305" y2="240"/>
        <line x1="165" y1="165" x2="25" y2="90"/>
      </g>
    </svg>
    <div class="ai-ring ai-r3"></div>
    <div class="ai-ring ai-r2"></div>
    <svg class="ai-mesh" viewBox="0 0 290 290">
      <circle cx="145" cy="145" r="142"/>
      <ellipse cx="145" cy="145" rx="142" ry="48"/>
      <ellipse cx="145" cy="145" rx="142" ry="94"/>
      <ellipse cx="145" cy="145" rx="142" ry="130"/>
      <ellipse cx="145" cy="145" rx="48" ry="142"/>
      <ellipse cx="145" cy="145" rx="94" ry="142"/>
      <ellipse cx="145" cy="145" rx="130" ry="142"/>
    </svg>
    <div class="ai-eq"></div>
    <div class="ai-eq2"></div>
    <div class="ai-ring ai-r1"></div>
    <div class="ai-dots"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>
    <div class="ai-nucleus"></div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown(
        f'<div style="text-align:center;">'
        f'<p style="color:{GREEN}; font-size:24px; letter-spacing:4px; '
        f'text-shadow:0 0 12px rgba(0,255,136,.6); margin-bottom:2px;">CORE</p>'
        f'<p style="color:{SUBTLE}; font-size:14px;">주식 분석 AI 비서</p></div>',
        unsafe_allow_html=True,
    )
    st.write("")

    # ----- 음성 입력 (마이크) -----
    voice_text = None
    if MIC_AVAILABLE:
        mc1, mc2 = st.columns([1, 3])
        with mc1:
            voice_text = speech_to_text(language="ko", start_prompt="🎤 말하기",
                                        stop_prompt="⏹️ 멈춤", just_once=True,
                                        use_container_width=True, key="ai_stt")
        with mc2:
            st.caption("마이크 누르고 말해봐 — 예: \"삼성전자 지금 들어가도 돼?\" "
                       "(크롬에서 제일 잘 돼. 종목명은 코드로 바꿔서 넣어줘)")
    else:
        st.caption("🎤 음성 입력은 지금 사용할 수 없어 (서버에 음성 도구 미설치). 글자로 물어봐도 똑같이 작동해.")

    # ----- 비서 입력 영역 -----
    ac1, ac2 = st.columns([1, 2])
    with ac1:
        ai_ticker = st.text_input("종목 코드", value=st.session_state.get("ai_ticker", ""),
                                  placeholder="예: 005930.KS, TSLA",
                                  key="ai_ticker_input")
    with ac2:
        ai_q = st.text_input("질문", value=voice_text if voice_text else "",
                             placeholder="예: 이거 지금 들어가도 돼? / 위험해? / 얼마나 강해?",
                             key="ai_question_input")

    # 빠른 질문 버튼
    st.caption("빠른 질문:")
    qc1, qc2, qc3, qc4 = st.columns(4)
    quick = None
    if qc1.button("지금 어때?", use_container_width=True): quick = "지금 전반적으로 어때?"
    if qc2.button("들어가도 돼?", use_container_width=True): quick = "지금 들어가도 돼?"
    if qc3.button("위험해?", use_container_width=True): quick = "이거 지금 위험해?"
    if qc4.button("얼마나 강해?", use_container_width=True): quick = "시장보다 얼마나 강해?"

    ask_now = st.button("🤖 비서에게 묻기", type="primary", use_container_width=True)

    # 음성으로 종목명을 말했을 때 코드로 바꿔주는 간단 사전 (주요 종목)
    NAME_TO_CODE = {
        "삼성전자": "005930.KS", "에스케이하이닉스": "000660.KS", "sk하이닉스": "000660.KS",
        "하이닉스": "000660.KS", "엘지전자": "066570.KS", "lg전자": "066570.KS",
        "네이버": "035420.KS", "카카오": "035720.KS", "현대차": "005380.KS",
        "기아": "000270.KS", "포스코": "005490.KS", "셀트리온": "068270.KS",
        "테슬라": "TSLA", "엔비디아": "NVDA", "애플": "AAPL", "구글": "GOOGL",
        "마이크로소프트": "MSFT", "아마존": "AMZN", "스페이스엑스": "SPCX", "스페이스x": "SPCX",
    }

    # 음성 텍스트에서 종목명 추출 → 코드 자동 입력
    if voice_text:
        vlow = voice_text.replace(" ", "").lower()
        for name, code in NAME_TO_CODE.items():
            if name in vlow:
                st.session_state.ai_ticker = code
                ai_ticker = code
                break

    # 질문 처리
    question = quick if quick else (ai_q if (ask_now or voice_text) else None)
    trigger = quick or ask_now or bool(voice_text)
    if trigger and ai_ticker.strip():
        st.session_state.ai_ticker = ai_ticker.strip()
        with st.spinner("코어가 분석 중..."):
            info = assistant_collect(ai_ticker.strip())
        if info is None:
            st.error(f"'{ai_ticker.strip()}' 데이터를 지금 못 가져왔어. "
                     "종목 코드가 맞다면(특히 유명한 미국 종목이면) 데이터 서버가 일시적으로 막힌 거라, "
                     "**10~20초 뒤에 다시 눌러봐** — 보통 그러면 돼. "
                     "코드 자체가 의심되면 한국 주식은 숫자+.KS/.KQ, 미국은 영문 티커야.")
        else:
            answer = assistant_answer(info, question or "지금 어때?")
            # 비서 답변 (말풍선 느낌)
            st.markdown(f"""
<div style="background:rgba(0,255,136,0.06); border:1px solid {BORDER};
     border-left:3px solid {GREEN}; border-radius:10px; padding:16px 18px; margin:10px 0;">
  <div style="color:{GREEN}; font-size:13px; letter-spacing:2px; margin-bottom:8px;">◆ CORE</div>
  <div style="color:{TEXT}; font-size:15px; line-height:1.7; white-space:pre-line;">{answer}</div>
</div>
""", unsafe_allow_html=True)

            # 미니 차트 (collect가 받아온 데이터 재활용 — 중복 다운로드 방지)
            mc = info.get("_close")
            if mc is not None and len(mc) > 1:
                mini = go.Figure()
                mini.add_trace(go.Scatter(x=mc.index, y=mc, name="종가",
                                          line=dict(color=GREEN, width=1.8)))
                if len(mc) >= 20:
                    mini.add_trace(go.Scatter(x=mc.index, y=mc.rolling(20).mean(),
                                              name="20일선", line=dict(color="#FFB030", width=1, dash="dot")))
                mini.update_layout(height=240, paper_bgcolor=BG, plot_bgcolor=BG,
                                   font=dict(color=TEXT, size=11), showlegend=True,
                                   margin=dict(l=10, r=10, t=24, b=10),
                                   title=dict(text=f"{info['ticker']} · 최근 6개월", font=dict(size=13)))
                mini.update_xaxes(gridcolor=PANEL); mini.update_yaxes(gridcolor=PANEL)
                st.plotly_chart(mini, use_container_width=True, config={"displaylogo": False})

            # 핵심 지표 카드
            mcols = st.columns(4)
            mcols[0].markdown(f"""<div class="stat-card"><div class="stat-label">현재가</div>
<div class="stat-value">{info['cur']:,.0f}</div></div>""", unsafe_allow_html=True)
            oh_txt = f"{info['overheat']}" if info['overheat'] is not None else "-"
            mcols[1].markdown(f"""<div class="stat-card"><div class="stat-label">과열 점수</div>
<div class="stat-value">{oh_txt}</div></div>""", unsafe_allow_html=True)
            rs_txt = f"{info['rel_strength']:+.1f}%p" if info['rel_strength'] is not None else "-"
            mcols[2].markdown(f"""<div class="stat-card"><div class="stat-label">상대강도</div>
<div class="stat-value">{rs_txt}</div></div>""", unsafe_allow_html=True)
            rsi_txt = f"{info['rsi']:.0f}" if info['rsi'] is not None else "-"
            mcols[3].markdown(f"""<div class="stat-card"><div class="stat-label">RSI(6)</div>
<div class="stat-value">{rsi_txt}</div></div>""", unsafe_allow_html=True)
    elif trigger and not ai_ticker.strip():
        st.warning("먼저 종목 코드를 넣어줘. (예: 005930.KS, TSLA) "
                   "음성으로 종목명을 말하면 자동으로 코드를 찾아주는데, 못 찾으면 직접 입력해줘.")
    else:
        st.info("종목 코드를 넣고 질문하거나 빠른 질문 버튼을 눌러봐. "
                "코어가 그 종목의 과열도·상대강도·RSI를 보고 답해줄게.")

    st.caption("⚠️ 이 비서는 종목을 찍어주거나 미래를 예측하지 않아. "
               "네 분석기 데이터를 해석해서 현재 상태를 말로 풀어주는 역할이야. 최종 판단은 네가 하는 거야.")

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
   - 💠 <span style="color:{OB_C}">주황 다이아 = 과매수 진입</span>: RSI(6일)가 70을 넘은 날. 단기 과열 — 식으면서 조정이 올 수도 있다는 뜻.
   - 💠 <span style="color:{OS_C}">하늘 다이아 = 과매도 진입</span>: RSI(6일)가 30 아래로 내려간 날. 과하게 빠졌다는 신호.
4. **RSI 패널**: 차트 맨 아래. 주황 선이 RSI 6일(민감), 회색 선이 RSI 20일(완만). 70 위(과매수)/30 아래(과매도) 구간이 색칠돼 있어.
5. **볼린저밴드**: 캔들 주변의 옅은 회색 띠. 주가가 보통 머무는 범위(20일 평균 ± 표준편차 2배)라서, 띠 위로 뚫고 나가면 과열 쪽, 아래로 뚫리면 과매도 쪽으로 해석되곤 해.
5. **시장 스캐너**: 시가총액 상위 종목들을 훑어서 🔥 거래량 동반 급등, ⭐ 최근 골든크로스,
   📊 거래량 급증 신호가 잡힌 종목만 추려줘 (국내·S&P500·나스닥). 표에서 종목을 클릭하면 분석기로 바로 넘어가.
6. **백테스트**: "골든크로스에 사서 데드크로스에 팔았다면?"을 과거 데이터로 계산한 것.
   전략이 항상 이기는 게 아니라는 걸 직접 확인하는 게 이 도구의 진짜 목적이야.
7. 모든 신호는 **참고용**이야. 수수료·세금·슬리피지도 계산에 없어.
""", unsafe_allow_html=True)

# ============================================================
#  공포·탐욕 온도계 화면
# ============================================================
elif st.session_state.page == "feargreed":
    st.markdown(AMBIENT_BG, unsafe_allow_html=True)

    with st.sidebar:
        st.button("← 홈으로", on_click=go_page, args=("home",), use_container_width=True)
        st.header("공포·탐욕 설정")
        fg_market_label = st.radio("시장", ["🇰🇷 국내 (코스피+코스닥)", "🇺🇸 미국 (S&P 500)", "🇺🇸 미국 (나스닥)"])
        if fg_market_label.startswith("🇰🇷"):
            fg_market = "KR"
        elif "나스닥" in fg_market_label:
            fg_market = "NASDAQ"
        else:
            fg_market = "S&P500"
        fg_n = st.slider("표본 종목 수 (많을수록 정확, 느림)", 30, 200, 80, step=10)
        fg_btn = st.button("🌡️ 온도 측정", type="primary", use_container_width=True)
        st.info("시장 '전체'가 지금 과열(탐욕)인지 얼어붙었는지(공포)를 재는 거야. "
                "개별 종목이 아니라 **숲 전체**를 보는 거지.")

    st.title("🌡️ 공포 · 탐욕 온도계")
    st.caption("시장 전체 분위기를 0(극단적 공포)~100(극단적 탐욕)으로. "
               "고수들은 '남들이 탐욕일 때 조심하고, 공포일 때 기회를 본다'고 하지.")

    if "fg_result" not in st.session_state:
        st.session_state.fg_result = None

    if fg_btn:
        today_key = "fg-v2-" + datetime.today().strftime("%Y-%m-%d-%H")
        try:
            listing = breadth_listing(fg_market, fg_n)
        except Exception as e:
            listing = None
            st.session_state.fg_error = f"{type(e).__name__}: {e}"

        if listing is None or len(listing) == 0:
            st.session_state.fg_result = (None, {}, 0, fg_market_label)
        else:
            codes = list(listing["Code"])
            up = above = nearhigh = total = 0
            prog = st.progress(0, text=f"시장 온도 재는 중... 0 / {len(codes)}")
            for i, code in enumerate(codes):
                res = breadth_one(fg_market, code, today_key)
                if res is not None:
                    total += 1
                    if res[0]: up += 1
                    if res[1]: above += 1
                    if res[2]: nearhigh += 1
                prog.progress((i + 1) / len(codes),
                              text=f"시장 온도 재는 중... {i + 1} / {len(codes)}  (유효 {total}개)")
            prog.empty()

            if total == 0:
                st.session_state.fg_result = (None, {}, 0, fg_market_label)
            else:
                parts = {
                    "상승 종목 비율": round(up / total * 100, 1),
                    "20일선 위 비율": round(above / total * 100, 1),
                    "신고가 근접 비율": round(nearhigh / total * 100, 1),
                }
                score = round(sum(parts.values()) / 3)
                st.session_state.fg_result = (score, parts, total, fg_market_label)

    if st.session_state.fg_result is None:
        st.write("👈 왼쪽에서 시장을 고르고 **온도 측정**을 눌러줘.")
    else:
        score, parts, total, mkt_label = st.session_state.fg_result
        if score is None:
            st.error("데이터를 못 가져와서 측정 실패. 잠시 후 다시 시도해줘.")
            if st.session_state.get("fg_error"):
                with st.expander("자세한 오류 (디버그용)"):
                    st.code(st.session_state.fg_error)
        else:
            label, cls, emoji = fear_greed_label(score)
            # 큰 온도계 게이지 (0~100 막대)
            bar_color = "#F23645" if score >= 55 else ("#3179F5" if score < 45 else "#9598A1")
            st.markdown(f"""
<div style="text-align:center; margin: 10px 0 6px;">
  <div style="font-size:64px; line-height:1;">{emoji}</div>
  <div style="font-size:52px; font-weight:800; color:{bar_color};">{score}</div>
  <div style="font-size:20px; color:{TEXT}; letter-spacing:2px;">{label}</div>
</div>
<div style="max-width:560px; margin:14px auto; height:16px; border-radius:8px;
     background:linear-gradient(90deg,#3179F5 0%,#9598A1 50%,#F23645 100%); position:relative;">
  <div style="position:absolute; left:calc({score}% - 9px); top:-5px; width:4px; height:26px;
       background:#fff; border-radius:2px; box-shadow:0 0 8px rgba(255,255,255,.8);"></div>
</div>
<div style="max-width:560px; margin:0 auto; display:flex; justify-content:space-between;
     font-size:11px; color:{SUBTLE};"><span>공포 0</span><span>중립 50</span><span>탐욕 100</span></div>
""", unsafe_allow_html=True)
            st.write("")
            st.caption(f"{mkt_label} · 표본 {total}개 종목 기준")

            # 재료 분해
            st.markdown("##### 온도를 구성하는 재료")
            cols = st.columns(len(parts))
            for col, (k, vpct) in zip(cols, parts.items()):
                col.markdown(f"""<div class="stat-card"><div class="stat-label">{k}</div>
<div class="stat-value">{vpct:.0f}%</div></div>""", unsafe_allow_html=True)

            st.write("")
            # 해석
            if score >= 75:
                st.warning("🔥 **극단적 탐욕.** 시장이 과열됐어. 대부분 종목이 오르고 신고가가 쏟아지는 상태. "
                           "이럴 때 새로 뛰어드는 게 제일 위험해 — 고점에서 물릴 확률이 높거든. 고수들이 조심하는 구간.")
            elif score >= 55:
                st.info("😎 **탐욕 구간.** 시장 분위기가 좋아. 근데 좋을 때일수록 'FOMO로 막 사는 것'을 경계해야 해.")
            elif score >= 45:
                st.info("😐 **중립.** 시장이 한 방향으로 쏠려있지 않아. 종목별로 옥석이 갈리는 구간.")
            elif score >= 25:
                st.info("😨 **공포 구간.** 시장이 위축돼 있어. 무섭지만, 좋은 종목이 싸지는 구간이기도 해 — 고수들이 기회를 보는 때.")
            else:
                st.success("🥶 **극단적 공포.** 시장이 얼어붙었어. 대부분 떨어지고 다들 패닉인 상태. "
                           "역사적으로 이런 극단적 공포 구간이 '바닥'인 경우가 많았어(항상은 아니야). "
                           "남들이 다 파는 이때가 역설적으로 기회일 수 있어 — 단, 떨어지는 칼을 잡는 위험도 있으니 신중히.")

            st.caption("⚠️ 이건 '지금 사라/팔라'가 아니야. 시장 전체 온도를 보여주는 것뿐이고, "
                       "극단적 공포가 더 깊어질 수도, 극단적 탐욕이 더 오를 수도 있어. "
                       "개별 종목 판단은 분석기에서 따로 해.")

# ============================================================
#  시장 스캐너 화면
# ============================================================
elif st.session_state.page == "scanner":
    st.markdown(AMBIENT_BG, unsafe_allow_html=True)

    with st.sidebar:
        st.button("← 홈으로", on_click=go_page, args=("home",), use_container_width=True)
        st.header("스캐너 설정")
        market = st.radio("시장", ["🇰🇷 국내 (코스피+코스닥)", "🇺🇸 미국 (S&P 500)", "🇺🇸 미국 (나스닥)"])
        is_us = market.startswith("🇺🇸")
        us_market = "NASDAQ" if "나스닥" in market else "S&P500"
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
        today_key = "sig-v6-" + datetime.today().strftime("%Y-%m-%d-%H")
        # 캐시 갱신용 열쇠: 시간 단위 + 신호 버전.
        # 신호 계산 방식을 바꿀 때 "sig-v2"를 v3, v4로 올리면 옛날 캐시를 안 쓰게 됨.
        scan_error = None
        try:
            with st.spinner("종목 명단 가져오는 중... (나스닥은 명단이 커서 첫 스캔 때 좀 걸려)"):
                listing = load_us(us_market, top_n) if is_us else load_krx_top(top_n)
        except Exception as e:
            listing = None
            scan_error = f"{type(e).__name__}: {e}"

        if listing is None or len(listing) == 0:
            st.error("종목 목록을 못 가져왔어. 잠시 후 다시 시도해줘.")
            if scan_error:
                with st.expander("자세한 오류 내용 (디버그용)"):
                    st.code(scan_error)
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
                df = pd.DataFrame(results).sort_values("_oh", ascending=True)
                df = df.drop(columns=["_oh"])  # 정렬 전용 컬럼 제거
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
    <div class="stat-label">🔥 거래량 급등+상승</div>
    <div class="stat-value">{int(df["신호"].str.contains("급등+상승", regex=False).sum())}개</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">⭐ 최근 골든크로스</div>
    <div class="stat-value">{int(df["신호"].str.contains("골든").sum())}개</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">📊 거래량 급증 (가격 잠잠)</div>
    <div class="stat-value">{int(df["신호"].str.contains("거래량 급증", regex=False).sum())}개</div>
  </div>
</div>
""", unsafe_allow_html=True)
        st.write("")
        # 표에서 행을 클릭하면 그 종목을 분석기에서 바로 연다
        event = st.dataframe(
            df, use_container_width=True, hide_index=True,
            on_select="rerun", selection_mode="single-row", key="scan_table",
        )
        sel = event.selection.rows if event and event.selection else []
        if sel:
            row = df.iloc[sel[0]]
            mkt = str(row["시장"])
            if mkt == "KOSPI":
                tick = f"{row['코드']}.KS"
            elif mkt == "KOSDAQ":
                tick = f"{row['코드']}.KQ"
            else:
                tick = str(row["코드"])
            st.session_state.ticker_input = tick
            st.session_state.query = {"ticker": tick, "period": "1y",
                                      "short": 20, "long": 60}
            st.session_state.page = "app"
            del st.session_state["scan_table"]  # 선택 초기화 (안 하면 돌아왔을 때 또 이동함)
            st.rerun()
        st.caption("종목 행을 클릭하면 분석기에서 바로 차트가 열려. 표 제목을 누르면 정렬돼.")
        with st.expander("표 읽는 법 — 과열도가 뭐야?"):
            st.markdown(
                "- **과열도 낮은 게 위로** 정렬돼 있어. 덜 과열된 = 새로 들어가기 그나마 나은 자리부터. "
                "🟢 안전 → 🟡 주의 → 🟠 과열 → 🔴 매우과열 순이야.\n"
                "- **신호**: 🔥 거래량 급등+상승 / 📊 거래량만 급증 / ⭐ 최근 골든크로스.\n\n"
                "**손절선·익절목표·상대강도·분할 진입 같은 자세한 매매 플랜은** 종목 행을 클릭해서 "
                "분석기로 넘어간 다음 **🎯 매매 플랜 탭**에서 볼 수 있어. 거기서 그 종목 변동성에 맞춘 "
                "손절·익절이랑, 시장을 이기는 종목인지(상대강도)까지 다 나와."
            )

# ============================================================
#  분석기 화면
# ============================================================
else:
    st.markdown(AMBIENT_BG, unsafe_allow_html=True)

    with st.sidebar:
        st.button("← 홈으로", on_click=go_page, args=("home",), use_container_width=True)
        st.header("설정")
        if "ticker_input" not in st.session_state:
            st.session_state.ticker_input = "005930.KS"
        ticker = st.text_input("종목 코드", key="ticker_input")
        st.caption(
            "예시) 삼성전자: 005930.KS · SK하이닉스: 000660.KS · "
            "엔비디아: NVDA · 테슬라: TSLA"
        )
        period = st.selectbox("기간", ["6mo", "1y", "2y", "5y"], index=1,
                              format_func=lambda p: PERIOD_LABEL[p])
        short_win = st.number_input("단기 이동평균 (일)", value=20, min_value=2, max_value=120)
        long_win = st.number_input("장기 이동평균 (일)", value=60, min_value=5, max_value=240)
        run = st.button("분석 시작", type="primary", use_container_width=True)
        live_mode = st.toggle("🔴 실시간 모드 (1분봉)")
        st.info("이 도구는 **과거** 신호를 보여주는 거지 "
                "미래를 예측하거나 매수/매도를 추천하는 게 아니야.")

    st.title("📊 분석기")

    # ---------- 🔴 실시간 모드 ----------
    # 15초마다 화면이 스스로 새로고침되면서 분봉과 현재가가 갱신된다.
    if live_mode:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=15_000, key="live_refresh")

        t = ticker.upper().strip()
        is_kr = t.endswith(".KS") or t.endswith(".KQ") or (t.isdigit() and len(t) == 6)

        mdf = fetch_minute(t)
        now_txt = datetime.now().strftime("%H:%M:%S")

        if mdf is not None and len(mdf) > 1:
            cur = float(mdf["Close"].iloc[-1])
            day_open = float(mdf["Open"].iloc[0]) if "Open" in mdf.columns else float(mdf["Close"].iloc[0])
            chg = (cur / day_open - 1) * 100

            c1, c2, c3 = st.columns(3)
            chg_cls = "stat-up" if chg > 0 else ("stat-down" if chg < 0 else "")
            c1.markdown(f"""<div class="stat-card"><div class="stat-label">현재가</div>
<div class="stat-value">{cur:,.2f}</div></div>""", unsafe_allow_html=True)
            c2.markdown(f"""<div class="stat-card"><div class="stat-label">시가 대비</div>
<div class="stat-value {chg_cls}">{chg:+.2f}%</div></div>""", unsafe_allow_html=True)
            c3.markdown(f"""<div class="stat-card"><div class="stat-label">마지막 갱신</div>
<div class="stat-value">{now_txt}</div></div>""", unsafe_allow_html=True)
            st.write("")

            lfig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                 row_heights=[0.78, 0.22], vertical_spacing=0.04)
            lfig.add_trace(go.Scatter(
                x=mdf.index, y=mdf["Close"], name="1분봉 종가",
                line=dict(color=GREEN, width=1.6),
                fill="tozeroy", fillcolor="rgba(0,255,136,0.05)",
            ), row=1, col=1)
            if "Volume" in mdf.columns:
                lfig.add_trace(go.Bar(
                    x=mdf.index, y=mdf["Volume"], name="거래량",
                    marker_color=GREEN_D, opacity=0.45,
                ), row=2, col=1)
            lfig.update_layout(
                height=560, paper_bgcolor=BG, plot_bgcolor=BG,
                font=dict(color=TEXT, size=12), hovermode="x unified",
                showlegend=False, margin=dict(l=10, r=10, t=20, b=10),
            )
            lfig.update_xaxes(gridcolor=PANEL, zeroline=False)
            lfig.update_yaxes(gridcolor=PANEL, zeroline=False)
            # 가격축이 0부터 시작하지 않게 (fill 때문에 생기는 문제 방지)
            ymin, ymax = float(mdf["Close"].min()), float(mdf["Close"].max())
            pad = (ymax - ymin) * 0.15 if ymax > ymin else ymax * 0.01
            lfig.update_yaxes(range=[ymin - pad, ymax + pad], row=1, col=1)

            st.plotly_chart(lfig, use_container_width=True,
                            config={"scrollZoom": True, "displaylogo": False})
            st.caption(f"🔴 15초마다 자동 갱신 · 무료 시세라 거래소에 따라 몇 분 지연될 수 있어 "
                       f"· 장 마감 시간엔 마지막 거래일 데이터가 보여")
        elif is_kr:
            # 분봉이 막혔으면 네이버 현재가라도 보여준다
            try:
                code6 = t.replace(".KS", "").replace(".KQ", "")
                price, rate = fetch_quote_kr(code6)
                chg_cls = "stat-up" if rate > 0 else ("stat-down" if rate < 0 else "")
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"""<div class="stat-card"><div class="stat-label">현재가 (네이버)</div>
<div class="stat-value">{price:,.0f}</div></div>""", unsafe_allow_html=True)
                c2.markdown(f"""<div class="stat-card"><div class="stat-label">등락률</div>
<div class="stat-value {chg_cls}">{rate:+.2f}%</div></div>""", unsafe_allow_html=True)
                c3.markdown(f"""<div class="stat-card"><div class="stat-label">마지막 갱신</div>
<div class="stat-value">{now_txt}</div></div>""", unsafe_allow_html=True)
                st.caption("분봉 데이터는 지금 못 가져와서 현재가만 갱신 중이야. (15초마다)")
            except Exception as e:
                st.error(f"'{t}' 실시간 데이터를 못 가져왔어.")
                with st.expander("자세한 오류 내용 (디버그용)"):
                    st.code(f"{type(e).__name__}: {e}")
        else:
            st.error(f"'{t}' 분봉 데이터를 못 가져왔어. 잠시 후 다시 시도해줘.")
        st.stop()

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

    # 데이터가 아예 없거나, Close가 없거나, 이동평균 계산할 만큼 충분치 않으면 막는다
    bad = (data is None or len(data) == 0 or "Close" not in getattr(data, "columns", []))
    if not bad:
        close = data["Close"].squeeze()
        if not isinstance(close, pd.Series) or close.dropna().shape[0] < max(q["long"], 5):
            bad = True
    if bad:
        st.warning(
            f"**'{q['ticker']}'** 데이터를 충분히 못 가져왔어. 보통 이런 경우야:\n\n"
            "- 종목 코드가 틀렸거나 존재하지 않는 종목 (예: 아직 상장 안 한 회사)\n"
            "- 상장한 지 얼마 안 돼서 데이터가 장기 이동평균을 계산할 만큼 안 쌓인 경우\n"
            "- 일시적으로 데이터 서버가 막힌 경우 (잠시 후 다시 시도)\n\n"
            "종목 코드를 확인해줘. 한국 주식은 숫자+`.KS`(코스피)/`.KQ`(코스닥), 미국 주식은 영문 티커야."
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

    # ---------- RSI 6일/20일 + 볼린저밴드 ----------
    rsi6 = rsi(close, 6)    # 민감한 단기선 — 과매수/과매도 마커는 이걸 기준으로
    rsi20 = rsi(close, 20)  # 완만한 장기선
    ob_enter = (rsi6 >= 70) & (rsi6.shift(1) < 70)   # 과매수 구간에 들어간 날
    os_enter = (rsi6 <= 30) & (rsi6.shift(1) > 30)   # 과매도 구간에 들어간 날
    ob_days = close.index[ob_enter.fillna(False)]
    os_days = close.index[os_enter.fillna(False)]

    # 볼린저밴드(20일, ±2σ): 주가가 보통 머무는 범위
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_up = bb_mid + 2 * bb_std
    bb_dn = bb_mid - 2 * bb_std

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

    r6_now = float(rsi6.iloc[-1]) if not pd.isna(rsi6.iloc[-1]) else None
    r20_now = float(rsi20.iloc[-1]) if not pd.isna(rsi20.iloc[-1]) else None
    if r6_now is None:
        rsi_label, rsi_class = "-", ""
    else:
        if r6_now >= 70:
            state, rsi_class = "과매수", "stat-up"
        elif r6_now <= 30:
            state, rsi_class = "과매도", "stat-down"
        else:
            state, rsi_class = "중립", ""
        r20_txt = f" · 20일 {r20_now:.0f}" if r20_now is not None else ""
        rsi_label = f"{r6_now:.0f} {state}{r20_txt}"

    def ret_class(x):
        return "stat-up" if x > 0 else ("stat-down" if x < 0 else "")

    # 과열·위험 점수 계산
    oh_score, oh_parts = overheat_score(close)
    oh_text, oh_class = overheat_label(oh_score)

    st.caption(f"데이터 출처: {source}")
    st.markdown(f"""
<div class="stat-row">
  <div class="stat-card">
    <div class="stat-label">현재가</div>
    <div class="stat-value">{last_price:,.0f}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">현재 RSI (6일 기준)</div>
    <div class="stat-value {rsi_class}">{rsi_label}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">기간 수익률 (그냥 들고 있었으면)</div>
    <div class="stat-value {ret_class(buy_hold_return)}">{buy_hold_return:+.1f}%</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">⚠️ 과열·위험 점수</div>
    <div class="stat-value {oh_class}">{oh_text}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # 과열 점수가 높으면 경고 배너 + 점수 분해
    if oh_score is not None:
        if oh_score >= 45:
            st.warning(
                f"**과열 신호 (점수 {oh_score}/100).** 이 종목은 이미 단기적으로 많이 오른 상태야. "
                "지금 **새로 진입하는 건 위험**할 수 있어 — 고점에서 물릴 위험이 크다는 뜻이야. "
                "이건 '팔아라'도 '떨어진다'도 아니고, '지금 들어가는 건 신중해라'는 신호야."
            )
        with st.expander(f"과열 점수는 어떻게 나온 거야? (현재 {oh_score}/100)"):
            for k, v in oh_parts.items():
                st.write(f"- {k}: +{v}")
            st.caption(
                "이 점수는 **예측이 아니라 현재 과열 정도를 요약**한 거야. "
                "점수가 낮다고 '사도 좋다'는 뜻이 절대 아니고, 높다고 반드시 떨어지는 것도 아니야 "
                "(과열인데 더 오르는 경우도 많아). 새로 진입할 때 'FOMO로 꼭대기에 뛰어드는 것'을 "
                "막아주는 용도로만 써."
            )
    st.write("")

    # ---------- 탭: 차트 / 매매 내역 / 읽는 법 ----------
    tab_chart, tab_plan, tab_trades, tab_guide = st.tabs(
        ["🕯️ 차트", "🎯 매매 플랜", "📋 매매 내역", "📖 읽는 법"])

    with tab_chart:
        st.markdown(f"#### {q['ticker']} · {PERIOD_LABEL[q['period']]}")
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

        # 볼린저밴드: 위/아래 경계선 사이를 옅게 칠함
        fig.add_trace(go.Scatter(
            x=bb_up.index, y=bb_up, name="볼린저밴드 (20일, ±2σ)",
            line=dict(color="#9598A1", width=0.8, dash="dot"),
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=bb_dn.index, y=bb_dn, showlegend=False,
            line=dict(color="#9598A1", width=0.8, dash="dot"),
            fill="tonexty", fillcolor="rgba(149,152,161,0.08)",
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

        # RSI 패널: 6일(민감)/20일(완만) 두 줄, 70 위/30 아래 구간 색칠
        fig.add_trace(go.Scatter(
            x=rsi6.index, y=rsi6, name="RSI(6)",
            line=dict(color=RSI_C, width=1.4),
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=rsi20.index, y=rsi20, name="RSI(20)",
            line=dict(color="#B0BEC5", width=1.1),
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
        )
        fig.update_xaxes(gridcolor=PANEL, zeroline=False,
                         rangebreaks=[dict(bounds=["sat", "mon"])])
        fig.update_yaxes(gridcolor=PANEL, zeroline=False)
        fig.update_yaxes(range=[0, 100], row=3, col=1)

        st.plotly_chart(fig, use_container_width=True,
                        config={"scrollZoom": True, "displaylogo": False})
        st.caption("🖱️ 휠: 확대/축소 · 드래그: 이동 · 더블클릭: 원위치")
        st.toast("분석 완료!", icon="✅")

    with tab_plan:
        st.markdown(f"#### 🎯 {q['ticker']} 매매 플랜")
        st.caption("실제로 이 종목을 사고판다면? — **예측이 아니라 미리 정해두는 규칙**이야.")

        cur_price = float(close.iloc[-1])

        # ----- 1. 손절·익절 (ATR 기반) -----
        hi = data["High"] if "High" in data.columns else None
        lo = data["Low"] if "Low" in data.columns else None
        atrp = atr_pct(hi, lo, close)
        if atrp is None:
            stop_pct = 8.0
        else:
            stop_pct = max(4.0, min(20.0, atrp * 2.0))
        target_pct = stop_pct * 1.5
        stop_price = cur_price * (1 - stop_pct / 100)
        target_price = cur_price * (1 + target_pct / 100)

        st.markdown("##### 1️⃣ 손절선 · 익절목표")
        p1, p2, p3 = st.columns(3)
        p1.markdown(f"""<div class="stat-card"><div class="stat-label">현재가</div>
<div class="stat-value">{cur_price:,.2f}</div></div>""", unsafe_allow_html=True)
        p2.markdown(f"""<div class="stat-card"><div class="stat-label">손절선 (-{stop_pct:.0f}%)</div>
<div class="stat-value stat-down">{stop_price:,.2f}</div></div>""", unsafe_allow_html=True)
        p3.markdown(f"""<div class="stat-card"><div class="stat-label">익절목표 (+{target_pct:.0f}%)</div>
<div class="stat-value stat-up">{target_price:,.2f}</div></div>""", unsafe_allow_html=True)
        if atrp is not None:
            st.caption(f"이 종목은 평소 하루 약 **{atrp:.1f}%** 출렁여(ATR). 손절폭은 그 2배로 잡았어 — "
                       "변동성에 맞춘 거라 얌전한 종목보다 넓거나 좁을 수 있어.")
        st.write("")

        # ----- 2. 상대강도 -----
        st.markdown("##### 2️⃣ 상대강도 — 시장을 이기는 종목인가?")
        stock_ret = (cur_price / float(close.iloc[0]) - 1) * 100
        idx_ret, idx_name, idx_tk, idx_close = relative_strength(q["ticker"], q["period"])

        if idx_ret is None:
            st.info(f"{idx_name} 지수 데이터를 지금 못 받아와서 상대강도는 계산 못 했어. "
                    "(데이터 서버 사정 — 잠시 후 다시 시도하면 될 수도 있어)")
        else:
            rs = stock_ret - idx_ret
            r1, r2, r3 = st.columns(3)
            r1.markdown(f"""<div class="stat-card"><div class="stat-label">이 종목 ({PERIOD_LABEL[q['period']]})</div>
<div class="stat-value {ret_class(stock_ret)}">{stock_ret:+.1f}%</div></div>""", unsafe_allow_html=True)
            r2.markdown(f"""<div class="stat-card"><div class="stat-label">{idx_name} 지수</div>
<div class="stat-value {ret_class(idx_ret)}">{idx_ret:+.1f}%</div></div>""", unsafe_allow_html=True)
            rs_cls = "stat-up" if rs > 0 else ("stat-down" if rs < 0 else "")
            r3.markdown(f"""<div class="stat-card"><div class="stat-label">상대강도 (차이)</div>
<div class="stat-value {rs_cls}">{rs:+.1f}%p</div></div>""", unsafe_allow_html=True)

            if rs > 5:
                st.success(f"📈 **시장보다 {rs:.1f}%p 더 강해.** 시장({idx_name})을 이기고 있는 '주도주' 쪽이야. "
                           "고수들이 '오르는 종목 중에서도 시장보다 잘 가는 것만 산다'고 할 때 보는 게 이거야.")
            elif rs < -5:
                st.warning(f"📉 **시장보다 {abs(rs):.1f}%p 약해.** 같은 기간 시장은 더 잘 갔는데 이 종목은 못 따라갔어. "
                           "오르더라도 '약한 상승'이라 주의. 시장이 꺾이면 더 빨리 빠질 수 있어.")
            else:
                st.info(f"시장({idx_name})이랑 비슷하게 움직였어. 특별히 강하지도 약하지도 않은 상태.")
            st.caption("상대강도 = 이 종목 상승률 − 시장지수 상승률. 같은 +10%라도 시장이 +3%일 때와 +15%일 때는 "
                       "의미가 완전히 달라 — 그걸 보정해서 '진짜 강한지'를 보는 거야.")
        st.write("")

        # ----- 3. 분할 진입 -----
        st.markdown("##### 3️⃣ 분할 진입 — 한 방에 사지 마라")
        budget = st.number_input("이 종목에 넣을 총 금액 (원하는 단위로)", value=1000000,
                                 min_value=0, step=100000, key="plan_budget")
        st.caption("한 번에 다 사면 '오늘 가격' 하나에 운명이 걸려. 3번 나눠 사면 평균 단가가 안정돼 "
                   "(너 SPCX 단타 때처럼 타이밍 하나에 거는 걸 막아줘).")
        if budget > 0:
            # 3분할: 현재가 / -손절폭의 1/3 / -손절폭의 2/3 지점에서 매수
            levels = [
                ("1차 (지금)", cur_price, budget * 0.4),
                (f"2차 (-{stop_pct/3:.1f}%)", cur_price * (1 - stop_pct/300), budget * 0.3),
                (f"3차 (-{stop_pct*2/3:.1f}%)", cur_price * (1 - stop_pct*2/300), budget * 0.3),
            ]
            rows = []
            tot_qty = 0
            for name, price, amt in levels:
                qty = amt / price if price > 0 else 0
                tot_qty += qty
                rows.append({
                    "단계": name,
                    "매수가": round(price, 2),
                    "투입금액": f"{amt:,.0f}",
                    "수량(주)": round(qty, 2),
                })
            avg = (budget / tot_qty) if tot_qty > 0 else cur_price
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.caption(f"3단계 다 채우면 평균 단가 약 **{avg:,.2f}** (지금 한 방에 사는 것보다 낮아). "
                       "물론 가격이 안 떨어지고 바로 오르면 1차만 체결되고 끝 — 그것도 정상이야. "
                       "분할은 '더 싸게 사려는 욕심'이 아니라 '타이밍 실수를 줄이려는 보험'이야.")
        st.write("")
        st.caption("⚠️ 이 플랜 전체는 매수 추천이 아니야. 손절·익절·분할은 '사기로 이미 정했다면 이렇게 관리해라'는 "
                   "규칙이고, 애초에 살지 말지는 네가 판단하는 거야. 특히 위 **과열·위험 점수**가 높으면 "
                   "이 플랜을 짜기 전에 '지금 진입 자체가 맞나'부터 다시 생각해봐.")

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
- 💠 <span style="color:{OB_C}">**주황 다이아 (과매수 진입)**</span>: RSI(6일)가 70을 넘은 날. 과열이라 조정이 올 수도 있다는 뜻.
- 💠 <span style="color:{OS_C}">**하늘 다이아 (과매도 진입)**</span>: RSI(6일)가 30 아래로 내려간 날. 과하게 빠졌다는 신호.
- **RSI 패널(맨 아래)**: 주황 선 RSI(6), 회색 선 RSI(20). 주황 구간(70↑) 과매수, 하늘 구간(30↓) 과매도.
- **볼린저밴드**: 캔들 주변 옅은 띠. 주가가 보통 머무는 범위(20일 평균 ±2σ). 띠를 위로 뚫으면 과열 쪽, 아래로 뚫리면 과매도 쪽 해석.
- **전략 수익률 vs 기간 수익률**: 크로스 신호대로 사고팔았을 때와 그냥 들고 있었을 때의 비교.
  전략이 항상 이기는 게 아니라는 걸 직접 확인하는 게 이 도구의 진짜 목적이야.
- 수수료·세금·슬리피지는 계산에 안 들어가 있어서 실제 수익률은 이것보다 낮아져.
- **⚠️ 과열·위험 점수 (0~100)**: RSI 과열 + 고점 근접 + 이동평균 이격 + 단기 급등폭 + 볼린저밴드 위치를 합친 점수.
  높을수록 '이미 많이 올라서 지금 새로 들어가면 위험'하다는 뜻. **이건 미래 예측이 아니라 현재 과열 정도를 요약한 거야.**
  점수가 낮다고 '사도 좋다'는 신호가 절대 아니고, 높아도 더 오를 수 있어. FOMO로 꼭대기에 뛰어드는 걸 막는 용도로만 쓰면 돼.
""", unsafe_allow_html=True)
