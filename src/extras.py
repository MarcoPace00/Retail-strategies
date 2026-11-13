"""
Descriptive results (PROTOCOL sections 5 and 9, appendix):
  * returns in historical crashes (Tier A)
  * after Italian tax (Tier C)
  * results in EUR without currency hedging (Tier C appendix)

    python src/extras.py     # -> results/crashes.csv, tax.csv, eur_appendix.csv
"""
import warnings

import numpy as np
import pandas as pd

import antifragile as A
import bench as BN
import config as C
import data as D
import engine as E
import strategies as S
import tax as TX

warnings.filterwarnings("ignore", category=RuntimeWarning)
END = BN.END

CRASHES = {"1929-32 Great Depression": ("1929-09-03", "1932-07-08"),
           "1937-38 recession": ("1937-03-06", "1938-03-31"),
           "1973-74 oil shock": ("1973-01-11", "1974-10-03"),
           "1987 crash": ("1987-08-25", "1987-12-04"),
           "2000-02 dot-com": ("2000-03-24", "2002-10-09"),
           "2007-09 financial crisis": ("2007-10-09", "2009-03-09"),
           "2020 Covid": ("2020-02-19", "2020-03-23"),
           "2022 rate shock": ("2022-01-03", "2022-10-12")}


def crashes(m, ind):
    res = BN.tier_a(m, ind)
    series = {"US market": m.mkt, "S1 Faber": res["S1 Faber US"][0],
              "S3 Beta rotation": res["S3 Beta rotation"][0],
              "S4 Trend 1x": res["S4 Trend 1x"][0], "S4 Trend 2x": res["S4 Trend 2x"][0],
              "Constant 2x": S.constant(m.mkt, m.rf, 2),
              "S5 Industry trend": res["S5 Industry trend cap 100%"][0]}
    rows = []
    for name, (a, b) in CRASHES.items():
        row = {"crash": name, "from": a, "to": b}
        for k, r in series.items():
            x = r[(r.index >= a) & (r.index <= b)]
            row[k] = float((1 + x).prod() - 1)
        rows.append(row)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
REGIME = {"GLD": "etp", "FXY": "etp", "FXF": "etp", "UPRO": "etp", "TQQQ": "etp",
          "EDC": "etp"}                                  # everything else: UCITS ETF
RATE = {"IEF": 0.125, "TLT": 0.125, "SHY": 0.125}       # government bond ETFs


def from_positions(pos, asset):
    """Targets at every change of a 0/1 position (decision dates, before the lag)."""
    pos = pos.dropna()
    ch = pos[pos != pos.shift(1)]
    return pd.DataFrame({asset: ch, "CASH": 1 - ch})


