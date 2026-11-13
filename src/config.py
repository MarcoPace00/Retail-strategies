"""Every number fixed by PROTOCOL.md, in one place."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CACHE = ROOT / "data" / "cache"
RESULTS = ROOT / "results"

FRENCH_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/{}.zip"
FRENCH_FILES = {
    "factors": "F-F_Research_Data_Factors_daily_CSV",
    "ind48": "48_Industry_Portfolios_daily_CSV",
}

# test bench (PROTOCOL section 4)
CASH_FEE = 0.0015              # T-bill return minus 0.15% a year
COST_ETF = 0.0005              # 5 bp per one-way trade
COST_LEVERAGED = 0.0010        # 10 bp for leveraged products
LEV_SPREAD = 0.01              # borrowing = T-bill + 1%
LEV_FEE = 0.01                 # 1% annual fee on leveraged products
ANN = 252
