# ============================================================
#  주식 분석기 v5 — 트레이딩 데스크 에디션
#  v4에서 바뀐 점:
#   - 첫 화면(홈 메뉴) 추가: 들어가면 분석기/사용법 선택 화면이 먼저 뜸
#   - 캔들 색 한국식으로: 상승 빨강 / 하락 파랑
#   - 신호 마커: 골든크로스 = 금색 별, 데드크로스 = 보라 삼각형
#   - 차트 조작: 마우스 휠로 확대/축소, 드래그로 이동, 더블클릭 원위치
#   - 숫자 카드를 직접 디자인한 카드로 교체 (+ 등장 애니메이션, 호버 효과)
#   - 결과 화면을 탭(차트/매매 내역/읽는 법)으로 정리
#  데이터 3단 예비 체계(야후 → 네이버/KRX → Stooq)는 그대로.
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
BG      = "#131722"   # 배경
PANEL   = "#1E222D"   # 카드/그리드
BORDER  = "#2A2E39"
TEXT    = "#D1D4DC"
SUBTLE  = "#787B86"
UP      = "#F23645"   # 상승 (한국식 빨강)
DOWN    = "#3179F5"   # 하락 (한국식 파랑)
GOLD    = "#FFC107"   # 골든크로스 (금색)
PURPLE  = "#A855F7"   # 데드크로스 (보라)
MA_S_C  = "#26A69A"   # 단기 이동평균 (청록)
MA_L_C  = "#E0E3EB"   # 장기 이동평균 (밝은 회색)

st.set_page_config(page_title="주식 분석기", page_icon="📈", layout="wide")

# ---------- 전체 스타일 + 애니메이션 ----------
st.markdown(f"""
<style>
/* 등장 애니메이션 */
@keyframes fadeUp {{
    from {{ opacity: 0; transform: translateY(16px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes gradientMove {{
    0%   {{ background-position: 0% 50%; }}
    50%  {{ background-position: 100% 50%; }}
    100% {{ background-position: 0% 50%; }}
}}

/* 홈 화면 큰 제목: 금색→빨강→파랑으로 흐르는 글자 */
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

/* 통계 카드 */
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

/* 버튼 살짝 떠오르는 효과 */
.stButton > button {{
    transition: transform .15s ease, box-shadow .15s ease;
    border-radius: 10px;
}}
.stButton > button:hover {{
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(0,0,0,0.35);
}}

/* 차트/탭 부드럽게 등장 */
[data-testid="stPlotlyChart"], .stTabs {{ animation: fadeUp 0.6s ease; }}

h1 {{ letter-spacing: -0.5px; }}
</style>
""", unsafe_allow_html=True)

PERIOD_DAYS = {"6mo": 182, "1y": 365, "2y": 730, "5y": 1825}
PERIOD_LABEL = {"6mo": "6개월", "1y": "1년", "2y": "2년", "5y": "5년"}


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


# ---------- 페이지 이동 관리 ----------
# session_state: 새로고침 전까지 기억되는 "사이트의 수첩".
# 어느 화면을 보고 있는지(page), 마지막 분석 조건이 뭔지(query)를 적어둔다.
if "page" not in st.session_state:
    st.session_state.page = "home"
if "query" not in st.session_state:
    st.session_state.query = None


def go(page_name: str):
    st.session_state.page = page_name


# ============================================================
#  홈 화면
# ============================================================
if st.session_state.page == "home":
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
        '<span class="chip">🧪 전략 백테스트</span>'
        '<span class="chip">🇰🇷 한국 + 🇺🇸 미국 주식</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.write("")

    c1, c2, _ = st.columns([1, 1, 2])
    with c1:
        st.button("📊 분석기 열기", type="primary", use_container_width=True,
                  on_click=go, args=("app",))
    with c2:
        st.button("📖 사용법 보기", use_container_width=True,
                  on_click=go, args=("guide",))

    st.write("")
    st.caption("⚠️ 이 도구는 과거 신호를 보여주는 거지 미래를 예측하거나 매수/매도를 추천하는 게 아니야.")

