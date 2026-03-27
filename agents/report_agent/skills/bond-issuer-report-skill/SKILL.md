---
name: bond-issuer-report-skill
description: Skill for generating credit analysis reports on bond issuers. Use this skill whenever the user asks to create, generate, or write an analysis report, credit report, issuer report, or risk assessment for a bond issuer or credit entity. Also trigger when the user mentions writing a report that involves credit ratings, probability of default, financial ratios, peer comparison, or risk decomposition — even if they don't call it a "credit report" explicitly. Covers requests like "analyze Apple's credit", "write a bond issuer report for TSLA", "give me a risk assessment of JPMorgan", or "create a report comparing this issuer to its peers".
---

# Bond Issuer Report Writing Skill

Generate self-contained HTML credit analysis reports for bond issuers. The agent fetches data through API calls, computes financial ratios locally, and produces a report with formatted tables and interactive Chart.js charts.

The report structure is flexible — there is a default template, but the user can request a different structure, add sections, remove sections, or change the analytical focus.

## Workflow

1. **Identify the issuer** from the user's request.
2. **Determine report sections** — use the default structure (§1) unless the user specifies something different.
3. **Fetch data** by calling the data APIs listed in §2. Call all the endpoints you need before writing.
4. **Compute credit ratios** locally from financial data (§3). These are simple calculations — do them yourself, no API needed.
5. **Write the HTML report** following the formatting rules in §4–§6.
6. **Return** the complete HTML string.

---

## 1. Default Report Structure

Use this structure when the user doesn't specify something custom. Each section maps to specific data sources and visual elements.

### Section 1: Executive Summary

A high-level snapshot with KPI cards and a short narrative paragraph.

**Data needed:** issuer profile, latest credit rating, latest 1Y PD, bond portfolio stats, latest-year financials.

**Visual elements:**
- 3–5 KPI cards in a grid (issuer name/sector, current rating badge, 1Y PD, bonds outstanding, a key ratio)
- One prose paragraph summarising the issuer's credit position

### Section 2: Temporal and Peer Comparison

How the issuer's risk has evolved over time, and how it stacks up against peers.

**Data needed:** credit rating history, credit spread history (12 months), historical PD (1Y and 5Y, 24 months), peer comparison metrics.

**Visual elements:**
- Rating history timeline (date + badge + agency/outlook per entry)
- Credit spread line chart (weekly-sampled from daily data)
- Historical PD line chart (1Y and 5Y series)
- Peer comparison table (issuer highlighted)

The temporal view answers "is this issuer getting riskier or safer?" The peer view answers "relative to similar companies, where does it sit?"

### Section 3: Risk Decomposition with Fundamental Analysis

Break down what drives the issuer's risk, grounded in financial fundamentals.

**Data needed:** risk factor decomposition (contributions + 6-month trends), annual financial statements (4 years), computed credit ratios.

**Visual elements:**
- Risk factor doughnut chart (contributions by factor)
- Risk factor trend horizontal bar chart (6M changes, red=worsening, green=improving)
- Risk factor detail table (factor name, contribution %, 6M trend with arrow)
- Financial summary table (revenue, net income, EBITDA, debt, cash by year)
- Revenue & profitability grouped bar chart
- Credit ratio line chart (interest coverage, net leverage, D/E)

This section connects the abstract risk factors to the concrete financial numbers behind them.

### Section 4: Summary and Recommendation

Synthesise findings into an actionable assessment.

**Visual elements:**
- Risk-level banner (LOW / MODERATE / ELEVATED) with explanatory text
- Key findings bullet list
- Worsening/improving factor callouts
- Disclaimer

**Risk level heuristic** (adapt based on data):
- LOW RISK: coverage > 10x, net leverage < 2x, 1Y PD < 0.5%
- MODERATE RISK: coverage > 4x, net leverage < 5x, 1Y PD < 1.5%
- ELEVATED RISK: everything else

### Adapting the structure

The user might request changes. Examples:

- *"Add a bond portfolio section"* → insert a section with bond details table (ISIN, coupon, maturity, price, YTM, spread, duration) from `get_bonds`.
- *"Skip the peer comparison"* → drop the peer table/chart from section 2 but keep the temporal analysis.
- *"Just give me an executive summary"* → produce only section 1 in extended form.
- *"Focus on the financials"* → expand section 3, minimise or drop sections 2 and 4.
- *"Use a different structure: overview, credit metrics, recommendation"* → follow their outline, map each section to relevant data.

Always number sections sequentially based on what's actually included.

---

## 2. Data APIs

Fetch data by calling these endpoints. The base URL and auth token come from your environment. Every endpoint requires `Authorization: Bearer <token>`.

Read `references/api_reference.md` for the full endpoint specifications, request/response schemas, and example payloads.

**Quick reference:**

