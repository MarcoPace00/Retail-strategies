"""
Strategy rules, as published (PROTOCOL section 2).

Every signal is a target computed from data up to the close of day t. `lag` is the number
of rows between that close and the first return the position earns:
  lag=1  same-day close (the papers' convention: trade at the close the signal is read)
  lag=2  next-day close (the protocol's main case for a retail investor)
"""
import numpy as np
import pandas as pd

import engine as E


# --------------------------------------------------------------------------- #
# S1  Faber: month-end price above its 10-month simple moving average
# --------------------------------------------------------------------------- #
def month_end_flags(index):
    s = pd.Series(index, index=index)
    return s.groupby(index.to_period("M")).transform("max") == s


def s1_faber(asset, rf, months=10, lag=1, cost=0.0005, cash_fee=0.0):
    """Hold the asset next month if its month-end total-return level > 10-month average."""
    level = E.wealth(asset)
    me = level[month_end_flags(level.index)]
    sma = me.rolling(months, min_periods=months).mean()
    sig = (me > sma).astype(float).where(sma.notna())
    pos = sig.reindex(level.index).ffill().shift(lag)
    cash = rf.reindex(asset.index) - cash_fee * E.calendar_days(asset.index) / 365.25
    r = pos * asset + (1 - pos) * cash
    return (r - pos.diff().abs().fillna(0) * cost).dropna()


# --------------------------------------------------------------------------- #
# S2  Dual momentum (Antonacci), monthly data
# --------------------------------------------------------------------------- #
def s2_dual_momentum(us, intl, rf, safe, look=12, cost=0.0005):
    """Month-end: pick the higher 12-month total return of US vs non-US stocks; if the
    winner's 12-month return is below T-bills', hold `safe` (bonds, or T-bills) instead.

    Inputs are monthly returns on a common month-end index; the choice made at the end of
    month t earns month t+1's return (the paper's same-close convention)."""
    df = pd.concat({"us": us, "intl": intl, "rf": rf, "safe": safe}, axis=1).dropna()
    trail = (1 + df).rolling(look).apply(np.prod, raw=True) - 1
    pick = np.where(trail.us >= trail.intl, "us", "intl")
    best = np.where(pick == "us", trail.us, trail.intl)
    choice = pd.Series(np.where(best > trail.rf, pick, "safe"), index=df.index)
    choice[trail.us.isna()] = None
    held = choice.shift(1)
    r = pd.Series([df.at[t, h] if isinstance(h, str) else np.nan
                   for t, h in zip(df.index, held)], index=df.index)
    switches = (held != held.shift(1)) & held.notna() & held.shift(1).notna()
    return (r - switches.astype(float) * 2 * cost).dropna(), held


def relative_momentum(us, intl, look=12):
    """Relative momentum only: always in the stronger of the two equity markets."""
    df = pd.concat({"us": us, "intl": intl}, axis=1).dropna()
    trail = (1 + df).rolling(look).apply(np.prod, raw=True) - 1
    held = pd.Series(np.where(trail.us >= trail.intl, "us", "intl"),
                     index=df.index).where(trail.us.notna()).shift(1)
    return pd.Series([df.at[t, h] if isinstance(h, str) else np.nan
                      for t, h in zip(df.index, held)], index=df.index).dropna()


# --------------------------------------------------------------------------- #
# S4  Leverage for the Long Run: 200-day moving average, L-times exposure
# --------------------------------------------------------------------------- #
def s4_trend(mkt, rf, L=1, n=200, lag=1, cost=0.0005, spread=0.01, fee=0.01,
             cash_fee=0.0):
    """Risk-on when the total-return level is strictly above its n-day simple average."""
    level = E.wealth(mkt)
    on = (level > level.rolling(n, min_periods=n).mean()).astype(float)
    on[level.rolling(n, min_periods=n).mean().isna()] = np.nan
    pos = on.shift(lag)
    lev = E.leveraged(mkt, rf, L, spread, fee if L > 1 else 0.0)
    cash = rf - cash_fee * E.calendar_days(rf.index) / 365.25
    r = pos * lev + (1 - pos) * cash
    traded = pos.diff().abs() * L
    return (r - traded.fillna(0) * cost).dropna()


def constant(mkt, rf, L=1, spread=0.01, fee=0.01):
    return E.leveraged(mkt, rf, L, spread, fee if L > 1 else 0.0)


