"""
Replication check (PROTOCOL section 7): reproduce published numbers with the papers' own
conventions (same-day-close execution, their costs, their sample) before any comparison.

    python src/replicate.py     # -> results/replication.csv
"""
import pandas as pd

import config as C
import data as D
import engine as E
import strategies as S


def window(r, start, end):
    return r[(r.index >= start) & (r.index <= end)]


def main():
    C.RESULTS.mkdir(exist_ok=True)
    m = D.french_market()
    ind = D.french_industries()
    rf = m["rf"]
    rows = []

    def add(paper, item, r, published):
        s = E.summary(r, rf)
        rows.append({"paper": paper, "item": item, **s,
                     **{f"pub_{k}": v for k, v in published.items()}})

    # --- Gayed (2026 revision of Leverage for the Long Run), French market 1928 -> 2026-07
    a, b = "1928-01-01", "2026-07-31"
    pub = {1: (0.1104, 0.1128, 0.68, -0.3379), 2: (0.1619, 0.2256, 0.62, -0.6027),
           3: (0.2083, 0.3385, 0.62, -0.7867)}
    for L, (cg, vo, sh, dd) in pub.items():
        r = window(S.s4_trend(m["mkt"], rf, L=L, lag=1, cost=0.0005), a, b)
        add("Gayed LftLR rev.", f"{L}x trend", r, dict(cagr=cg, vol=vo, sharpe=sh, max_dd=dd))
    pubc = {2: (0.1144, 0.3444, 0.39, -0.9844), 3: (0.1044, 0.5167, 0.39, -0.9989)}
    for L, (cg, vo, sh, dd) in pubc.items():
        r = window(S.constant(m["mkt"], rf, L=L), a, b)
        add("Gayed LftLR rev.", f"{L}x constant", r, dict(cagr=cg, vol=vo, sharpe=sh, max_dd=dd))
    add("Gayed LftLR rev.", "market", window(m["mkt"], a, b),
        dict(cagr=0.1001, vol=0.1721, sharpe=0.44, max_dd=-0.8407))

    # --- Gayed (2026 revision of Beta Rotation), French portfolios 1926-07-31 -> 2026-07-31, gross
    a, b = "1926-07-31", "2026-07-31"
    r = window(S.s3_beta_rotation(ind["Util"], m["mkt"], lag=1, cost=0.0), a, b)
    add("Gayed Beta rotation rev.", "rotation gross", r,
        dict(cagr=0.1298, vol=0.1688, sharpe=0.60, max_dd=-0.8523))
    add("Gayed Beta rotation rev.", "market", window(m["mkt"], a, b),
        dict(cagr=0.1024, vol=0.1711, sharpe=0.46, max_dd=-0.8407))
    add("Gayed Beta rotation rev.", "utilities", window(ind["Util"], a, b),
        dict(cagr=0.0913, vol=0.1746, sharpe=0.39, max_dd=-0.8756))

    # --- Zarattini & Antonacci: 48 industries, Jul 1926 -> Mar 2024, gross, cap 200%
    a, b = "1926-07-01", "2024-03-31"
    r, gross = S.s5_industry_trend(ind, rf, cap=2.0, lag=1)
    r = window(r, a, b)
    add("Zarattini & Antonacci", "timing industry (cap 200%)", r,
        dict(cagr=0.182, vol=0.126, sharpe=1.39))
    add("Zarattini & Antonacci", "market", window(m["mkt"], a, b),
        dict(cagr=0.097, vol=0.171, sharpe=0.63))
    print(f"S5 average gross exposure: {window(gross, a, b).mean():.2f}")

    # --- Faber (2013 update), Appendix B decade table: S&P 500 vs 10-month timing.
    # Faber uses GFD S&P 500 total returns; we use the French market (all US stocks): a proxy.
    faber = {"1930s": (-0.0047, 0.0315), "1940s": (0.0899, 0.0552), "1950s": (0.1926, 0.1740),
             "1960s": (0.0776, 0.0712), "1970s": (0.0588, 0.0840), "1980s": (0.1755, 0.1527),
             "1990s": (0.1821, 0.1309), "2000s": (-0.0094, 0.0773)}
    tim = S.s1_faber(m["mkt"], rf, lag=1, cost=0.0)
    dec_rows = []
    for dec, (bh_pub, tm_pub) in faber.items():
        y0 = int(dec[:4])
        a, b = f"{y0}-01-01", f"{y0 + 9}-12-31"
        dec_rows.append({"decade": dec, "market": E.cagr(window(m["mkt"], a, b)),
                         "pub_sp500": bh_pub, "timing": E.cagr(window(tim, a, b)),
                         "pub_timing": tm_pub})
    dec = pd.DataFrame(dec_rows)
    dec["timing_minus_market"] = dec.timing - dec.market
    dec["pub_timing_minus_sp500"] = dec.pub_timing - dec.pub_sp500
    dec.to_csv(C.RESULTS / "replication_faber_decades.csv", index=False)
    print(dec.round(4).to_string(index=False))
    print("sign agreement of timing-minus-market by decade:",
          int((dec.timing_minus_market * dec.pub_timing_minus_sp500 > 0).sum()), "/", len(dec))

    # --- Antonacci: monthly. US = French market; non-US = French Ind_all (EAFE-like, from 1975,
    # so the first trade is Jan 1976 vs the paper's 1974); bonds = 5-year Treasury built from
    # FRED GS5 yields (proxy for the Barclays Aggregate).
    us = D.to_monthly(m["mkt"])
    rfm = D.to_monthly(rf)
    intl = D.french_intl_monthly()
    bond = D.bond_from_yield(D.fred("GS5"), 5)
    mrows = []

    def addm(item, r, published, a, b):
        r = r[(r.index >= a) & (r.index <= b)]
        mrows.append({"paper": "Antonacci", "item": item, **E.summary_monthly(r, rfm),
                      **{f"pub_{k}": v for k, v in published.items()}})

    a, b = "1974-01-31", "2011-12-31"           # 2012/2016 paper, Table 1 (T-bills as safe asset)
    dm_tb, _ = S.s2_dual_momentum(us, intl, rfm, rfm, cost=0.0)
    addm("equities module, dual (T-bills)", dm_tb, dict(cagr=.1579, vol=.1277, sharpe=.73,
                                                         max_dd=-.2301), a, b)
    addm("equities module, relative only", S.relative_momentum(us, intl),
         dict(cagr=.1346, vol=.1617, sharpe=.45, max_dd=-.5456), a, b)
    addm("US stocks", us, dict(cagr=.1149, vol=.1586, sharpe=.35, max_dd=-.5065), a, b)
    addm("non-US stocks", intl, dict(cagr=.1186, vol=.1767, sharpe=.33, max_dd=-.5737), a, b)
    a, b = "1974-01-31", "2015-03-31"           # blog table: GEM with bonds as safe asset
    gem, _ = S.s2_dual_momentum(us, intl, rfm, bond, cost=0.0)
    addm("GEM (bonds as safe asset)", gem, dict(cagr=.177, vol=.124, sharpe=.89, max_dd=-.178),
         a, b)
    mout = pd.DataFrame(mrows)
    print(mout.round(4).to_string(index=False))
    rows.extend(mrows)

    # --- Zarattini & Antonacci, ETF section: 31 State Street ETFs, Jan 2005 -> Mar 2024,
    # same-day close, cap 200%, no costs (the paper charges only $0.0035/share).
    # Sharpe here as the paper defines it: average return / volatility.
    import numpy as np
    rets = D.etf_returns()
    rfe = rf.reindex(rets.index).fillna(0.0)
    sec = rets[D.S5_ETFS]
    sec = sec[sec.index >= "2004-08-01"]
    r, _ = S.s5_industry_trend(sec, rfe, cap=2.0, lag=1)
    r = r[(r.index >= "2005-01-01") & (r.index <= "2024-03-31")]
    spy = rets["SPY"].loc[r.index]
    for item, x, pub in (("timing ETFs (raw Sharpe)", r, dict(sharpe=0.61, max_dd=-0.24)),
                         ("SPY (raw Sharpe)", spy, dict(sharpe=0.59, max_dd=-0.55))):
        s = E.summary(x, rfe)
        s["sharpe"] = float(x.mean() * 252 / (x.std() * np.sqrt(252)))
        rows.append({"paper": "Zarattini & Antonacci (ETFs)", "item": item, **s,
                     **{f"pub_{k}": v for k, v in pub.items()}})

    out = pd.DataFrame(rows)
    out.to_csv(C.RESULTS / "replication.csv", index=False)
    cols = ["paper", "item", "start", "end", "cagr", "pub_cagr", "vol", "pub_vol",
            "sharpe", "pub_sharpe", "max_dd", "pub_max_dd", "arith_ann"]
    print(out[cols].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
