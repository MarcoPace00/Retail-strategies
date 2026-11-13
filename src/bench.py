"""
The common test bench (PROTOCOL sections 4-6).

Main case: signal at a close, trade at the next day's close (lag=2); 5 bp per one-way
trade (10 bp on leveraged products); cash earns the 1-month T-bill return minus 0.15%.
Everything ends on 2026-09-30, the last day of the T-bill series.

    python src/bench.py     # -> results/summary.csv, primary_tests.csv, sensitivities.csv,
                            #    s6_weight_grid.csv, returns.parquet
"""
import warnings

import numpy as np
import pandas as pd

import antifragile as A
import config as C
import data as D
import engine as E
import stats as ST
import strategies as S

warnings.filterwarnings("ignore", category=RuntimeWarning)
END = "2026-09-30"
PUB = {"S1": "2006-01-01", "S2": "2012-01-01", "S3": "2014-01-01", "S4": "2016-01-01",
       "S5": "2024-04-01", "S6": "2019-03-01"}


def clip(r):
    return r[r.index <= END]


def cash_daily(rf, fee=C.CASH_FEE):
    return rf - fee * E.calendar_days(rf.index) / 365.25


# --------------------------------------------------------------------------- #
# tier A / B builders (French library, FRED)
# --------------------------------------------------------------------------- #
def tier_a(m, ind, lag=2, cost=C.COST_ETF, cash_fee=C.CASH_FEE):
    rf, mkt = m.rf, m.mkt
    out = {}
    out["S1 Faber US"] = (S.s1_faber(mkt, rf, lag=lag, cost=cost, cash_fee=cash_fee), mkt)
    out["S3 Beta rotation"] = (S.s3_beta_rotation(ind["Util"], mkt, lag=lag, cost=cost),
                               mkt)
    for L in (1, 2, 3):
        c = cost if L == 1 else 2 * cost              # leveraged products: twice the cost
        r = S.s4_trend(mkt, rf, L=L, lag=lag, cost=c, cash_fee=cash_fee)
        out[f"S4 Trend {L}x"] = (r, mkt if L == 1 else S.constant(mkt, rf, L=L))
    for cap in (1.0, 2.0, 3.0):
        c = cost if cap == 1 else 2 * cost
        r, _ = S.s5_industry_trend(ind, rf, cap=cap, lag=lag, cost=c, cash_fee=cash_fee,
                                   spread=C.LEV_SPREAD, lev_fee=C.LEV_FEE)
        out[f"S5 Industry trend cap {int(cap * 100)}%"] = (r, mkt)
    return {k: (clip(s), clip(b)) for k, (s, b) in out.items()}


def tier_b(m, cost=C.COST_ETF):
    us, rfm = D.to_monthly(m.mkt), D.to_monthly(m.rf)
    intl = D.french_intl_monthly()
    bond = D.bond_from_yield(D.fred("GS5"), 5)
    gem, _ = S.s2_dual_momentum(us, intl, rfm, bond, cost=cost)
    mix = pd.concat({"us": us, "intl": intl, "bond": bond}, axis=1).dropna()
    bench = 0.3 * mix.us + 0.3 * mix.intl + 0.4 * mix.bond
    return {"S2 GEM": (gem, bench)}, rfm


# --------------------------------------------------------------------------- #
# tier C builders (ETFs)
# --------------------------------------------------------------------------- #
def month_ends(index):
    return index.to_series().groupby(index.to_period("M")).max().values


def faber_targets(close, assets):
    me = close[assets].loc[month_ends(close.index)]
    sma = me.rolling(10, min_periods=10).mean()
    ok = sma.notna().all(1)
    on = (me > sma)[ok].astype(float) / len(assets)
    on["CASH"] = 1 - on.sum(1)
    return on