| Endpoint | Returns | Used for |
|----------|---------|----------|
| `GET /api/data/issuers` | List of all issuers | Resolving issuer names |
| `GET /api/data/issuers/{id}` | Full issuer data bundle | One-shot fetch of everything |
| `GET /api/data/issuers/{id}/ratings` | Rating history | Temporal analysis |
| `GET /api/data/issuers/{id}/pd` | PD term structure + history | Credit risk charts |
| `GET /api/data/issuers/{id}/financials` | Annual financial statements | Fundamental analysis |
| `GET /api/data/issuers/{id}/bonds` | Bond portfolio | Portfolio section |
| `GET /api/data/issuers/{id}/spreads` | 12-month daily spreads | Spread chart |
| `GET /api/data/issuers/{id}/risk-decomposition` | Factor contributions + trends | Risk decomposition |
| `GET /api/data/issuers/{id}/peers` | Peer comparison table | Peer analysis |

When the backend is in mock mode (`USE_MOCK=true`), these endpoints return deterministic mock data. No database needed.

---

## 3. Local Ratio Computations

Compute these from the financial statements yourself — they're simple arithmetic and don't need an API call.

**From financials:**
- Interest Coverage = EBITDA ÷ Interest Expense
- Net Leverage = (Total Debt − Cash) ÷ EBITDA
- Debt-to-Equity = Total Debt ÷ Equity
- Profit Margin % = Net Income ÷ Revenue × 100
- Debt-to-Assets = Total Debt ÷ Total Assets

**From bond portfolio:**
- Number of bonds = count
- Total outstanding ($M) = sum of issue_size_mm
- Weighted avg coupon = Σ(coupon × issue_size_mm) ÷ Σ(issue_size_mm)
- Weighted avg duration = Σ(modified_duration × issue_size_mm) ÷ Σ(issue_size_mm)

---

## 4. HTML Output Format

The report is a single self-contained HTML file. It loads Chart.js from CDN and Google Fonts (DM Sans + JetBrains Mono). No other external dependencies.

Read `references/html_format.md` for the complete CSS, component patterns, and chart configuration templates.

**Critical rules:**
- The HTML must include a working light/dark theme toggle. Use CSS custom properties (`var(--bg1)`, `var(--tx1)`, etc.) throughout — never hardcode colours for text, backgrounds, or chart elements.
- Every `<canvas>` for a chart must have a unique `id`.
- Every chart `<script>` must be wrapped in an IIFE: `(()=>{ ... })();`
- Chart axis labels, ticks, and gridlines must use CSS variable colours so they adapt to the theme.
- Financial values: `$XXX.XB` for billions, `$XXX.XM` for millions.
- PD values: multiply raw values by 100 and display as `X.XXX%`.
- Ratios: `X.XXx` format.
- For spread history, sample every 7th data point to keep the chart readable.

Use the CSS from `assets/report_styles.css` — include it verbatim inside the `<style>` tag. This handles the theme variables, typography, KPI cards, tables, chart containers, rating badges, timelines, and responsive layout.

---

## 5. Component Patterns

### KPI cards
```html
<div class="kpi-grid">
  <div class="kpi">
    <div class="kpi-label">LABEL</div>
    <div class="kpi-value">VALUE</div>
    <div class="kpi-sub">Secondary info</div>
  </div>
</div>
```

### Rating badges
Colour-coded spans: AAA–AA range = teal, A range = blue, BBB range = amber, BB–B range = orange/red.
```html
<span class="rating-badge" style="background:#14b8a6">AA</span>
```

### Rating timeline
```html
<div class="rating-timeline">
  <div class="tl-item">
    <span class="tl-date">2024-09-15</span>
    <span class="rating-badge" style="background:#14b8a6">AA</span>
    <span class="tl-meta">S&P · Stable</span>
  </div>
</div>
```

### Tables
```html
<div class="tbl-wrap">
  <table>
    <thead><tr><th>Col</th></tr></thead>
    <tbody><tr><td>Val</td></tr></tbody>
  </table>
</div>
```
Use `class="hl"` on `<tr>` to highlight the target issuer in peer tables.

### Recommendation banner
```html
<div class="rec-banner" style="border-left:4px solid #10b981">
  <div class="rec-level" style="color:#10b981">LOW RISK</div>
  <p>Assessment text.</p>
</div>
```

### Charts
```html
<div class="chart-box"><canvas id="uniqueId"></canvas></div>
<script>
(()=>{
  new Chart(document.getElementById('uniqueId'), {
    type: 'line', /* or 'bar', 'doughnut' */
    data: { labels: [...], datasets: [...] },
    options: {
      responsive: true,
      scales: {
        x: { ticks: { color: 'var(--tx2)' }, grid: { color: 'var(--bdr)' } },
        y: { ticks: { color: 'var(--tx2)' }, grid: { color: 'var(--bdr)' } }
      }
    }
  });
})();
</script>
```

---

## 6. Quality Checklist

Before returning the report, verify:

- [ ] All data comes from API calls — nothing fabricated
- [ ] All charts use `var(--tx2)` / `var(--bdr)` / `var(--tx1)` for theme compatibility
- [ ] Each chart script is in its own IIFE
- [ ] All canvas IDs are unique
- [ ] Financial values are human-readable ($B, $M)
- [ ] PD values are shown as percentages
- [ ] Rating badges have correct colours
- [ ] Theme toggle button works
- [ ] Sections are numbered sequentially
- [ ] The HTML starts with `<!DOCTYPE html>` and is a complete document