# --------------------------------------------------------------------------- #
# S3  Beta rotation: utilities vs market, 4-week relative total return, weekly
# --------------------------------------------------------------------------- #
def s3_beta_rotation(util, mkt, weeks=4, lag=1, cost=0.0):
    """Hold utilities next week if (U/M) rose over the last `weeks` completed weeks."""
    U, M = E.wealth(util), E.wealth(mkt)
    ratio = U / M
    week = ratio.index.to_period("W-FRI")
    last_day = ratio.groupby(week).tail(1)                 # last session of each week
    score = last_day / last_day.shift(weeks) - 1
    sig = (score > 0).astype(float).where(score.notna())
    daily_sig = sig.reindex(ratio.index).ffill()           # decided at week's last close
    pos = daily_sig.shift(lag)
    r = pos * util + (1 - pos) * mkt
    traded = pos.diff().abs() * 2                          # sell one leg, buy the other
    return (r - traded.fillna(0) * cost).dropna()


# --------------------------------------------------------------------------- #
# S5  Industry trend following (Zarattini & Antonacci)
# --------------------------------------------------------------------------- #
def _keltner(P, n, k, sign):
    ema = P.ewm(span=n, adjust=False, min_periods=n).mean()
    band = 1.4 * k * P.diff().abs().rolling(n, min_periods=n).mean()
    return ema + sign * band


def s5_industry_trend(ind, rf, cap=2.0, target=0.015, vol_n=14, lag=1, cost=0.0,
                      spread=0.0, cash_fee=0.0, lev_fee=0.0, weights_out=None):
    """Long-only timing of each industry; equal volatility budget; exposure cap `cap`.

    Borrowing above 100% exposure costs the T-bill rate plus `spread` (paper: spread 0);
    `lev_fee` is the annual leveraged-product fee, charged in proportion to the extra
    exposure up to one unit (so a full 2x or 3x product pays the whole fee, as in S4)."""
    P = E.wealth(ind).where(ind.notna())                   # total-return level, NaN = missing
    upper = np.minimum(P.rolling(20, min_periods=20).max(), _keltner(P, 20, 2, +1))
    lower = np.maximum(P.rolling(40, min_periods=40).min(), _keltner(P, 40, 2, -1))
    sigma = ind.rolling(vol_n, min_periods=vol_n).std()
    sigma = sigma.where(sigma > 0)                         # a flat stretch gives no size

    Pv, Uv, Lv = P.values, upper.values, lower.values
    T, N = Pv.shape
    held = np.zeros((T, N), bool)
    stop = np.full(N, np.nan)
    inpos = np.zeros(N, bool)
    for t in range(1, T):
        p, up_prev, lo = Pv[t], Uv[t - 1], Lv[t]
        # exits: close below the trailing stop carried from the previous day
        ex = inpos & (p < stop)
        inpos[ex] = False
        stop[ex] = np.nan
        # entries: close at or above the previous day's upper band
        en = (~inpos) & (p >= up_prev)
        inpos[en] = True
        stop[en] = lo[en]
        # stop never moves down
        upd = inpos & ~en
        stop[upd] = np.fmax(stop[upd], lo[upd])
        inpos[np.isnan(p)] = False
        held[t] = inpos

    avail = P.notna().sum(1).values
    w = np.where(held, (target / np.maximum(avail, 1)[:, None]) / sigma.values, 0.0)
    w = np.nan_to_num(w)
    expo = w.sum(1)
    scale = np.where(expo > cap, cap / np.maximum(expo, 1e-12), 1.0)
    w = pd.DataFrame(w * scale[:, None], index=ind.index, columns=ind.columns)
    if weights_out is not None:                            # target weights, before the lag
        weights_out.append(w)
    pos = w.shift(lag).fillna(0.0)
    gross = pos.sum(1)
    days = E.calendar_days(rf.index)
    cash_r = rf - cash_fee * days / 365.25
    extra = (gross - 1).clip(lower=0)
    borrow = extra * spread * days / 365.25 + extra.clip(upper=1) * lev_fee * days / 365.25
    r = (pos * ind.fillna(0.0)).sum(1) + (1 - gross) * cash_r - borrow
    traded = pos.diff().abs().sum(1)
    return (r - traded * cost), gross
