"""
signal_scoreboard.py
신호 채점기(Signal Scoreboard) — stock-analyzer 드롭인 모듈

핵심 아이디어:
  "기록"을 며칠씩 기다려 쌓는 대신, 과거 전체에 신호를 돌려서 한 번에 채점한다.
  그리고 모든 신호의 성적을 '아무 날에나 그냥 보유했을 때(baseline)'와 비교한다.
  baseline을 못 이기면 그 신호는 엣지가 없다 -> 화면에서 지운다.
"""

import numpy as np
import pandas as pd


# ----------------------------------------------------------------------
# 1) 지표 계산
# ----------------------------------------------------------------------
def rsi(price: pd.Series, period: int = 14) -> pd.Series:
    delta = price.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def bollinger_pctb(price: pd.Series, window: int = 20, k: float = 2.0) -> pd.Series:
    ma = price.rolling(window).mean()
    sd = price.rolling(window).std()
    upper, lower = ma + k * sd, ma - k * sd
    return (price - lower) / (upper - lower)  # 1 위 = 상단 돌파, 0 아래 = 하단 이탈


# ----------------------------------------------------------------------
# 2) 신호 정의 (event = '상태'가 아니라 '전환되는 그 날'만 잡는다)
#    상태(RSI>70 매일)를 다 세면 연속된 날들이 겹쳐서 표본이 뻥튀기된다.
#    그래서 '막 넘어선 날'만 신호로 친다 -> 표본이 정직해진다.
# ----------------------------------------------------------------------
def _cross_up(state: pd.Series) -> pd.Series:
    state = state.fillna(False)
    return state & (~state.shift(1).fillna(False))


def signal_golden_cross(df, short=20, long=60):
    p = df["Close"]
    return _cross_up(p.rolling(short).mean() > p.rolling(long).mean())


def signal_rsi_overbought(df, period=14, thr=70):
    return _cross_up(rsi(df["Close"], period) > thr)


def signal_rsi_oversold(df, period=14, thr=30):
    return _cross_up(rsi(df["Close"], period) < thr)


def signal_bb_breakout(df, window=20, k=2.0):
    return _cross_up(bollinger_pctb(df["Close"], window, k) > 1.0)


# ----------------------------------------------------------------------
# 3) 채점기 — 신호 vs baseline
# ----------------------------------------------------------------------
def evaluate_signal(df: pd.DataFrame, signal_mask: pd.Series,
                    horizon: int = 5, price_col: str = "Close") -> dict:
    price = df[price_col].astype(float)
    fwd = price.shift(-horizon) / price - 1.0      # horizon일 뒤 수익률
    valid = fwd.notna()

    sig = signal_mask.reindex(df.index).fillna(False) & valid
    n_sig = int(sig.sum())

    if n_sig == 0:
        return {"n_signals": 0, "note": "신호 발생 0회 — 평가 불가"}

    sig_ret = fwd[sig]
    base_ret = fwd[valid]

    edge = float(sig_ret.mean() - base_ret.mean())

    # 표본이 적으면 우연일 수 있다 -> 정직하게 경고
    if n_sig < 10:
        reliability = "표본 매우 적음(우연일 가능성 큼)"
    elif n_sig < 30:
        reliability = "표본 적음(참고만)"
    else:
        reliability = "표본 어느 정도 확보"

    return {
        "horizon": horizon,
        "n_signals": n_sig,
        "signal_win_rate": round(float((sig_ret > 0).mean()), 3),
        "baseline_win_rate": round(float((base_ret > 0).mean()), 3),
        "signal_avg_return": round(float(sig_ret.mean()), 4),
        "baseline_avg_return": round(float(base_ret.mean()), 4),
        "edge_vs_baseline": round(edge, 4),
        "verdict": "엣지 있음" if edge > 0 else "엣지 없음(장식)",
        "reliability": reliability,
    }


SIGNALS = {
    "골든크로스(20/60)": signal_golden_cross,
    "RSI 과매수 진입(>70)": signal_rsi_overbought,
    "RSI 과매도 진입(<30)": signal_rsi_oversold,
    "볼린저 상단 돌파": signal_bb_breakout,
}


def scoreboard(df: pd.DataFrame, horizon: int = 5) -> pd.DataFrame:
    rows = []
    for name, fn in SIGNALS.items():
        r = evaluate_signal(df, fn(df), horizon=horizon)
        r["signal"] = name
        rows.append(r)
    cols = ["signal", "n_signals", "signal_avg_return",
            "baseline_avg_return", "edge_vs_baseline", "verdict", "reliability"]
    return pd.DataFrame(rows).reindex(columns=cols)
