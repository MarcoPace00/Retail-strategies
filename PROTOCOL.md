# Protocol (pre-registered)

> Written and fixed **before any code was written** (the private development history records the
> timestamps). After that, rules changed only through the changelog at the end, with results
> reported before and after any change.

## 1. Question

Six published, retail-oriented timing strategies all claim to beat buying and holding the stock
market, mostly by avoiding large crashes. **When every strategy is tested the same way (same
data, same costs, same cash, the published rules with nothing tuned), which ones still beat the
market, and are they still working after their papers came out?**

A second question, for a European (Italian) retail investor: **what is left after using the
products they can actually buy and paying Italian tax?**

Results are published whatever they are. If the main results are weak, any further analyses are
added in a separate, clearly labelled exploratory section; the main results are not changed.

## 2. Strategies (rules as published; nothing is tuned)

| # | Strategy | Rule, as published | Paper's data ends → post-publication test starts |
|---|---|---|---|
| S1 | **Faber trend timing** (Faber 2007, update 2013) | At each month-end, hold the asset if its price is above its 10-month simple moving average, otherwise hold cash. Applied to US stocks alone, and to the 5-asset portfolio (US stocks, foreign developed stocks, 10-year Treasuries, commodities, REITs), 20% each, each asset timed separately. | 2005 → Jan 2006 |
| S2 | **Dual momentum, Global Equities Momentum** (Antonacci 2012/2014) | At each month-end, compare the 12-month total return of US stocks and of non-US stocks; pick the higher. If the winner's 12-month return is below that of T-bills, hold bonds (US aggregate bond index) instead. No skipped month. | 2011 → Jan 2012 |
| S3 | **Beta rotation with utilities** (Gayed & Bilello 2014) | Every week, compare the 4-week total return of utilities with that of the whole market. If utilities did better, hold utilities next week; otherwise hold the market. Always fully invested in stocks. | 2013 → Jan 2014 |
| S4 | **Leverage for the Long Run** (Gayed & Bilello 2016) | Every day, if the S&P 500 total-return index closed above its 200-day simple moving average, hold the index at 1×, 2× or 3× daily leverage; otherwise hold cash. | 2015 → Jan 2016 |
| S5 | **Industry trend following** (Zarattini & Antonacci 2025) | For each of 48 US industries, buy when the close is at or above the lower of two upper bands (20-day Donchian high; 20-day Keltner-type band), exit when it falls below a trailing stop (the higher of the 40-day Donchian low and the 40-day Keltner-type lower band; the stop never moves down). Each held industry is sized for an equal share of 1.5% daily portfolio volatility (14-day volatility), rebalanced daily. **Total exposure capped at 100% (main case, no borrowing)**; the paper's 200% cap and a 300% cap (the most that 3× products allow) are sensitivities using the synthetic leverage model of §4. | Mar 2024 → Apr 2024 |
| S6 | **Antifragile Asset Allocation** (Giordano 2019) | At each month-end, rank 11 sector ETFs (XLY, XLV, XLU, XLP, XLK, XLI, XLF, XLE, XLB, VOX, RWR) on 4-month momentum, volatility, average correlation and a trend signal; hold the top 5 at 20% each if their 4-month momentum is positive. Unused weight goes to the top 3 of 7 hedge ETFs (FXY, FXF, GLD, IEF, SH, TLT, SHY) with positive momentum; otherwise to SHY (the paper's "cash"). | Feb 2019 → Mar 2019 |

**Benchmarks.** Each strategy is compared with buying and holding what it trades: the US market
(S1-US, S3, S4 at 1×, S5), the equal-weight 5-asset mix (S1-GTAA), a 60/40 global mix (S2), the
same leverage held permanently (S4 at 2× and 3×), and SPY (S6). S3 is also compared with a fixed
50/50 utilities/market mix, so the signal has to beat simply owning both.

### Antifragile: the unpublished parts

The paper does not publish the ranking weights, nor exactly how its "edited" volatility model
works. Fixed in advance:
- **Weights:** momentum, volatility and correlation get the weights of Keller & van Putten's
  *Flexible Asset Allocation* (2012), the model it builds on: 0.50 / 0.25 / 0.25. The trend signal
  gets 0.25, and the four weights are then rescaled to sum to 1.
- **Volatility:** standard GARCH(1,1) on 2 years of daily returns.
- **Robustness:** every combination of the four weights on a 0.05 grid is run, and the
  *distribution* of results (median and range) is reported. The best combination is never singled out.
- **Leveraged variant (S6-L), secondary:** the same model with UPRO (3× S&P 500), TQQQ (3× Nasdaq-100)
  and EDC (3× emerging markets) added to the sector list, starting when all three exist (2010).
  It is reported next to the published version but is **not** one of the 12 primary tests. The
  three funds were chosen after seeing an earlier informal test, so a test on them would not be
  independent.

## 3. Data and tiers

| Tier | Period | Data (free) | Strategies |
|---|---|---|---|
| **A — a century** | Jul 1926 → latest | Kenneth French data library: daily US market, 48 industry portfolios (incl. utilities), 1-month T-bill | S1-US, S3, S4, S5 |
| **B — half a century** | 1970s → latest | MSCI EAFE / ACWI ex-US monthly; US Treasury yields from FRED turned into bond returns; FTSE Nareit REITs; commodities only if a lawful long index series is found | S1-GTAA, S2 |
| **C — tradable ETFs** | ~2005 → latest | Adjusted ETF prices (Yahoo) | all six, on real ETFs, incl. S6 |

Every strategy is run in every tier its data allows. Tiers A and B use research portfolios that
nobody could buy directly; Tier C uses funds that existed.

**Data deviations from the papers (fixed now):**
- Pre-ETF bonds: a 5-year (S2) or 10-year (S1) constant-maturity Treasury return computed from
  FRED yields, instead of the commercial bond indices the papers used.
- S5 on daily closes only, as in the paper (which also had no highs and lows).
- Missing pre-1988 values are not filled in from other sources.

## 4. The common test bench

- **Execution:** the signal is read at a close, and the trade happens at the **next** day's close.
  A retail investor can't trade at a closing price they haven't seen yet. Same-day trading, as the
  papers assumed, is reported as a sensitivity.
- **Costs:** 5 bp per one-way trade on ETFs and the research portfolios; 10 bp on leveraged
  products. Results are also shown at 0 and 25 bp, because historical costs were higher.
- **Cash:** the 1-month T-bill return (French library, known point in time) minus 0.15% a year,
  the typical fee of an overnight-rate / money-market fund. Sensitivity: cash earns 0%.
- **Synthetic leverage (S4, and S5 above 100% exposure):** each day, L × index return
  − (L−1) × (T-bill rate + 1%) − a 1% annual fund fee, as in Gayed's 2026 revision. Before use,
  this simulation is checked against real SSO (2×) and UPRO (3×) returns since 2006/2009; the
  tracking error is reported.
- **Currency:** USD. An appendix repeats the Tier C results in EUR without currency hedging
  (EUR/USD rates from the ECB), as an extra.

## 5. What is measured

- Return per year (CAGR), volatility, Sharpe ratio (return above T-bills ÷ volatility), maximum
  drawdown, longest time below a previous peak.
- Return in the worst crashes: 1929–32, 1937–38, 1973–74, 1987, 2000–02, 2008–09, 2020, 2022.
- Trades per year, and time in the market.
- **After Italian tax** (Tier C): 26% on each realised gain. Gains on ETFs cannot be offset by
  earlier losses (ETF gains are taxed as "capital income", losses are "other income"), so every
  profitable exit is taxed immediately, while buy-and-hold defers all tax to the end.

## 6. Statistical tests (fixed in advance)

**Primary tests: two per strategy, 12 in total.**
1. Over the longest sample available, is the strategy's Sharpe ratio higher than its benchmark's?
2. After publication, is it still higher?

**How they are judged:**
- **Uncertainty:** each Sharpe difference gets a 95% interval from a paired block bootstrap:
  resample whole years of returns, strategy and benchmark together, 5,000 times.
- **Correction for testing 12 things:** the 12 p-values are corrected with Holm's method.
- **Everything else is descriptive:** drawdowns, crash returns, leverage levels, cost levels,
  tiers.

**No parameter search.** Sensitivity results (other moving averages, lookbacks, costs, execution
timing) are reported in full, and the published rule stays the headline.

## 7. Replication check, before any comparison

Before comparing anything, the code must reproduce published numbers from the same data,
within stated tolerances:
- Zarattini & Antonacci: 48 industries 1926–2024, 18.2% return, 12.6% volatility (gross).
- Gayed 2026 revision: French-market 2× trend 1928–2026, CAGR 16.19%; beta rotation on French
  portfolios 1926–2026, gross CAGR 12.98%.
- Antonacci: GEM 1974–2015 from his blog table, using the data available.
- Faber: S&P timing 1926–2012, from his decade table.

Any mismatch is reported and explained before going further.

## 8. Decisions taken before committing (2026-11-13)

1. **Cash:** T-bill return minus 0.15% a year as the main case; 0% as a sensitivity.
2. **Currency:** USD; EUR unhedged as an appendix (Tier C only).
3. **S5 exposure:** capped at 100% as the main case; 200% (the paper's) and 300% as sensitivities.
4. **S6:** published universe as the primary test; leveraged variant S6-L as secondary.

## 9. European retail implementation (descriptive, Tier C)

- **What is buyable:** EU retail investors cannot buy US-domiciled ETFs. For each strategy, list
  the UCITS products available: S&P 500 / MSCI USA, sector ETFs (11 US sectors exist as UCITS),
  leveraged 2× UCITS ETFs and 3× ETPs, gold ETCs, Treasury ETFs, overnight-rate ETFs.
- **Fees:** their ongoing charges versus the US funds used in the backtest.
- **Leveraged products:** 3× S&P 500 and 3× Nasdaq-100 exist for EU retail investors as ETPs
  (exchange-traded notes, not UCITS ETFs), and 2× versions exist as UCITS ETFs. Availability of a
  3× emerging-markets product is to be checked. Two consequences, both reported:
  - **Issuer risk:** an ETP is a debt security of its issuer, unlike a UCITS fund.
  - **Tax:** in Italy, gains on ETPs are "other income", so they can be offset by earlier losses,
    unlike gains on ETFs.
- **What can't be done:**
  - S5's 48 industries (only about 11 UCITS sectors exist);
  - S6's currency and inverse ETFs (only partly available).

## Changelog

**Implementation details the protocol left open, fixed before the first comparison run:**
- **End date:** every comparison ends on 2026-09-30, the last day of the T-bill series (ETF
  prices run later), so cash is the same in every tier.
- **S4 primary test:** 2× trend versus the unlevered market, the paper's own headline comparison.
- **S6 details:**
  - Higher TRank is better: high momentum, low volatility and low correlation get the high ranks.
  - Momentum and correlation use 84 trading days.
  - An asset enters the ranking once it has 504 days of history.
  - The paper's trend bands are ambiguous, so the trend factor is a breakout state (uptrend
    after a close above the previous day's upper band, downtrend after a close below the
    previous day's lower band, unchanged in between). An earlier informal implementation
    compared today's close with a band that included today's close, so "uptrend" could never
    occur.
- **Tier B (monthly data)** trades at the month-end close; next-day execution can't be
  represented with monthly data.
- **Tier C GEM** uses EFA for non-US stocks (from 2001; ACWX starts only in 2008) and AGG for
  bonds.
- **60/40 benchmark:** 30% US stocks, 30% non-US stocks, 40% bonds, rebalanced monthly.
- **Tier C GTAA-5:** SPY, EFA, IEF, GSG, VNQ.
- **S5 above 100% exposure:** borrowing at T-bill + 1%; the 1% leveraged-product fee is charged
  in proportion to the extra exposure, up to one unit.

**Fixed after the first comparison run (results before → after):**
- **S6 started in 2001, before any hedge ETF had 504 days of history**, so unused weight earned
  nothing until 2004. It now starts on 2004-07-30, when the hedge group can be ranked.
  - Full-sample Sharpe: 0.483 vs SPY 0.459 (2001 start) → 0.566 vs SPY 0.561 (2004 start).
  - Post-publication results unchanged.
- **The 25 bp cost sensitivity did not apply to the leveraged versions.** S4 2× at 25 bp: Sharpe
  0.535 → 0.343. Primary tests unaffected.
- **The 0% cash sensitivity compared S4 2× with the unlevered market** instead of constant 2×.
  Labelling only; primary tests unaffected.

**Replication added:** the Industry Trends paper's ETF section (2005–2024) reproduces exactly:
Sharpe 0.61 (paper 0.61), drawdown −23% (paper −24%).

**Descriptive analyses, implemented after the main results** (these do not affect the primary
tests):
- **Crash returns.**
- **Italian tax:** weighted-average cost; ETF gains taxed at sale with no loss offset; ETP/ETC
  gains offset by losses from the previous 4 years; 26%, and 12.5% on Treasury ETFs.
- **EUR appendix:** from 1999, Sharpe ratio against the euro-area 3-month rate (FRED
  IR3TIB01EZM156N).
- **UCITS product table.**

No rule was changed after results were seen.
