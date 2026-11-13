"""
S6  Antifragile Asset Allocation (Giordano 2019), PROTOCOL section 2.

Each month-end, every asset in a group gets four factors:
  M  4-month momentum (84 trading days rate of change)
  V  GARCH(1,1) volatility forecast, fitted on the last 504 daily returns
  C  average correlation with the other assets of its group, last 84 trading days
  T  trend state: -1 uptrend, +1 downtrend, 0 before the first signal
     (uptrend after a close above the previous day's upper band = 63-day highest close
      + 42-day ATR; downtrend after a close below the previous day's lower band =
      105-day highest low - 42-day ATR; the state persists in between)
TRank = wM*Rank(M) + wV*Rank(V) + wC*Rank(C) - wT*T + M/n, higher is better:
  high momentum, low volatility and low correlation get the high ranks.

Allocation: top 5 sectors at 20% each if M > 0; unused weight goes to the top 3 hedges
(equal weight among those with M > 0, otherwise SHY).
An asset enters the ranking once it has 504 days of history.
"""
import itertools
import warnings

import numpy as np
import pandas as pd

import config as C
import data as D

SECTORS = "XLY XLV XLU XLP XLK XLI XLF XLE XLB VOX RWR".split()
HEDGES = "FXY FXF GLD IEF SH TLT SHY".split()
LEVERED = "UPRO TQQQ EDC".split()
CASH = "SHY"
PAPER_W = np.array([0.50, 0.25, 0.25, 0.25]) / 1.25      # M, V, C, T rescaled to sum 1


def _trend_state(ohlc, ticker):
    h, l, c = ohlc["High"][ticker], ohlc["Low"][ticker], ohlc["Close"][ticker]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 42, min_periods=42, adjust=False).mean()
    upper = (c.rolling(63).max() + atr).shift(1)
    lower = (l.rolling(105).max() - atr).shift(1)
    state = np.zeros(len(c))
    s = 0.0
    cv, uv, lv = c.values, upper.values, lower.values
    for i in range(len(c)):
        if not np.isnan(uv[i]) and cv[i] > uv[i]:
            s = -1.0
        elif not np.isnan(lv[i]) and cv[i] < lv[i]:
            s = 1.0
        state[i] = s
    return pd.Series(state, index=c.index)


def _garch_vol(r):
    from arch import arch_model
    x = r.dropna().values[-504:] * 100
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = arch_model(x, vol="Garch", p=1, q=1, rescale=False).fit(disp="off")
        f = res.forecast(horizon=1).variance.values[-1, 0]
        return float(np.sqrt(f) / 100 * np.sqrt(252))
    except Exception:
        return float(np.std(x) / 100 * np.sqrt(252))


def factors(tickers, end="2026-09-30"):
    """Month-end factor panel {M, V, C, T} for one group, cached to disk."""
    path = C.CACHE / f"af_factors_{'_'.join(tickers)}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    ohlc = D.etf_prices()
    close = ohlc["Close"][tickers]
    close = close[close.index <= end]
    rets = close.pct_change(fill_method=None)
    trend = pd.DataFrame({t: _trend_state(ohlc, t) for t in tickers}).reindex(close.index)
    me = close.index.to_series().groupby(close.index.to_period("M")).max()
    rows = []
    for d in me.values:
        d = pd.Timestamp(d)
        hist = rets.loc[:d]
        ok = [t for t in tickers if hist[t].notna().sum() >= 504]
        if len(ok) < 2:
            continue
        win = hist[ok].iloc[-84:]
        corr = win.corr()
        for t in ok:
            c = close[t].loc[:d].dropna()
            rows.append({"date": d, "ticker": t,
                         "M": c.iloc[-1] / c.iloc[-85] - 1,
                         "V": _garch_vol(hist[t]),
                         "C": corr.loc[t, [x for x in ok if x != t]].mean(),
                         "T": trend.at[d, t]})
    out = pd.DataFrame(rows)
    out.to_parquet(path)
    return out


def trank(f, w):
    """TRank per (date, ticker); higher is better."""
    g = f.groupby("date")
    n = g["ticker"].transform("count")
    rM = g["M"].rank(ascending=True)
    rV = g["V"].rank(ascending=False)
    rC = g["C"].rank(ascending=False)
    return w[0] * rM + w[1] * rV + w[2] * rC - w[3] * f["T"] + f["M"] / n


def targets(fs, fh, w, sectors_n=5, hedges_n=3):
    """Month-end target weights for the combined Antifragile portfolio."""
    fs = fs.assign(score=trank(fs, w))
    fh = fh.assign(score=trank(fh, w))
    rows = {}
    for d, gs in fs.groupby("date"):
        top = gs.nlargest(sectors_n, "score")
        wts = {t: 1 / sectors_n for t, m in zip(top.ticker, top.M) if m > 0}
        rest = 1 - sum(wts.values())
        if rest > 1e-9:
            gh = fh[fh.date == d].nlargest(hedges_n, "score")
            if len(gh):
                for t, m in zip(gh.ticker, gh.M):
                    key = t if m > 0 else CASH
                    wts[key] = wts.get(key, 0) + rest / hedges_n * (hedges_n / len(gh))
            else:
                wts[CASH] = wts.get(CASH, 0) + rest
        rows[d] = wts
    return pd.DataFrame(rows).T.fillna(0.0).sort_index()


def weight_grid(step=0.05):
    k = int(round(1 / step))
    for a, b, c in itertools.product(range(k + 1), repeat=3):
        d = k - a - b - c
        if d >= 0:
            yield np.array([a, b, c, d]) / k