def gem_targets(close, rf):
    me_idx = month_ends(close.index)
    px = close[["SPY", "EFA", "AGG"]].loc[me_idx]
    tb = (1 + rf).cumprod().reindex(close.index).ffill().loc[me_idx]
    r12 = px / px.shift(12) - 1
    t12 = tb / tb.shift(12) - 1
    ok = r12.notna().all(1) & t12.notna()
    rows = {}
    for d in r12.index[ok]:
        pick = "SPY" if r12.at[d, "SPY"] >= r12.at[d, "EFA"] else "EFA"
        if r12.at[d, pick] <= t12[d]:
            pick = "AGG"
        rows[d] = {pick: 1.0}
    return pd.DataFrame(rows).T.fillna(0.0)


def tier_c(m, lag=2, cost=C.COST_ETF, cash_fee=C.CASH_FEE):
    ohlc = D.etf_prices()
    close = ohlc["Close"][ohlc.index <= END]
    rets = close.pct_change(fill_method=None)
    rf = m.rf.reindex(rets.index).fillna(0.0)
    cash = cash_daily(rf, cash_fee)
    R = rets.assign(CASH=cash)
    lev_cost = {"SSO": C.COST_LEVERAGED, "UPRO": C.COST_LEVERAGED, "TQQQ": C.COST_LEVERAGED,
                "EDC": C.COST_LEVERAGED, "CASH": 0.0}
    out = {}

    # S1: Faber on SPY, and the 5-asset portfolio
    t = faber_targets(close, ["SPY"])
    out["S1 Faber US (ETF)"] = (E.run_weights(t, R, lag, cost, lev_cost), rets.SPY)
    g5 = ["SPY", "EFA", "IEF", "GSG", "VNQ"]
    t = faber_targets(close, g5)
    bh = pd.DataFrame(0.2, index=t.index, columns=g5)
    out["S1 Faber GTAA-5 (ETF)"] = (E.run_weights(t, R, lag, cost, lev_cost),
                                   E.run_weights(bh, R, 1, 0.0))
    # S2: GEM on SPY / EFA / AGG
    t = gem_targets(close, m.rf)
    mix = pd.DataFrame({"SPY": 0.3, "EFA": 0.3, "AGG": 0.4}, index=t.index)
    out["S2 GEM (ETF)"] = (E.run_weights(t, R, lag, cost, lev_cost),
                           E.run_weights(mix, R, 1, 0.0))
    # S3: beta rotation XLU / VTI
    out["S3 Beta rotation (ETF)"] = (S.s3_beta_rotation(rets.XLU, rets.VTI, lag=lag,
                                                        cost=cost), rets.VTI)
    # S4: 200-day SPY signal, actual SPY / SSO / UPRO
    level = (1 + rets.SPY.fillna(0)).cumprod().where(close.SPY.notna())
    sma = level.rolling(200, min_periods=200).mean()
    on = (level > sma).astype(float).where(sma.notna())
    pos = on.shift(lag)
    for etf, L in (("SPY", 1), ("SSO", 2), ("UPRO", 3)):
        c = cost if L == 1 else (C.COST_LEVERAGED if cost > 0 else 0.0)
        r = pos * rets[etf] + (1 - pos) * cash - pos.diff().abs() * c
        out[f"S4 Trend {L}x (ETF {etf})"] = (r.dropna(), rets[etf])
    # S5: 31 State Street sector ETFs
    sec = rets[D.S5_ETFS]
    for cap in (1.0, 2.0, 3.0):
        c = cost if cap == 1 else (C.COST_LEVERAGED if cost > 0 else 0.0)
        r, _ = S.s5_industry_trend(sec, rf, cap=cap, lag=lag, cost=c, cash_fee=cash_fee,
                                   spread=C.LEV_SPREAD, lev_fee=C.LEV_FEE)
        r = r[r.index >= sec.dropna(how="all").index[60]]
        out[f"S5 Industry trend cap {int(cap * 100)}% (ETF)"] = (r, rets.SPY)
    # S6: Antifragile, published universe, and the leveraged variant
    fh = A.factors(A.HEDGES)
    hedge_start = fh.date.min()                       # the hedge group needs 504 days too
    for name, group in (("S6 Antifragile (ETF)", A.SECTORS),
                        ("S6-L Antifragile + UPRO/TQQQ/EDC (ETF)", A.SECTORS + A.LEVERED)):
        fs = A.factors(group)
        fs = fs[fs.date >= max(hedge_start, pd.Timestamp("2010-02-28" if "S6-L" in name
                                                          else "1900-01-01"))]
        t = A.targets(fs, fh, A.PAPER_W)
        out[name] = (E.run_weights(t, R, lag, cost, lev_cost), rets.SPY)
    return {k: (clip(s.dropna()), clip(b.dropna())) for k, (s, b) in out.items()}, rf


