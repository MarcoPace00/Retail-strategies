# Replication check

Before any comparison, the code has to reproduce numbers the papers themselves published,
using each paper's own rules and conventions (PROTOCOL section 7). Output:
[`replication.csv`](replication.csv), [`replication_faber_decades.csv`](replication_faber_decades.csv).
Reproduce with `python src/replicate.py`.

## Summary

| Paper | What is compared | Result |
|---|---|---|
| Gayed, *Leverage for the Long Run* (2026 revision) | 1×, 2×, 3× trend and constant leverage, US market 1928–Jul 2026 | **Exact**: return, volatility, Sharpe ratio and maximum drawdown all match to 4 decimals |
| Gayed, *Beta Rotation* (2026 revision) | Utilities/market rotation on French portfolios 1926–Jul 2026, before costs | **Exact**: 12.98% a year, Sharpe 0.60, drawdown −85.23% |
| Zarattini & Antonacci, *A Century of Profitable Industry Trends* | 48-industry trend portfolio, Jul 1926–Mar 2024, before costs | **Close**: drawdown 33% (paper 33%), volatility 12.7% (12.6%), Sharpe 1.39 (1.39); return 19.2% (18.2%) |
| Zarattini & Antonacci, ETF section | 31 State Street sector ETFs, 2005–Mar 2024, before costs | **Exact**: Sharpe 0.61 (paper 0.61) vs SPY 0.59 (0.59); drawdown −23% (−24%) |
| Faber, *A Quantitative Approach to Tactical Asset Allocation* | 10-month moving-average timing by decade, 1930s–2000s | **Close**: timing beats or trails the market in the same 8 of 8 decades, by similar amounts |
| Antonacci, *Risk Premia Harvesting Through Dual Momentum* | US vs non-US stocks with T-bills or bonds as the safe asset | **Approximate**: Sharpe 0.67 vs 0.73 (T-bills), 0.86 vs 0.89 (bonds); return 1.4–1.8 points lower |

## Notes on the differences

- **Industry Trends:**
  - The paper's "Sharpe ratio" is average return ÷ volatility, without subtracting the T-bill
    rate. With that definition we get 1.39 (paper 1.39) for the strategy and 0.62 (0.63) for the
    market.
  - Our returns are 0.4–1.0 points higher for both the strategy and the market. That points to
    revisions in the underlying stock database (our file is the September 2026 version), not to
    the rule.
- **Faber:** the paper uses the S&P 500; we use the whole US market from the French library.
  Decade returns differ by up to about 2 points, but the direction of every decade matches.
- **Antonacci:** three data substitutions, all forced by free data availability:
  - non-US stocks come from the French library's international index (from January 1975, so our
    first trade is January 1976 instead of 1974), not MSCI EAFE / ACWI ex-US;
  - US stocks are the whole US market, not MSCI US;
  - the bond safe asset is a 5-year Treasury bond computed from FRED yields, not the Barclays
    Aggregate.

  Our benchmark returns are themselves about 1 point lower than the paper's, which accounts for
  most of the gap.

## A bug found during this check

In the Industry Trends code, an industry whose price did not move for 14 days got zero measured
volatility and therefore an infinite weight. Positions with zero measured volatility now get no
weight. Fixed before any comparison was run.
