"""Deterministic mock data for all issuer data APIs.

Used when USE_MOCK=True. Each function returns the same shape
that the real backend API would return.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import Any

ISSUERS: dict[str, dict[str, str]] = {
    "AAPL": {"name": "Apple Inc.", "sector": "Technology", "country": "US", "ticker": "AAPL"},
    "MSFT": {"name": "Microsoft Corporation", "sector": "Technology", "country": "US", "ticker": "MSFT"},
    "JPM":  {"name": "JPMorgan Chase & Co.", "sector": "Financials", "country": "US", "ticker": "JPM"},
    "TSLA": {"name": "Tesla Inc.", "sector": "Consumer Discretionary", "country": "US", "ticker": "TSLA"},
    "GS":   {"name": "Goldman Sachs Group", "sector": "Financials", "country": "US", "ticker": "GS"},
}

def _su(iid: str, salt: str, lo: float, hi: float) -> float:
    h = hashlib.md5(f"{iid}{salt}".encode()).hexdigest()
    return lo + (int(h[:8], 16) / 0xFFFFFFFF) * (hi - lo)

_RATINGS = {
    "AAPL": [("2018-01-15","AAA","S&P","Stable"),("2020-06-01","AA+","S&P","Negative"),("2022-03-10","AA+","Moody's","Stable"),("2024-09-15","AA","S&P","Stable")],
    "MSFT": [("2017-05-01","AAA","S&P","Stable"),("2019-11-20","AAA","Fitch","Stable"),("2022-01-05","AAA","S&P","Stable"),("2024-07-01","AAA","Moody's","Stable")],
    "JPM":  [("2018-03-10","A+","S&P","Stable"),("2020-04-15","A","S&P","Negative"),("2021-12-01","A+","Moody's","Positive"),("2024-06-20","A+","S&P","Positive")],
    "TSLA": [("2019-08-01","BB-","S&P","Stable"),("2021-02-15","BB","Fitch","Positive"),("2023-01-10","BB+","S&P","Positive"),("2024-11-01","BBB-","S&P","Positive")],
    "GS":   [("2018-06-01","A","S&P","Stable"),("2020-05-10","A-","S&P","Negative"),("2022-08-15","A","Moody's","Stable"),("2024-04-01","A","S&P","Stable")],
}
_BASE_PD = {"AAPL": 0.0002, "MSFT": 0.0001, "JPM": 0.0005, "TSLA": 0.0015, "GS": 0.0004}
_BASE_SPREAD = {"AAPL": 55, "MSFT": 45, "JPM": 80, "TSLA": 200, "GS": 75}
_FIN = {
    "AAPL": dict(revenue=394e9,net_income=97e9,total_assets=352e9,total_debt=111e9,equity=62e9,ebitda=130e9,interest_expense=3.9e9,cash=48e9,operating_cf=110e9),
    "MSFT": dict(revenue=211e9,net_income=72e9,total_assets=411e9,total_debt=78e9,equity=206e9,ebitda=100e9,interest_expense=2.1e9,cash=104e9,operating_cf=89e9),
    "JPM":  dict(revenue=154e9,net_income=49e9,total_assets=3740e9,total_debt=450e9,equity=303e9,ebitda=70e9,interest_expense=25e9,cash=580e9,operating_cf=55e9),
    "TSLA": dict(revenue=97e9,net_income=7.9e9,total_assets=106e9,total_debt=5.6e9,equity=53e9,ebitda=14e9,interest_expense=0.5e9,cash=26e9,operating_cf=13e9),
    "GS":   dict(revenue=47e9,net_income=11e9,total_assets=1570e9,total_debt=280e9,equity=116e9,ebitda=18e9,interest_expense=15e9,cash=240e9,operating_cf=14e9),
}

def list_issuers() -> list[dict]:
    return [{"id": k, **v} for k, v in ISSUERS.items()]

def get_rating_history(iid: str) -> list[dict]:
    path = _RATINGS.get(iid.upper(), _RATINGS["AAPL"])
    return [{"date": d, "rating": r, "agency": a, "outlook": o} for d, r, a, o in path]

def get_pd_data(iid: str) -> dict:
    iid = iid.upper(); bp = _BASE_PD.get(iid, 0.0005)
    tenors = [0.5, 1, 2, 3, 5, 7, 10]
    curve = [{"tenor": t, "pd": round(bp * (1 + 0.35 * t), 6)} for t in tenors]
    today = datetime.now()
    hist = [{"date": (today - timedelta(days=30*(23-m))).strftime("%Y-%m-%d"),
             "pd_1y": round(bp + _su(iid, f"ph1{m}", -0.0001, 0.0001), 6),
             "pd_5y": round(bp * 2.8 + _su(iid, f"ph5{m}", -0.0003, 0.0003), 6)} for m in range(24)]
    return {"current_curve": curve, "historical": hist}

def get_financials(iid: str) -> list[dict]:
    iid = iid.upper(); base = _FIN.get(iid, _FIN["AAPL"])
    return [{"year": yr, **{k: round(v * (1 + 0.05*(i-1) + _su(iid, f"f{yr}", -0.02, 0.02)))
             for k, v in base.items()}} for i, yr in enumerate([2021, 2022, 2023, 2024])]

def get_bonds(iid: str) -> list[dict]:
    iid = iid.upper(); coupons = [2.5, 3.0, 3.75, 4.25, 5.0, 5.5]
    return [{"isin": f"US{iid}{i:03d}", "coupon": coupons[i], "maturity": f"{2026+i*2}-06-15",
             "face_value": 1000, "currency": "USD", "issue_size_mm": [500,750,1000,1500,2000,1000][i],
             "price": round(95+_su(iid,f"bp{i}",0,13),2), "ytm": round(3.5+_su(iid,f"by{i}",0,3),3),
             "spread_bps": round(40+_su(iid,f"bs{i}",0,210)), "modified_duration": round(1.5+_su(iid,f"bd{i}",0,10.5),2)
             } for i in range(6)]

def get_spread_history(iid: str) -> list[dict]:
    iid = iid.upper(); s = _BASE_SPREAD.get(iid, 80); today = datetime.now()
    hist = []
    for d in range(365):
        dt = today - timedelta(days=364 - d)
        s += _su(iid, f"sp{d}", -3, 3); s = max(20, s)
        hist.append({"date": dt.strftime("%Y-%m-%d"), "spread_bps": round(s, 1)})
    return hist

def get_risk_decomposition(iid: str) -> dict:
    iid = iid.upper()
    raw = {"macro_economy": 10+_su(iid,"r0",0,15), "industry_risk": 8+_su(iid,"r1",0,12),
           "leverage": 12+_su(iid,"r2",0,18), "profitability": 8+_su(iid,"r3",0,12),
           "liquidity": 5+_su(iid,"r4",0,10), "market_sentiment": 6+_su(iid,"r5",0,9),
           "country_risk": 2+_su(iid,"r6",0,8)}
    total = sum(raw.values())
    return {"contributions_pct": {k: round(v/total*100, 1) for k, v in raw.items()},
            "trend_6m": {k: round(_su(iid, f"rt{k}", -5, 5), 1) for k in raw}}

def get_peer_comparison(iid: str) -> list[dict]:
    iid = iid.upper()
    result = []
    for pid in [iid] + [p for p in ISSUERS if p != iid]:
        pf = _FIN.get(pid, _FIN["AAPL"]); pr = _RATINGS.get(pid, _RATINGS["AAPL"])
        result.append({"issuer_id": pid, "name": ISSUERS[pid]["name"], "rating": pr[-1][1],
                        "leverage": round(pf["total_debt"]/pf["ebitda"], 2),
                        "interest_coverage": round(pf["ebitda"]/pf["interest_expense"], 2),
                        "profit_margin_pct": round(pf["net_income"]/pf["revenue"]*100, 1),
                        "debt_to_equity": round(pf["total_debt"]/pf["equity"], 2)})
    return result

def get_issuer_full(iid: str) -> dict[str, Any] | None:
    iid = iid.upper()
    if iid not in ISSUERS:
        return None
    return {"issuer": {**ISSUERS[iid], "id": iid}, "rating_history": get_rating_history(iid),
            "pd_data": get_pd_data(iid), "financials": get_financials(iid), "bonds": get_bonds(iid),
            "spread_history": get_spread_history(iid), "risk_decomposition": get_risk_decomposition(iid),
            "peer_comparison": get_peer_comparison(iid)}
