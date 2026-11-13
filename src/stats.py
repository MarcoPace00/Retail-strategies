"""Primary-test statistics (PROTOCOL section 6)."""
import numpy as np
import pandas as pd


def sharpe_diff_bootstrap(strat, bench, rf, block, n_boot=5000, ann=252, seed=20261113):
    """Paired circular block bootstrap of Sharpe(strategy) - Sharpe(benchmark).

    Both excess-return series are resampled with the same blocks of `block` observations
    (one year), keeping their dependence. Returns the observed difference, a 95% interval
    and the one-sided p-value P(difference <= 0) under the bootstrap distribution."""
    df = pd.concat({"s": strat, "b": bench, "rf": rf}, axis=1).dropna()
    xs = (df.s - df.rf).values
    xb = (df.b - df.rf).values
    T = len(xs)
    k = int(np.ceil(T / block))

    def prefix(v):
        v2 = np.concatenate([v, v[:block]])
        return np.concatenate([[0.0], np.cumsum(v2)])

    P = [prefix(v) for v in (xs, xs ** 2, xb, xb ** 2)]
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, T, size=(n_boot, k))
    sums = [p[starts + block] - p[starts] for p in P]       # block sums, (n_boot, k)
    n = k * block
    ms, m2s, mb, m2b = (s.sum(1) / n for s in sums)
    sh_s = ms / np.sqrt(m2s - ms ** 2) * np.sqrt(ann)
    sh_b = mb / np.sqrt(m2b - mb ** 2) * np.sqrt(ann)
    d = sh_s - sh_b
    obs = xs.mean() / xs.std() * np.sqrt(ann) - xb.mean() / xb.std() * np.sqrt(ann)
    return {"n_obs": T, "sharpe_strategy": xs.mean() / xs.std() * np.sqrt(ann),
            "sharpe_benchmark": xb.mean() / xb.std() * np.sqrt(ann), "diff": obs,
            "ci_low": float(np.percentile(d, 2.5)), "ci_high": float(np.percentile(d, 97.5)),
            "p_one_sided": float((d <= 0).mean())}


def holm(pvals):
    """Holm step-down adjusted p-values (same order as input)."""
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * p[i])
        adj[i] = min(running, 1.0)
    return adj
