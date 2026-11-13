"""
Italian tax for a retail investor (PROTOCOL section 5), on the ETF versions (Tier C).

Rules modelled (simplified; not tax advice):
  * Gains on UCITS ETFs are "capital income" (redditi di capitale): taxed when sold, and
    earlier losses cannot be set against them.
  * Gains and losses on ETPs/ETCs (leveraged notes, gold, currency notes) are "other income"
    (redditi diversi): gains are first offset by losses carried forward from the previous
    4 years, the rest is taxed.
  * Losses on ETFs are also "other income": they are carried forward for 4 years, but can
    only be used against ETP/ETC gains.
  * Rate 26%; 12.5% on government bond ETFs. Cost basis = weighted average cost.
  * Buy-and-hold pays tax only when the position is sold at the end.
Taxes are paid from the portfolio on the day of the sale.
"""
import numpy as np
import pandas as pd

YEARS_CARRY = 4


def run_taxed(targets, rets, regime, rate, lag=2, cost=0.0005, cost_map=None):
    """After-tax wealth path, and final wealth after selling everything.

    targets : decision date x asset target weights (sum 1)
    rets    : daily returns (columns include all target assets)
    regime  : asset -> 'etf' or 'etp';  rate : asset -> tax rate"""
    cols = list(targets.columns)
    R = rets[cols].fillna(0.0).values
    idx = rets.index
    pos_of = {d: idx.get_indexer([d], method="pad")[0] for d in targets.index}
    exec_rows = {min(p + lag - 1, len(idx) - 1): d for d, p in pos_of.items() if p >= 0}
    c = np.array([(cost_map or {}).get(a, cost) for a in cols])
    is_etp = np.array([regime.get(a, "etf") == "etp" for a in cols])
    rt = np.array([rate.get(a, 0.26) for a in cols])
    V = None
    B = np.zeros(len(cols))
    carry = []                                         # [(expiry_date, amount)]
    wealth = np.full(len(idx), np.nan)
    taxes_paid = 0.0

    def realise(gain, i, day):
        nonlocal carry
        carry = [(e, a) for e, a in carry if e >= day and a > 0]
        if gain < 0:
            carry.append((day + pd.DateOffset(years=YEARS_CARRY), -gain))
            return 0.0
        if is_etp[i]:
            for k, (e, a) in enumerate(carry):
                use = min(a, gain)
                gain -= use
                carry[k] = (e, a - use)
                if gain <= 0:
                    break
        return rt[i] * max(gain, 0.0)

    for t in range(len(idx)):
        if V is not None:
            V = V * (1 + R[t])
            wealth[t] = V.sum()
        if t in exec_rows:
            w = targets.loc[exec_rows[t]].values.astype(float)
            if V is None:
                V = w * (1 - (w * c).sum())
                B = V.copy()
                wealth[t] = V.sum()
                continue
            W = V.sum()
            trade_cost = float((np.abs(w * W - V) * c).sum())
            tax = 0.0
            for i in range(len(cols)):
                sell = V[i] - w[i] * W
                if sell > 1e-12 and V[i] > 0:
                    basis_out = B[i] * sell / V[i]
                    tax += realise(sell - basis_out, i, idx[t])
                    B[i] -= basis_out
                    V[i] -= sell
            W_after = W - tax - trade_cost
            taxes_paid += tax
            newV = w * W_after
            for i in range(len(cols)):
                if newV[i] > V[i]:
                    B[i] += newV[i] - V[i]
                elif V[i] > 0:
                    B[i] *= newV[i] / V[i]
            V = newV
            wealth[t] = V.sum()
    s = pd.Series(wealth, index=idx).dropna()
    # final sale
    final_tax = 0.0
    for i in range(len(cols)):
        if V[i] > 0:
            final_tax += realise(V[i] - B[i], i, idx[-1])
    return s, float(V.sum() - final_tax), taxes_paid + final_tax
