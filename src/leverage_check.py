"""
Check the synthetic leverage model against real leveraged ETFs (PROTOCOL section 4).

Synthetic L-times S&P 500 = L x SPY return - (L-1) x (T-bill + 1%) - 1% fee, daily.
Compared with SSO (2x, from 2006) and UPRO (3x, from 2009).

    python src/leverage_check.py      # -> results/leverage_check.csv
"""
import numpy as np
import pandas as pd

import config as C
import data as D
import engine as E

END = "2026-09-30"


def main():
    r = D.etf_returns()
    rf = D.french_market()["rf"]
    rows = []
    for etf, L in (("SSO", 2), ("UPRO", 3)):
        df = pd.concat({"spy": r["SPY"], "act": r[etf], "rf": rf}, axis=1).dropna()
        df = df[df.index <= END]
        syn = E.leveraged(df.spy, df.rf, L, C.LEV_SPREAD, C.LEV_FEE)
        diff = syn - df.act
        rows.append({"etf": etf, "leverage": L, "start": df.index[0].date(),
                     "end": df.index[-1].date(),
                     "cagr_actual": E.cagr(df.act), "cagr_synthetic": E.cagr(syn),
                     "max_dd_actual": E.max_dd(df.act), "max_dd_synthetic": E.max_dd(syn),
                     "tracking_error_ann": float(diff.std() * np.sqrt(C.ANN)),
                     "daily_corr": float(df.act.corr(syn))})
    out = pd.DataFrame(rows)
    out.to_csv(C.RESULTS / "leverage_check.csv", index=False)
    print(out.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