def tax_table(m):
    ohlc = D.etf_prices()
    close = ohlc["Close"][ohlc.index <= END]
    rets = close.pct_change(fill_method=None)
    rf = m.rf.reindex(rets.index).fillna(0.0)
    R = rets.assign(CASH=BN.cash_daily(rf))
    level = (1 + rets.SPY.fillna(0)).cumprod().where(close.SPY.notna())
    sma = level.rolling(200, min_periods=200).mean()
    trend = (level > sma).astype(float).where(sma.notna())
    lev_cost = {a: C.COST_LEVERAGED for a in ("SSO", "UPRO", "TQQQ", "EDC")}

    def bh(asset, start):
        return pd.DataFrame({asset: [1.0]}, index=[pd.Timestamp(start)])

    pairs = {}
    t = BN.faber_targets(close, ["SPY"])
    pairs["S1 Faber US"] = (t, bh("SPY", t.index[0]))
    for etf, L in (("SPY", 1), ("SSO", 2), ("UPRO", 3)):
        on = trend[rets[etf].notna()]
        tt = from_positions(on, etf)
        pairs[f"S4 Trend {L}x ({etf})"] = (tt, bh(etf, tt.index[0]))
    U, M = (1 + rets.XLU.fillna(0)).cumprod(), (1 + rets.VTI.fillna(0)).cumprod()
    ratio = (U / M)[rets.VTI.notna() & rets.XLU.notna()]
    last = ratio.groupby(ratio.index.to_period("W-FRI")).tail(1)
    st = (last / last.shift(4) - 1 > 0).astype(float).where(last.shift(4).notna()).dropna()
    st = st[st != st.shift(1)]
    pairs["S3 Beta rotation"] = (pd.DataFrame({"XLU": st, "VTI": 1 - st}),
                                 bh("VTI", st.index[0]))
    t = BN.gem_targets(close, m.rf)
    mix = pd.DataFrame({"SPY": 0.3, "EFA": 0.3, "AGG": 0.4}, index=t.index)
    pairs["S2 GEM"] = (t, mix)
    wl = []
    S.s5_industry_trend(rets[D.S5_ETFS], rf, cap=1.0, lag=0, weights_out=wl)
    w = wl[0].fillna(0.0)
    w = w[w.index >= rets[D.S5_ETFS].dropna(how="all").index[60]]
    w["CASH"] = 1 - w.sum(1)
    pairs["S5 Industry trend"] = (w, bh("SPY", w.index[0]))
    fh = A.factors(A.HEDGES)
    fs = A.factors(A.SECTORS)
    t = A.targets(fs[fs.date >= fh.date.min()], fh, A.PAPER_W)
    pairs["S6 Antifragile"] = (t, bh("SPY", t.index[0]))

    rows = []
    zero = {a: 0.0 for a in R.columns}
    for name, (ts, tb) in pairs.items():
        out = {"strategy": name}
        for label, tg, lag, cost in (("strategy", ts, 2, C.COST_ETF),
                                     ("benchmark", tb, 1, 0.0)):
            path, final, _ = TX.run_taxed(tg, R, REGIME, zero, lag, cost, lev_cost)
            _, final_tax, taxes = TX.run_taxed(tg, R, REGIME, RATE, lag, cost, lev_cost)
            path = path[path.index <= END]
            yrs = (path.index[-1] - path.index[0]).days / 365.25
            out[f"{label}_cagr_pre_tax"] = final ** (1 / yrs) - 1
            out[f"{label}_cagr_after_tax"] = final_tax ** (1 / yrs) - 1
        out["start"] = path.index[0].date()
        out["tax_drag_strategy"] = out["strategy_cagr_pre_tax"] - out["strategy_cagr_after_tax"]
        out["tax_drag_benchmark"] = out["benchmark_cagr_pre_tax"] - \
            out["benchmark_cagr_after_tax"]
        rows.append(out)
        print(name, {k: round(v, 4) for k, v in out.items() if isinstance(v, float)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
def eur_appendix(m):
    res, rfc = BN.tier_c(m)
    fx = D.eurusd().ffill()
    eur_rate = D.fred("IR3TIB01EZM156N")                 # euro-area 3-month rate, monthly
    rows = []
    for name, (s, b) in res.items():
        if "S6-L" in name:
            continue
        idx = s.index.intersection(b.index)
        f = fx.reindex(idx).ffill()
        conv = f.shift(1) / f
        rf_eur = (eur_rate.reindex(idx, method="ffill") / 252).fillna(0.0)
        for label, x in (("strategy", s.loc[idx]), ("benchmark", b.loc[idx])):
            xe = ((1 + x) * conv - 1).dropna()
            xe = xe[xe.index >= "1999-02-01"]
            sm = E.summary(xe, rf_eur)
            rows.append({"strategy": name, "series": label, **sm})
    return pd.DataFrame(rows)


def main():
    m = D.french_market()
    m = m[m.index <= END]
    ind = D.french_industries()
    ind = ind[ind.index <= END]
    cr = crashes(m, ind)
    cr.to_csv(C.RESULTS / "crashes.csv", index=False)
    print(cr.round(3).to_string(index=False))
    tx = tax_table(m)
    tx.to_csv(C.RESULTS / "tax.csv", index=False)
    eu = eur_appendix(m)
    eu.to_csv(C.RESULTS / "eur_appendix.csv", index=False)
    print(eu[["strategy", "series", "start", "cagr", "vol", "sharpe", "max_dd"]]
          .round(3).to_string(index=False))


if __name__ == "__main__":
    main()
