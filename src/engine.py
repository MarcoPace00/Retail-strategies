"""Performance metrics and the synthetic-leverage return model."""
import numpy as np
import pandas as pd

import config as C


def wealth(r):
    return (1 + r.fillna(0.0)).cumprod()


def cagr(r):
    """Compound annual growth over calendar time (first return counted from the prior day)."""
    r = r.dropna()
    days = (r.index[-1] - r.index[0]).days + 1
    return float(wealth(r).iloc[-1] ** (365.25 / days) - 1)


def vol(r):
    return float(r.std() * np.sqrt(C.ANN))


def sharpe(r, rf):
    x = (r - rf.reindex(r.index)).dropna()
    return float(x.mean() / x.std() * np.sqrt(C.ANN))


def max_dd(r):
    w = wealth(r)
    return float((w / w.cummax().clip(lower=1.0) - 1).min())


def summary(r, rf):
    return {"start": r.index[0].date(), "end": r.index[-1].date(),
            "cagr": cagr(r), "vol": vol(r), "sharpe": sharpe(r, rf), "max_dd": max_dd(r),
            "arith_ann": float(r.mean() * C.ANN)}


def summary_monthly(r, rf):
    """Monthly-data version: CAGR, annualised vol and Sharpe (x12), month-end drawdown."""
    r = r.dropna()
    x = (r - rf.reindex(r.index)).dropna()
    w = (1 + r).cumprod()
    return {"start": r.index[0].date(), "end": r.index[-1].date(),
            "cagr": float(w.iloc[-1] ** (12 / len(r)) - 1), "vol": float(r.std() * np.sqrt(12)),
            "sharpe": float(x.mean() / x.std() * np.sqrt(12)),
            "max_dd": float((w / w.cummax().clip(lower=1.0) - 1).min()),
            "arith_ann": float(r.mean() * 12)}


def run_weights(targets, rets, lag=2, cost=0.0005, cost_map=None):
    """Daily returns of a portfolio rebalanced to `targets` (rows = decision dates).

    targets : DataFrame, decision date x asset, weights summing to 1 (may include 'CASH')
    rets    : DataFrame of daily returns with the same asset columns
    lag     : rows between the decision close and the execution close
              (1 = same close, 2 = next day's close: the protocol's main case)
    Holdings drift with returns between rebalances. Each rebalance pays cost x |traded|
    (per asset from cost_map if given), deducted from the next day's return."""
    rets = rets[targets.columns].fillna(0.0)
    idx = rets.index
    pos_of = {d: idx.get_indexer([d], method="pad")[0] for d in targets.index}
    exec_rows = {min(p + lag - 1, len(idx) - 1): d for d, p in pos_of.items() if p >= 0}
    c = pd.Series(cost, index=targets.columns) if cost_map is None else \
        pd.Series({a: cost_map.get(a, cost) for a in targets.columns})
    w = None
    out = np.full(len(idx), np.nan)
    pending_cost = 0.0
    R = rets.values
    for i in range(len(idx)):
        if w is not None:
            gross = w * (1 + R[i])
            out[i] = gross.sum() - 1 - pending_cost
            w = gross / gross.sum()
            pending_cost = 0.0
        if i in exec_rows:
            new = targets.loc[exec_rows[i]].values
            prev = np.zeros_like(new) if w is None else w
            pending_cost = float((np.abs(new - prev) * c.values).sum())
            w = new.astype(float)
    return pd.Series(out, index=idx).dropna()


def calendar_days(index):
    """Calendar days elapsed since the previous observation (first = 1)."""
    d = pd.Series(index, index=index).diff().dt.days
    return d.fillna(1).astype(float)


def leveraged(r, rf, L, spread=C.LEV_SPREAD, fee=C.LEV_FEE, rf_annual=None):
    """Daily return of an L-times daily-reset exposure.

    Borrowing on (L-1) at the previous day's T-bill rate (annualised x252) plus a spread,
    and the annual fee, both accrued over calendar days / 365.25."""
    if L == 1:
        return r.copy()
    days = calendar_days(r.index)
    rate = rf.shift(1).fillna(rf) * C.ANN if rf_annual is None else rf_annual
    borrow = (L - 1) * (rate + spread) * days / 365.25
    return L * r - borrow - fee * days / 365.25
