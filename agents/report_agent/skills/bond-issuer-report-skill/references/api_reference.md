# Data API Reference

Base URL: configured via environment variable `API_BASE_URL` (default: `http://localhost:8000`).

All endpoints require `Authorization: Bearer <token>`.

---

## GET /api/data/issuers

List all available issuers.

**Response** `200 OK`
```json
[
  {"id": "AAPL", "name": "Apple Inc.", "sector": "Technology", "country": "US", "ticker": "AAPL"},
  {"id": "MSFT", "name": "Microsoft Corporation", "sector": "Technology", "country": "US", "ticker": "MSFT"}
]
```

---

## GET /api/data/issuers/{issuer_id}

Full data bundle for one issuer. Returns everything in a single call.

**Response** `200 OK`
```json
{
  "issuer": {"id": "AAPL", "name": "Apple Inc.", "sector": "Technology", "country": "US", "ticker": "AAPL"},
  "rating_history": [{"date": "2024-09-15", "rating": "AA", "agency": "S&P", "outlook": "Stable"}],
  "pd_data": {
    "current_curve": [{"tenor": 1, "pd": 0.0002}],
    "historical": [{"date": "2024-01-15", "pd_1y": 0.0002, "pd_5y": 0.0006}]
  },
  "financials": [{"year": 2024, "revenue": 394000000000, "net_income": 97000000000, "total_assets": 352000000000, "total_debt": 111000000000, "equity": 62000000000, "ebitda": 130000000000, "interest_expense": 3900000000, "cash": 48000000000, "operating_cf": 110000000000}],
  "bonds": [{"isin": "USAAPL000", "coupon": 2.5, "maturity": "2026-06-15", "face_value": 1000, "currency": "USD", "issue_size_mm": 500, "price": 98.5, "ytm": 3.8, "spread_bps": 65, "modified_duration": 3.2}],
  "spread_history": [{"date": "2024-01-15", "spread_bps": 52.3}],
  "risk_decomposition": {
    "contributions_pct": {"macro_economy": 18.2, "industry_risk": 14.5, "leverage": 22.1, "profitability": 15.8, "liquidity": 10.3, "market_sentiment": 11.4, "country_risk": 7.7},
    "trend_6m": {"macro_economy": 1.2, "industry_risk": -0.8, "leverage": 2.5, "profitability": -1.3, "liquidity": 0.4, "market_sentiment": 3.1, "country_risk": -0.5}
  },
  "peer_comparison": [{"issuer_id": "AAPL", "name": "Apple Inc.", "rating": "AA", "leverage": 0.85, "interest_coverage": 33.33, "profit_margin_pct": 24.6, "debt_to_equity": 1.79}]
}
```

---

## GET /api/data/issuers/{issuer_id}/ratings

Credit rating history.

**Response** `200 OK`
```json
[
  {"date": "2018-01-15", "rating": "AAA", "agency": "S&P", "outlook": "Stable"},
  {"date": "2020-06-01", "rating": "AA+", "agency": "S&P", "outlook": "Negative"},
  {"date": "2024-09-15", "rating": "AA", "agency": "S&P", "outlook": "Stable"}
]
```

---

## GET /api/data/issuers/{issuer_id}/pd

PD term structure (current) and historical PD (24 monthly points).

**Response** `200 OK`
```json
{
  "current_curve": [
    {"tenor": 0.5, "pd": 0.00015},
    {"tenor": 1, "pd": 0.0002},
    {"tenor": 5, "pd": 0.0005},
    {"tenor": 10, "pd": 0.001}
  ],
  "historical": [
    {"date": "2022-03-15", "pd_1y": 0.00018, "pd_5y": 0.00055},
    {"date": "2024-01-15", "pd_1y": 0.0002, "pd_5y": 0.0006}
  ]
}
```

Note: PD values are raw decimals. Multiply by 100 to display as percentages.

---

## GET /api/data/issuers/{issuer_id}/financials

Annual financial statements (4 years).

**Response** `200 OK`
```json
[
  {
    "year": 2024,
    "revenue": 394000000000,
    "net_income": 97000000000,
    "total_assets": 352000000000,
    "total_debt": 111000000000,
    "equity": 62000000000,
    "ebitda": 130000000000,
    "interest_expense": 3900000000,
    "cash": 48000000000,
    "operating_cf": 110000000000
  }
]
```

Note: All values are in absolute dollars (not billions). Divide by 1e9 for display.

---

## GET /api/data/issuers/{issuer_id}/bonds

Outstanding bond portfolio.

**Response** `200 OK`
```json
[
  {
    "isin": "USAAPL000",
    "coupon": 2.5,
    "maturity": "2026-06-15",
    "face_value": 1000,
    "currency": "USD",
    "issue_size_mm": 500,
    "price": 98.5,
    "ytm": 3.8,
    "spread_bps": 65,
    "modified_duration": 3.2
  }
]
```

---

## GET /api/data/issuers/{issuer_id}/spreads

Daily credit spread history (365 data points).

**Response** `200 OK`
```json
[
  {"date": "2023-03-28", "spread_bps": 52.3},
  {"date": "2023-03-29", "spread_bps": 53.1}
]
```

For charts, sample every 7th point (weekly) to keep it readable.

---

## GET /api/data/issuers/{issuer_id}/risk-decomposition

Risk factor breakdown with 6-month trends.

**Response** `200 OK`
```json
{
  "contributions_pct": {
    "macro_economy": 18.2,
    "industry_risk": 14.5,
    "leverage": 22.1,
    "profitability": 15.8,
    "liquidity": 10.3,
    "market_sentiment": 11.4,
    "country_risk": 7.7
  },
  "trend_6m": {
    "macro_economy": 1.2,
    "industry_risk": -0.8,
    "leverage": 2.5,
    "profitability": -1.3,
    "liquidity": 0.4,
    "market_sentiment": 3.1,
    "country_risk": -0.5
  }
}
```

Positive trend values = worsening (risk increasing). Negative = improving.

---

## GET /api/data/issuers/{issuer_id}/peers

Peer comparison metrics.

**Response** `200 OK`
```json
[
  {"issuer_id": "AAPL", "name": "Apple Inc.", "rating": "AA", "leverage": 0.85, "interest_coverage": 33.33, "profit_margin_pct": 24.6, "debt_to_equity": 1.79},
  {"issuer_id": "MSFT", "name": "Microsoft Corporation", "rating": "AAA", "leverage": 0.76, "interest_coverage": 47.62, "profit_margin_pct": 34.1, "debt_to_equity": 0.38}
]
```

The target issuer is always included as the first entry.

---

## Authentication

All endpoints use Bearer token auth:

```
Authorization: Bearer <jwt_token>
```

To obtain a token:

```
POST /api/agent/token
Content-Type: application/json

{"username": "analyst", "password": "analyst123"}
```

Response: `{"access_token": "eyJ...", "token_type": "bearer"}`

---

## Mock Mode

When the backend environment variable `USE_MOCK=true` (default), all endpoints return deterministic mock data without needing a database. Available mock issuers: AAPL, MSFT, JPM, TSLA, GS.