# --------------------------------------------------------------------------- #
def summarise(results, rf, tier, monthly=False):
    rows = []
    fn = E.summary_monthly if monthly else E.summary
    for name, (s, b) in results.items():
        idx = s.index.intersection(b.index)
        s, b = s.loc[idx], b.loc[idx]
        key = name.split()[0].replace("-L", "")
        for period, mask in (("full", idx == idx),
                             ("post-publication", idx >= pd.Timestamp(PUB[key]))):
            if mask.sum() < 24:
                continue
            ss, bb = fn(s[mask], rf), fn(b[mask], rf)
            rows.append({"tier": tier, "strategy": name, "period": period,
                         **{f"s_{k}": v for k, v in ss.items()},
                         **{f"b_{k}": v for k, v in bb.items() if k not in ("start", "end")}})
    return rows


PRIMARY = {"S1": ("A", "S1 Faber US"), "S2": ("B", "S2 GEM"), "S3": ("A", "S3 Beta rotation"),
           "S4": ("A", "S4 Trend 2x"), "S5": ("A", "S5 Industry trend cap 100%"),
           "S6": ("C", "S6 Antifragile (ETF)")}


def primary_tests(A_, B_, C_, rfd, rfm, rfc):
    pools = {"A": (A_, rfd, 252), "B": (B_, rfm, 12), "C": (C_, rfc, 252)}
    rows = []
    for key, (tier, name) in PRIMARY.items():
        res, rf, ann = pools[tier]
        s, b = res[name]
        if name == "S4 Trend 2x":                     # vs the unlevered market (paper's test)
            b = A_["S4 Trend 1x"][1]
        for period, start in (("full", None), ("post-publication", PUB[key])):
            ss = s if start is None else s[s.index >= start]
            bb = b if start is None else b[b.index >= start]
            st = ST.sharpe_diff_bootstrap(ss, bb, rf, block=ann, ann=ann)
            rows.append({"test": f"{key} {period}", "strategy": name, "tier": tier,
                         "start": ss.index[0].date(), "end": ss.index[-1].date(), **st})
    out = pd.DataFrame(rows)
    out["p_holm"] = ST.holm(out.p_one_sided)
    return out


def sensitivities(m, ind):
    """Primary tier-A strategies under alternative assumptions (full sample)."""
    rows = []
    cases = {"main": {}, "cash 0%": {"cash_fee": None}, "same-day close": {"lag": 1},
             "costs 0 bp": {"cost": 0.0}, "costs 25 bp": {"cost": 0.0025}}
    for case, kw in cases.items():
        args = {"lag": 2, "cost": C.COST_ETF, "cash_fee": C.CASH_FEE}
        args.update({k: v for k, v in kw.items() if k != "cash_fee"})
        if "cash_fee" in kw:                         # 0% cash: fee = the whole T-bill return
            res = tier_a_zero_cash(m, ind, args["lag"], args["cost"])
        else:
            res = tier_a(m, ind, **args)
        for name in ("S1 Faber US", "S3 Beta rotation", "S4 Trend 1x", "S4 Trend 2x",
                     "S5 Industry trend cap 100%"):
            s, b = res[name]
            rows.append({"case": case, "strategy": name, **E.summary(s, m.rf),
                         "bench_sharpe": E.sharpe(b.loc[s.index.intersection(b.index)], m.rf)})
    return pd.DataFrame(rows)


