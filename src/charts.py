"""
README figures.

    python src/charts.py     # -> results/fig_century.png, fig_tests.png, fig_tax.png
"""
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import bench as BN  # noqa: E402
import config as C  # noqa: E402
import data as D  # noqa: E402
import engine as E  # noqa: E402

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]   # validated categorical slots 1-4
MARKET = "#8a8a85"
INK, MUTED, GRID = "#1f1f1e", "#6b6b66", "#e6e6e3"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
                     "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.titlecolor": INK, "axes.titlesize": 11, "axes.titleweight": "bold",
                     "figure.facecolor": "white", "axes.facecolor": "white"})


def _clean(ax):
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.tick_params(length=0)


def century():
    m = D.french_market()
    m = m[m.index <= BN.END]
    ind = D.french_industries()
    ind = ind[ind.index <= BN.END]
    res = BN.tier_a(m, ind)
    start = "1928-01-01"
    series = [("US market (buy and hold)", m.mkt, MARKET),
              ("S1 Faber 10-month average", res["S1 Faber US"][0], SERIES[0]),
              ("S4 200-day average, 1x", res["S4 Trend 1x"][0], SERIES[1]),
              ("S5 Industry trends", res["S5 Industry trend cap 100%"][0], SERIES[2]),
              ("S3 Beta rotation", res["S3 Beta rotation"][0], SERIES[3])]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True,
                                 gridspec_kw={"height_ratios": [2.2, 1]})
    ends = []
    for name, r, col in series:
        r = r[r.index >= start]
        w = E.wealth(r)
        lw = 2.4 if "market" in name else 1.6
        a1.plot(w, color=col, lw=lw)
        ends.append([np.log10(w.iloc[-1]), name, w.index[-1]])
        dd = w / w.cummax() - 1
        if "market" in name or "S4" in name:
            a2.plot(dd * 100, color=col, lw=1.4 if "S4" in name else 1.8)
    ends.sort()                                   # spread end labels at least 0.17 log10 apart
    for k in range(1, len(ends)):
        ends[k][0] = max(ends[k][0], ends[k - 1][0] + 0.17)
    for y, name, x in ends:
        a1.text(x + pd.Timedelta(days=500), 10 ** y, name, color=INK, fontsize=9, va="center")
    a1.set_yscale("log")
    a1.set_ylabel("Growth of $1 (log scale)")
    a1.set_title("A century of the same rules, after costs (1928 - Sep 2026)", loc="left")
    a2.set_ylabel("Fall from previous peak, %")
    a2.set_title("Drawdowns: the market vs the 200-day rule", loc="left")
    a2.text(pd.Timestamp("1933-06-01"), -86, "market", color=MUTED, fontsize=9)
    a2.text(pd.Timestamp("1933-06-01"), -32, "200-day rule", color=MUTED, fontsize=9)
    for a in (a1, a2):
        _clean(a)
    a1.set_xlim(pd.Timestamp(start), pd.Timestamp("2048-01-01"))
    fig.tight_layout()
    fig.savefig(C.RESULTS / "fig_century.png", dpi=150)


def tests():
    p = pd.read_csv(C.RESULTS / "primary_tests.csv")
    p["key"] = p.test.str[:2]
    names = {"S1": "S1 Faber", "S2": "S2 Dual momentum", "S3": "S3 Beta rotation",
             "S4": "S4 200-day, 2x", "S5": "S5 Industry trends", "S6": "S6 Antifragile"}
    fig, ax = plt.subplots(figsize=(9, 4.6))
    keys = list(names)
    for j, (period, col, off) in enumerate((("full", SERIES[0], -0.15),
                                            ("post-publication", SERIES[1], 0.15))):
        q = p[p.test.str.endswith(period)].set_index("key").loc[keys]
        y = np.arange(len(keys))[::-1] + off
        ax.hlines(y, q.ci_low, q.ci_high, color=col, lw=2)
        ax.plot(q["diff"], y, "o", color=col, ms=8, mec="white", mew=2,
                label="whole history" if period == "full" else "after publication")
    ax.axvline(0, color=INK, lw=1)
    ax.set_yticks(np.arange(len(keys))[::-1], [names[k] for k in keys])
    ax.set_xlabel("Sharpe ratio of the strategy minus Sharpe ratio of its benchmark "
                  "(dot = estimate, line = 95% range)")
    ax.set_title("Does timing beat holding? Right of zero = better", loc="left")
    ax.legend(frameon=False, loc="upper left")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.tick_params(length=0)
    fig.tight_layout()
    fig.savefig(C.RESULTS / "fig_tests.png", dpi=150)


def taxes():
    t = pd.read_csv(C.RESULTS / "tax.csv")
    fig, ax = plt.subplots(figsize=(9, 5))
    y = np.arange(len(t))[::-1]
    for off, pre, post, col, lab in ((0.17, "strategy_cagr_pre_tax", "strategy_cagr_after_tax",
                                      SERIES[0], "strategy"),
                                     (-0.17, "benchmark_cagr_pre_tax",
                                      "benchmark_cagr_after_tax", MARKET, "buy and hold")):
        ax.hlines(y + off, t[post] * 100, t[pre] * 100, color=col, lw=2)
        ax.plot(t[pre] * 100, y + off, "o", ms=8, mfc="white", mec=col, mew=2)
        ax.plot(t[post] * 100, y + off, "o", ms=8, color=col, mec="white", mew=2, label=lab)
    ax.set_yticks(y, t.strategy)
    ax.set_xlabel("Return per year, %  (hollow = before tax, filled = after Italian tax)")
    ax.set_title("Frequent exits are taxed every time: ETF versions, Italian investor",
                 loc="left")
    ax.legend(frameon=False, loc="lower right")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.tick_params(length=0)
    fig.tight_layout()
    fig.savefig(C.RESULTS / "fig_tax.png", dpi=150)


if __name__ == "__main__":
    century()
    tests()
    taxes()
