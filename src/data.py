"""
Data loaders. Raw files are downloaded once into data/raw (not committed: provider terms).

    python src/data.py          # download / refresh everything
"""
import io
import urllib.request
import zipfile

import numpy as np
import pandas as pd

import config as C


def _download(name):
    C.RAW.mkdir(parents=True, exist_ok=True)
    path = C.RAW / f"{name}.zip"
    if not path.exists():
        urllib.request.urlretrieve(C.FRENCH_URL.format(name), path)
    return path


def _french_table(name, section=0):
    """Parse one table of a Ken French daily CSV (section 0 = first table)."""
    z = zipfile.ZipFile(_download(name))
    lines = z.read(z.namelist()[0]).decode("latin1").splitlines()
    tables, cur = [], None
    for line in lines:
        s = line.strip()
        if s.startswith(",") and cur is None:
            cur = [line]
        elif cur is not None:
            if s and s[0].isdigit():
                cur.append(line)
            else:
                tables.append(cur)
                cur = None
    if cur:
        tables.append(cur)
    df = pd.read_csv(io.StringIO("\n".join(tables[section])), index_col=0)
    df.index = pd.to_datetime(df.index.astype(str).str.strip(), format="%Y%m%d")
    df.columns = [c.strip() for c in df.columns]
    df = df.replace([-99.99, -999], np.nan) / 100.0
    return df


def french_market():
    """Daily total return of the US market, and the daily 1-month T-bill return."""
    f = _french_table(C.FRENCH_FILES["factors"])
    return pd.DataFrame({"mkt": f["Mkt-RF"] + f["RF"], "rf": f["RF"]})


def french_industries():
    """Daily value-weighted total returns of the 48 industry portfolios (NaN = missing)."""
    return _french_table(C.FRENCH_FILES["ind48"], section=0)


def _download_url(url, fname):
    C.RAW.mkdir(parents=True, exist_ok=True)
    path = C.RAW / fname
    if not path.exists():
        urllib.request.urlretrieve(url, path)
    return path


def to_monthly(daily):
    """Compound daily returns into calendar-month returns (month-end index)."""
    m = (1 + daily).groupby(daily.index.to_period("M")).prod() - 1
    m.index = m.index.to_timestamp("M")
    return m


def french_intl_monthly():
    """Non-US developed markets, value-weighted USD total return, monthly from 1975.

    Ken French 'International Indices', file Ind_all, first table ('Mkt' column)."""
    path = _download_url(C.FRENCH_URL.format("F-F_International_Indices"),
                         "F-F_International_Indices.zip")
    z = zipfile.ZipFile(path)
    lines = z.read("Ind_all.Dat").decode("latin1").splitlines()
    rows = []
    for line in lines[4:]:
        parts = line.split()
        if not parts or not (parts[0].isdigit() and len(parts[0]) == 6):
            break
        rows.append((parts[0], float(parts[1])))
    s = pd.Series({pd.Period(d[:4] + "-" + d[4:], "M").to_timestamp("M"): v / 100
                   for d, v in rows})
    return s.replace(-0.9999, np.nan).rename("intl")


def fred(series):
    """Monthly FRED series (percent), month-end index."""
    path = _download_url(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}",
                         f"fred_{series}.csv")
    df = pd.read_csv(path, parse_dates=[0], index_col=0, na_values=".")
    s = df.iloc[:, 0].astype(float) / 100
    s.index = s.index.to_period("M").to_timestamp("M")
    return s.rename(series)


def bond_from_yield(y, maturity):
    """Monthly total return of a constant-maturity par bond rebought every month.

    Buy at par with coupon = last month's yield; one month later revalue the
    (maturity - 1/12)-year bond at the new yield (semi-annual coupons) and add the coupon."""
    y0, y1 = y.shift(1), y
    n = 2 * (maturity - 1 / 12)
    c = y0 / 2
    disc = (1 + y1 / 2)
    price = c / (y1 / 2) * (1 - disc ** (-n)) + disc ** (-n)
    return (price - 1 + y0 / 12).dropna().rename(f"bond{maturity}y")


ETF_TICKERS = sorted(set(
    "SPY VTI QQQ EFA ACWX AGG IEF TLT SHY BIL GSG DBC VNQ SSO UPRO TQQQ EDC "
    # Antifragile: sectors and hedges (paper, Tables 2 and 5)
    "XLY XLV XLU XLP XLK XLI XLF XLE XLB VOX RWR FXY FXF GLD SH "
    # Industry Trends ETF section (paper, Table 6)
    "XBI KRE XLC XRT XOP XLRE XHB KBE XME KIE XSD XAR XES KCE XNTK XHE XSW XPH XTN XHS "
    "XITK XTL".split()))
S5_ETFS = ("XLF XLK XLE XLV XLI XBI XLU XLP XLY KRE XLB XLC XRT XOP XLRE XHB KBE XME KIE "
           "XSD XAR XES KCE XNTK XHE XSW XPH XTN XHS XITK XTL").split()


def etf_prices(refresh=False):
    """Split- and dividend-adjusted daily OHLC for every ETF (Yahoo), cached."""
    C.CACHE.mkdir(parents=True, exist_ok=True)
    path = C.CACHE / "etf_ohlc.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)
    import yfinance as yf
    raw = yf.download(ETF_TICKERS, start="1993-01-01", auto_adjust=True, progress=False,
                      group_by="column", threads=True)
    out = raw[["Open", "High", "Low", "Close"]]
    out.index = pd.to_datetime(out.index).tz_localize(None)
    out.to_parquet(path)
    return out


def etf_returns():
    close = etf_prices()["Close"]
    return close.pct_change(fill_method=None).where(close.notna())


def eurusd():
    """USD per EUR, daily (FRED DEXUSEU, from 1999)."""
    path = _download_url("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXUSEU",
                         "fred_DEXUSEU.csv")
    df = pd.read_csv(path, parse_dates=[0], index_col=0, na_values=".")
    return df.iloc[:, 0].astype(float).rename("usd_per_eur")


if __name__ == "__main__":
    m = french_market()
    i = french_industries()
    print(m.index[0].date(), m.index[-1].date(), len(m))
    print(i.shape, i.index[-1].date(), int(i.notna().sum(1).iloc[0]), "industries on day one")