def tier_a_zero_cash(m, ind, lag, cost):
    """Cash earns 0%: the cash return is replaced by zero (T-bills still the Sharpe hurdle)."""
    m0 = m.copy()
    res = {}
    mkt, rf = m.mkt, m.rf
    zero = rf * 0
    res["S1 Faber US"] = (S.s1_faber(mkt, zero, lag=lag, cost=cost), mkt)
    res["S3 Beta rotation"] = (S.s3_beta_rotation(ind["Util"], mkt, lag=lag, cost=cost), mkt)
    for L in (1, 2):
        c = cost if L == 1 else 2 * cost
        lev = E.leveraged(mkt, rf, L, C.LEV_SPREAD, C.LEV_FEE if L > 1 else 0.0)
        level = E.wealth(mkt)
        sma = level.rolling(200, min_periods=200).mean()
        pos = (level > sma).astype(float).where(sma.notna()).shift(lag)
        r = (pos * lev - pos.diff().abs() * c).dropna()
        res[f"S4 Trend {L}x"] = (r, mkt if L == 1 else S.constant(mkt, rf, L=L))
    r, _ = S.s5_industry_trend(ind, zero, cap=1.0, lag=lag, cost=cost)
    res["S5 Industry trend cap 100%"] = (r, mkt)
    return {k: (clip(s), clip(b)) for k, (s, b) in res.items()}


def s6_grid(m):
    """Distribution of S6 results over every weight combination (0.05 grid)."""
    ohlc = D.etf_prices()
    close = ohlc["Close"][ohlc.index <= END]
    rets = close.pct_change(fill_method=None)
    rf = m.rf.reindex(rets.index).fillna(0.0)
    R = rets.assign(CASH=cash_daily(rf))
    fs, fh = A.factors(A.SECTORS), A.factors(A.HEDGES)
    fs = fs[fs.date >= fh.date.min()]
    rows = []
    for w in A.weight_grid(0.05):
        r = clip(E.run_weights(A.targets(fs, fh, w), R, 2, C.COST_ETF))
        rows.append({"wM": w[0], "wV": w[1], "wC": w[2], "wT": w[3], **E.summary(r, rf)})
    return pd.DataFrame(rows)


def main():
    m = D.french_market()
    m = m[m.index <= END]
    ind = D.french_industries()
    ind = ind[ind.index <= END]
    A_ = tier_a(m, ind)
    B_, rfm = tier_b(m)
    C_, rfc = tier_c(m)
    rows = summarise(A_, m.rf, "A") + summarise(B_, rfm, "B", monthly=True) + \
        summarise(C_, rfc, "C")
    summ = pd.DataFrame(rows)
    summ.to_csv(C.RESULTS / "summary.csv", index=False)
    cols = ["tier", "strategy", "period", "s_start", "s_end", "s_cagr", "b_cagr", "s_sharpe",
            "b_sharpe", "s_max_dd", "b_max_dd"]
    print(summ[cols].round(3).to_string(index=False))

    prim = primary_tests(A_, B_, C_, m.rf, rfm, rfc)
    prim.to_csv(C.RESULTS / "primary_tests.csv", index=False)
    print(prim.round(3).to_string(index=False))

    sens = sensitivities(m, ind)
    sens.to_csv(C.RESULTS / "sensitivities.csv", index=False)
    print(sens[["case", "strategy", "cagr", "sharpe", "max_dd", "bench_sharpe"]]
          .round(3).to_string(index=False))

    pd.DataFrame({f"{k}|strategy": v[0] for k, v in {**A_, **C_}.items()}).to_parquet(
        C.RESULTS / "returns.parquet")

    grid = s6_grid(m)
    grid.to_csv(C.RESULTS / "s6_weight_grid.csv", index=False)
    print("S6 weight grid:", len(grid), "combinations; Sharpe median",
          round(grid.sharpe.median(), 3), "range", round(grid.sharpe.min(), 3), "to",
          round(grid.sharpe.max(), 3))


if __name__ == "__main__":
    main()