# ============================================================
#  사용법 화면
# ============================================================
elif st.session_state.page == "guide":
    st.button("← 홈으로", on_click=go, args=("home",))
    st.title("📖 사용법")
    st.markdown(f"""
1. **분석기 열기**에서 종목 코드와 기간을 고르고 **분석 시작**을 눌러.
   - 한국 주식은 숫자 코드 + `.KS`(코스피)/`.KQ`(코스닥) — 예: 삼성전자 `005930.KS`
   - 미국 주식은 영문 티커 — 예: 엔비디아 `NVDA`, 테슬라 `TSLA`
2. **차트 조작**: 마우스 휠로 확대/축소, 드래그로 좌우 이동, 더블클릭하면 원위치.
3. **신호 읽는 법**
   - ⭐ <span style="color:{GOLD}">금색 별 = 골든크로스</span>: 단기 평균이 장기 평균을 위로 뚫은 날. 흔히 상승 신호로 불림.
   - 🔻 <span style="color:{PURPLE}">보라 삼각형 = 데드크로스</span>: 반대로 아래로 뚫은 날.
4. **백테스트**: "골든크로스에 사서 데드크로스에 팔았다면?"을 과거 데이터로 계산한 것.
   그냥 들고 있었을 때(기간 수익률)와 비교해봐 — 전략이 항상 이기는 게 아니라는 걸
   직접 확인하는 게 이 도구의 진짜 목적이야.
5. 수수료·세금·슬리피지는 계산에 없어서 실제 수익률은 표시보다 낮아져.
""", unsafe_allow_html=True)

# ============================================================
#  분석기 화면
# ============================================================
else:
    with st.sidebar:
        st.button("← 홈으로", on_click=go, args=("home",), use_container_width=True)
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

    # "분석 시작"을 누르면 조건을 수첩(session_state)에 적어둔다.
    # 이렇게 하면 탭을 누르거나 화면이 갱신돼도 결과가 사라지지 않는다.
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

    def ret_class(x):  # 수익률 색: 플러스 빨강(상승색) / 마이너스 파랑
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
    <div class="stat-label">거래 횟수</div>
    <div class="stat-value">{len(trades)}회</div>
  </div>
</div>
""", unsafe_allow_html=True)
    st.write("")

    # ---------- 탭: 차트 / 매매 내역 / 읽는 법 ----------
    tab_chart, tab_trades, tab_guide = st.tabs(["🕯️ 차트", "📋 매매 내역", "📖 읽는 법"])

    with tab_chart:
        has_ohlc = all(c in data.columns for c in ["Open", "High", "Low"])
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

        if has_volume:
            open_ref = data["Open"] if has_ohlc else data["Close"]
            vol_colors = [UP if c >= o else DOWN
                          for c, o in zip(data["Close"], open_ref)]
            fig.add_trace(go.Bar(
                x=data.index, y=data["Volume"], name="거래량",
                marker_color=vol_colors, opacity=0.55,
            ), row=2, col=1)

        fig.update_layout(
            height=620,
            paper_bgcolor=BG, plot_bgcolor=BG,
            font=dict(color=TEXT, size=12),
            hovermode="x unified",
            dragmode="pan",                      # 드래그 = 이동
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0),
            margin=dict(l=10, r=10, t=30, b=10),
            title=dict(text=f"{q['ticker']}  ·  {PERIOD_LABEL[q['period']]}",
                       x=0.5, font=dict(size=15)),
        )
        fig.update_xaxes(gridcolor=PANEL, zeroline=False,
                         rangebreaks=[dict(bounds=["sat", "mon"])])
        fig.update_yaxes(gridcolor=PANEL, zeroline=False)

        # scrollZoom: 마우스 휠 확대/축소 켜기
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
- ⭐ <span style="color:{GOLD}">**금색 별 (골든크로스)**</span>: 단기({s_win}일) 평균이 장기({l_win}일) 평균을 **위로** 뚫은 날. 흔히 상승 신호로 불림.
- 🔻 <span style="color:{PURPLE}">**보라 삼각형 (데드크로스)**</span>: 반대로 **아래로** 뚫은 날.
- **전략 수익률 vs 기간 수익률**: 크로스 신호대로 사고팔았을 때와 그냥 처음부터 들고 있었을 때의 비교.
  전략이 항상 이기는 게 아니라는 걸 직접 확인하는 게 이 도구의 진짜 목적이야.
- 수수료·세금·슬리피지는 계산에 안 들어가 있어서 실제 수익률은 이것보다 낮아져.
""", unsafe_allow_html=True)
