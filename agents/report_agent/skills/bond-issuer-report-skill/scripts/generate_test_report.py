#!/usr/bin/env python3
"""
Simulate the agent using the credit-report skill.

This script:
1. Reads the skill's SKILL.md to understand the report format
2. Fetches data (from mock since no backend is running)
3. Computes ratios locally (as the skill instructs)
4. Generates the HTML report following the skill's format/component patterns
5. Saves the output for review

Usage:
    python scripts/generate_test_report.py AAPL [output_path]
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Since no backend is running, use mock data directly
# In production, the agent would call the API endpoints listed in SKILL.md §2
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
CSS_FILE = SKILL_DIR / "assets" / "report_styles.css"


# ── Mock data (same structure the APIs would return) ──────────────────────

import hashlib

def _su(iid, salt, lo, hi):
    h = hashlib.md5(f"{iid}{salt}".encode()).hexdigest()
    return lo + (int(h[:8], 16) / 0xFFFFFFFF) * (hi - lo)

ISSUERS = {
    "AAPL": {"name":"Apple Inc.","sector":"Technology","country":"US","ticker":"AAPL"},
    "MSFT": {"name":"Microsoft Corporation","sector":"Technology","country":"US","ticker":"MSFT"},
    "JPM":  {"name":"JPMorgan Chase & Co.","sector":"Financials","country":"US","ticker":"JPM"},
    "TSLA": {"name":"Tesla Inc.","sector":"Consumer Discretionary","country":"US","ticker":"TSLA"},
    "GS":   {"name":"Goldman Sachs Group","sector":"Financials","country":"US","ticker":"GS"},
}

_RATINGS = {
    "AAPL":[("2018-01-15","AAA","S&P","Stable"),("2020-06-01","AA+","S&P","Negative"),("2022-03-10","AA+","Moody's","Stable"),("2024-09-15","AA","S&P","Stable")],
    "MSFT":[("2017-05-01","AAA","S&P","Stable"),("2019-11-20","AAA","Fitch","Stable"),("2022-01-05","AAA","S&P","Stable"),("2024-07-01","AAA","Moody's","Stable")],
    "JPM": [("2018-03-10","A+","S&P","Stable"),("2020-04-15","A","S&P","Negative"),("2021-12-01","A+","Moody's","Positive"),("2024-06-20","A+","S&P","Positive")],
    "TSLA":[("2019-08-01","BB-","S&P","Stable"),("2021-02-15","BB","Fitch","Positive"),("2023-01-10","BB+","S&P","Positive"),("2024-11-01","BBB-","S&P","Positive")],
    "GS":  [("2018-06-01","A","S&P","Stable"),("2020-05-10","A-","S&P","Negative"),("2022-08-15","A","Moody's","Stable"),("2024-04-01","A","S&P","Stable")],
}

_BASE_PD = {"AAPL":0.0002,"MSFT":0.0001,"JPM":0.0005,"TSLA":0.0015,"GS":0.0004}
_BASE_SPREAD = {"AAPL":55,"MSFT":45,"JPM":80,"TSLA":200,"GS":75}

_FIN = {
    "AAPL":{"revenue":394e9,"net_income":97e9,"total_assets":352e9,"total_debt":111e9,"equity":62e9,"ebitda":130e9,"interest_expense":3.9e9,"cash":48e9,"operating_cf":110e9},
    "MSFT":{"revenue":211e9,"net_income":72e9,"total_assets":411e9,"total_debt":78e9,"equity":206e9,"ebitda":100e9,"interest_expense":2.1e9,"cash":104e9,"operating_cf":89e9},
    "JPM": {"revenue":154e9,"net_income":49e9,"total_assets":3740e9,"total_debt":450e9,"equity":303e9,"ebitda":70e9,"interest_expense":25e9,"cash":580e9,"operating_cf":55e9},
    "TSLA":{"revenue":97e9,"net_income":7.9e9,"total_assets":106e9,"total_debt":5.6e9,"equity":53e9,"ebitda":14e9,"interest_expense":0.5e9,"cash":26e9,"operating_cf":13e9},
    "GS":  {"revenue":47e9,"net_income":11e9,"total_assets":1570e9,"total_debt":280e9,"equity":116e9,"ebitda":18e9,"interest_expense":15e9,"cash":240e9,"operating_cf":14e9},
}

from datetime import timedelta

def fetch_all(iid):
    """Simulate fetching all data from APIs."""
    iid = iid.upper()
    issuer = {**ISSUERS[iid], "id": iid}

    ratings = [{"date":d,"rating":r,"agency":a,"outlook":o} for d,r,a,o in _RATINGS.get(iid,_RATINGS["AAPL"])]

    bp = _BASE_PD.get(iid, 0.0005)
    tenors = [0.5,1,2,3,5,7,10]
    pd_curve = [{"tenor":t,"pd":round(bp*(1+0.35*t),6)} for t in tenors]
    today = datetime.now()
    pd_hist = [{"date":(today-timedelta(days=30*(23-m))).strftime("%Y-%m-%d"),
                "pd_1y":round(bp+_su(iid,f"ph1{m}",-0.0001,0.0001),6),
                "pd_5y":round(bp*2.8+_su(iid,f"ph5{m}",-0.0003,0.0003),6)} for m in range(24)]

    base = _FIN.get(iid, _FIN["AAPL"])
    financials = []
    for i, yr in enumerate([2021,2022,2023,2024]):
        factor = 1 + 0.05*(i-1) + _su(iid,f"f{yr}",-0.02,0.02)
        row = {"year":yr}
        for k,v in base.items(): row[k] = round(v*factor)
        financials.append(row)

    coupons = [2.5,3.0,3.75,4.25,5.0,5.5]
    bonds = [{"isin":f"US{iid}{i:03d}","coupon":coupons[i],"maturity":f"{2026+i*2}-06-15",
              "face_value":1000,"currency":"USD","issue_size_mm":[500,750,1000,1500,2000,1000][i],
              "price":round(95+_su(iid,f"bp{i}",0,13),2),"ytm":round(3.5+_su(iid,f"by{i}",0,3),3),
              "spread_bps":round(40+_su(iid,f"bs{i}",0,210)),"modified_duration":round(1.5+_su(iid,f"bd{i}",0,10.5),2)} for i in range(6)]

    s = _BASE_SPREAD.get(iid,80)
    spreads = []
    for d in range(365):
        dt = today - timedelta(days=364-d)
        s += _su(iid,f"sp{d}",-3,3); s = max(20,s)
        spreads.append({"date":dt.strftime("%Y-%m-%d"),"spread_bps":round(s,1)})

    raw_risk = {"macro_economy":10+_su(iid,"r0",0,15),"industry_risk":8+_su(iid,"r1",0,12),
                "leverage":12+_su(iid,"r2",0,18),"profitability":8+_su(iid,"r3",0,12),
                "liquidity":5+_su(iid,"r4",0,10),"market_sentiment":6+_su(iid,"r5",0,9),
                "country_risk":2+_su(iid,"r6",0,8)}
    total = sum(raw_risk.values())
    risk = {"contributions_pct":{k:round(v/total*100,1) for k,v in raw_risk.items()},
            "trend_6m":{k:round(_su(iid,f"rt{k}",-5,5),1) for k in raw_risk}}

    peers = []
    for pid in [iid] + [p for p in ISSUERS if p != iid]:
        pf = _FIN.get(pid, _FIN["AAPL"])
        pr = _RATINGS.get(pid, _RATINGS["AAPL"])
        peers.append({"issuer_id":pid,"name":ISSUERS[pid]["name"],
                       "rating":pr[-1][1],
                       "leverage":round(pf["total_debt"]/pf["ebitda"],2),
                       "interest_coverage":round(pf["ebitda"]/pf["interest_expense"],2),
                       "profit_margin_pct":round(pf["net_income"]/pf["revenue"]*100,1),
                       "debt_to_equity":round(pf["total_debt"]/pf["equity"],2)})

    return {"issuer":issuer,"rating_history":ratings,"pd_data":{"current_curve":pd_curve,"historical":pd_hist},
            "financials":financials,"bonds":bonds,"spread_history":spreads,
            "risk_decomposition":risk,"peer_comparison":peers}


# ── Local ratio computations (SKILL.md §3) ────────────────────────────────

def compute_ratios(financials):
    ratios = []
    for f in financials:
        eq=f["equity"] or 1; ie=f["interest_expense"] or 1; eb=f["ebitda"] or 1; rv=f["revenue"] or 1
        ratios.append({"year":f["year"],
            "interest_coverage":round(eb/ie,2), "net_leverage":round((f["total_debt"]-f["cash"])/eb,2),
            "debt_to_equity":round(f["total_debt"]/eq,2), "profit_margin_pct":round(f["net_income"]/rv*100,1)})
    return ratios

def bond_stats(bonds):
    n = len(bonds); total = sum(b["issue_size_mm"] for b in bonds)
    wac = sum(b["coupon"]*b["issue_size_mm"] for b in bonds)/total if total else 0
    wad = sum(b["modified_duration"]*b["issue_size_mm"] for b in bonds)/total if total else 0
    return n, total, round(wac,2), round(wad,1)


# ── Report generation (following SKILL.md §4–§6) ──────────────────────────

def fmt(v):
    if v is None: return "N/A"
    if abs(v)>=1e9: return f"${v/1e9:,.1f}B"
    if abs(v)>=1e6: return f"${v/1e6:,.1f}M"
    return f"{v:,.2f}"

BADGE_COLORS = {
    "AAA":"#0d9488","AA+":"#0d9488","AA":"#14b8a6","AA-":"#14b8a6",
    "A+":"#2563eb","A":"#3b82f6","A-":"#60a5fa",
    "BBB+":"#ca8a04","BBB":"#eab308","BBB-":"#facc15",
    "BB+":"#ea580c","BB":"#f97316","BB-":"#fb923c",
    "B+":"#dc2626","B":"#ef4444","B-":"#f87171",
}

def badge(r):
    c = BADGE_COLORS.get(r,"#6b7280")
    return f'<span class="rating-badge" style="background:{c}">{r}</span>'

def generate_report(data, sections=None):
    """Generate the HTML report following SKILL.md patterns."""
    issuer = data["issuer"]; ratings = data["rating_history"]
    pd_data = data["pd_data"]; financials = data["financials"]
    bonds = data["bonds"]; spreads = data["spread_history"]
    risk = data["risk_decomposition"]; peers = data["peer_comparison"]
    ratios = compute_ratios(financials)
    lr = ratings[-1] if ratings else {}
    fin = financials[-1] if financials else {}
    r = ratios[-1] if ratios else {}
    n_bonds, total_mm, wac, wad = bond_stats(bonds)
    pd_1y = pd_data["historical"][-1]["pd_1y"] if pd_data.get("historical") else 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    css = CSS_FILE.read_text() if CSS_FILE.exists() else ""

    active = sections or ["executive_summary","temporal_peer_comparison","risk_decomposition_fundamental","summary_recommendation"]
    body_parts = []
    sec_num = 0

    for sec in active:
        sec_num += 1
        if sec == "executive_summary":
            body_parts.append(f"""
<section id="sec-{sec_num}"><h2>{sec_num}. Executive Summary</h2>
<div class="kpi-grid">
<div class="kpi"><div class="kpi-label">Issuer</div><div class="kpi-value">{issuer['name']}</div><div class="kpi-sub">{issuer['sector']} · {issuer['country']}</div></div>
<div class="kpi"><div class="kpi-label">Credit Rating</div><div class="kpi-value">{badge(lr.get('rating','NR'))}</div><div class="kpi-sub">{lr.get('agency','–')} · {lr.get('outlook','–')}</div></div>
<div class="kpi"><div class="kpi-label">1-Year PD</div><div class="kpi-value">{pd_1y*100:.3f}%</div><div class="kpi-sub">Probability of Default</div></div>
<div class="kpi"><div class="kpi-label">Bonds Outstanding</div><div class="kpi-value">{n_bonds} issues · ${total_mm:,.0f}M</div><div class="kpi-sub">Wt Avg Cpn {wac}% · Dur {wad}yr</div></div>
</div>
<div class="prose"><p><strong>{issuer['name']}</strong> ({issuer.get('ticker','')}) holds a <strong>{lr.get('rating','NR')}</strong> rating with a <strong>{lr.get('outlook','–')}</strong> outlook from {lr.get('agency','–')}.
In FY{fin.get('year','')}, revenue was {fmt(fin.get('revenue'))}, EBITDA {fmt(fin.get('ebitda'))}, net income {fmt(fin.get('net_income'))}.
Key ratios: interest coverage <strong>{r.get('interest_coverage','N/A')}x</strong>, net leverage <strong>{r.get('net_leverage','N/A')}x</strong>, D/E <strong>{r.get('debt_to_equity','N/A')}x</strong>.</p></div>
</section>""")

        elif sec == "temporal_peer_comparison":
            rtl = "".join(f'<div class="tl-item"><span class="tl-date">{x["date"]}</span>{badge(x["rating"])}<span class="tl-meta">{x["agency"]} · {x["outlook"]}</span></div>' for x in ratings)
            sp_d = json.dumps([s["date"] for s in spreads[::7]])
            sp_v = json.dumps([s["spread_bps"] for s in spreads[::7]])
            pd_hd = json.dumps([p["date"] for p in pd_data["historical"]])
            pd1 = json.dumps([round(p["pd_1y"]*100,4) for p in pd_data["historical"]])
            pd5 = json.dumps([round(p["pd_5y"]*100,4) for p in pd_data["historical"]])
            pd_tenors = json.dumps([f'{p["tenor"]}Y' for p in pd_data["current_curve"]])
            pd_curve_v = json.dumps([round(p["pd"]*100,4) for p in pd_data["current_curve"]])
            prows = "".join(f'<tr{"" if p["issuer_id"]!=issuer.get("id","") else " class=hl"}><td>{p["name"]}</td><td>{badge(p["rating"])}</td><td>{p["leverage"]:.2f}x</td><td>{p["interest_coverage"]:.2f}x</td><td>{p["profit_margin_pct"]:.1f}%</td><td>{p["debt_to_equity"]:.2f}x</td></tr>' for p in peers)

            body_parts.append(f"""
<section id="sec-{sec_num}"><h2>{sec_num}. Temporal and Peer Comparison</h2>
<h3>Rating History</h3><div class="rating-timeline">{rtl}</div>
<h3>Credit Spread (bps) – 12 Months</h3><div class="chart-box"><canvas id="c{sec_num}a"></canvas></div>
<script>(()=>{{new Chart(document.getElementById('c{sec_num}a'),{{type:'line',data:{{labels:{sp_d},datasets:[{{label:'Spread',data:{sp_v},borderColor:'#3b82f6',backgroundColor:'rgba(59,130,246,0.06)',fill:true,tension:0.35,pointRadius:0,borderWidth:2}}]}},options:{{responsive:true,plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{maxTicksLimit:12,color:'var(--tx2)'}},grid:{{color:'var(--bdr)'}}}},y:{{title:{{display:true,text:'bps',color:'var(--tx2)'}},grid:{{color:'var(--bdr)'}},ticks:{{color:'var(--tx2)'}}}}}}}}}})}})();</script>
<h3>PD Term Structure (Current)</h3><div class="chart-box"><canvas id="c{sec_num}e"></canvas></div>
<script>(()=>{{new Chart(document.getElementById('c{sec_num}e'),{{type:'bar',data:{{labels:{pd_tenors},datasets:[{{label:'PD %',data:{pd_curve_v},backgroundColor:'rgba(139,92,246,0.55)',borderColor:'#8b5cf6',borderWidth:1,borderRadius:4}}]}},options:{{responsive:true,plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:{{display:false}},ticks:{{color:'var(--tx2)'}}}},y:{{title:{{display:true,text:'PD (%)',color:'var(--tx2)'}},grid:{{color:'var(--bdr)'}},ticks:{{color:'var(--tx2)'}}}}}}}}}})}})();</script>
<h3>Historical PD (1Y &amp; 5Y)</h3><div class="chart-box"><canvas id="c{sec_num}b"></canvas></div>
<script>(()=>{{new Chart(document.getElementById('c{sec_num}b'),{{type:'line',data:{{labels:{pd_hd},datasets:[{{label:'1Y PD %',data:{pd1},borderColor:'#0d9488',backgroundColor:'rgba(13,148,136,0.06)',fill:true,tension:0.35,pointRadius:0,borderWidth:2}},{{label:'5Y PD %',data:{pd5},borderColor:'#f59e0b',backgroundColor:'rgba(245,158,11,0.06)',fill:true,tension:0.35,pointRadius:0,borderWidth:2}}]}},options:{{responsive:true,plugins:{{legend:{{labels:{{color:'var(--tx1)'}}}}}},scales:{{x:{{ticks:{{maxTicksLimit:12,color:'var(--tx2)'}},grid:{{color:'var(--bdr)'}}}},y:{{title:{{display:true,text:'PD (%)',color:'var(--tx2)'}},grid:{{color:'var(--bdr)'}},ticks:{{color:'var(--tx2)'}}}}}}}}}})}})();</script>
<h3>Peer Comparison</h3><div class="tbl-wrap"><table><thead><tr><th>Issuer</th><th>Rating</th><th>Leverage</th><th>Coverage</th><th>Margin</th><th>D/E</th></tr></thead><tbody>{prows}</tbody></table></div>
</section>""")

        elif sec == "risk_decomposition_fundamental":
            ct = risk["contributions_pct"]; tr = risk["trend_6m"]
            rl = json.dumps([k.replace("_"," ").title() for k in ct])
            rv = json.dumps(list(ct.values()))
            tv = json.dumps(list(tr.values()))
            rc = "['#3b82f6','#8b5cf6','#ef4444','#10b981','#f59e0b','#ec4899','#6366f1']"
            colors_list = ['#3b82f6','#8b5cf6','#ef4444','#10b981','#f59e0b','#ec4899','#6366f1']
            rrows = ""
            for i,(k,v) in enumerate(ct.items()):
                t = tr[k]; arrow = "↑" if t>0 else ("↓" if t<0 else "→")
                cls = "tup" if t>0 else ("tdn" if t<0 else "tfl")
                rrows += f'<tr><td><span class="dot" style="background:{colors_list[i%7]}"></span>{k.replace("_"," ").title()}</td><td>{v:.1f}%</td><td class="{cls}">{arrow} {t:+.1f}%</td></tr>'
            frows = "".join(f'<tr><td>{f["year"]}</td><td>{fmt(f["revenue"])}</td><td>{fmt(f["net_income"])}</td><td>{fmt(f["ebitda"])}</td><td>{fmt(f["total_debt"])}</td><td>{fmt(f["cash"])}</td></tr>' for f in financials)
            yrs = json.dumps([str(f["year"]) for f in financials])
            rev_v = json.dumps([round(f["revenue"]/1e9,1) for f in financials])
            ni_v = json.dumps([round(f["net_income"]/1e9,1) for f in financials])
            eb_v = json.dumps([round(f["ebitda"]/1e9,1) for f in financials])
            cov_v = json.dumps([x["interest_coverage"] for x in ratios])
            lev_v = json.dumps([x["net_leverage"] for x in ratios])
            dte_v = json.dumps([x["debt_to_equity"] for x in ratios])

            body_parts.append(f"""
<section id="sec-{sec_num}"><h2>{sec_num}. Risk Decomposition &amp; Fundamental Analysis</h2>
<h3>Risk Factor Breakdown</h3>
<div class="risk-grid">
<div class="chart-box"><canvas id="c{sec_num}a"></canvas></div>
<div class="tbl-wrap compact"><table><thead><tr><th>Factor</th><th>Weight</th><th>6M Trend</th></tr></thead><tbody>{rrows}</tbody></table></div>
</div>
<script>(()=>{{new Chart(document.getElementById('c{sec_num}a'),{{type:'doughnut',data:{{labels:{rl},datasets:[{{data:{rv},backgroundColor:{rc},borderWidth:0,hoverOffset:8}}]}},options:{{responsive:true,cutout:'55%',plugins:{{legend:{{position:'bottom',labels:{{color:'var(--tx1)',padding:12,usePointStyle:true}}}}}}}}}})}})();</script>
<h3>Factor Trend (6M Change)</h3><div class="chart-box"><canvas id="c{sec_num}b"></canvas></div>
<script>(()=>{{var td={tv};new Chart(document.getElementById('c{sec_num}b'),{{type:'bar',data:{{labels:{rl},datasets:[{{label:'Δ6M',data:td,backgroundColor:td.map(v=>v>=0?'rgba(239,68,68,0.6)':'rgba(16,185,129,0.6)'),borderRadius:4}}]}},options:{{responsive:true,indexAxis:'y',plugins:{{legend:{{display:false}}}},scales:{{x:{{title:{{display:true,text:'Change (%)',color:'var(--tx2)'}},grid:{{color:'var(--bdr)'}},ticks:{{color:'var(--tx2)'}}}},y:{{grid:{{display:false}},ticks:{{color:'var(--tx2)'}}}}}}}}}})}})();</script>
<h3>Financial Summary</h3><div class="tbl-wrap"><table><thead><tr><th>Year</th><th>Revenue</th><th>Net Inc</th><th>EBITDA</th><th>Debt</th><th>Cash</th></tr></thead><tbody>{frows}</tbody></table></div>
<h3>Revenue &amp; Profitability ($B)</h3><div class="chart-box"><canvas id="c{sec_num}c"></canvas></div>
<script>(()=>{{new Chart(document.getElementById('c{sec_num}c'),{{type:'bar',data:{{labels:{yrs},datasets:[{{label:'Revenue',data:{rev_v},backgroundColor:'rgba(59,130,246,0.65)',borderRadius:4}},{{label:'Net Income',data:{ni_v},backgroundColor:'rgba(16,185,129,0.65)',borderRadius:4}},{{label:'EBITDA',data:{eb_v},backgroundColor:'rgba(139,92,246,0.65)',borderRadius:4}}]}},options:{{responsive:true,plugins:{{legend:{{labels:{{color:'var(--tx1)'}}}}}},scales:{{x:{{grid:{{display:false}},ticks:{{color:'var(--tx2)'}}}},y:{{title:{{display:true,text:'$ Billions',color:'var(--tx2)'}},grid:{{color:'var(--bdr)'}},ticks:{{color:'var(--tx2)'}}}}}}}}}})}})();</script>
<h3>Credit Ratios</h3><div class="chart-box"><canvas id="c{sec_num}d"></canvas></div>
<script>(()=>{{new Chart(document.getElementById('c{sec_num}d'),{{type:'line',data:{{labels:{yrs},datasets:[{{label:'Coverage',data:{cov_v},borderColor:'#0d9488',tension:0.3,borderWidth:2}},{{label:'Net Leverage',data:{lev_v},borderColor:'#ef4444',tension:0.3,borderWidth:2}},{{label:'D/E',data:{dte_v},borderColor:'#f59e0b',tension:0.3,borderWidth:2}}]}},options:{{responsive:true,plugins:{{legend:{{labels:{{color:'var(--tx1)'}}}}}},scales:{{x:{{grid:{{display:false}},ticks:{{color:'var(--tx2)'}}}},y:{{title:{{display:true,text:'Ratio',color:'var(--tx2)'}},grid:{{color:'var(--bdr)'}},ticks:{{color:'var(--tx2)'}}}}}}}}}})}})();</script>
</section>""")

        elif sec == "summary_recommendation":
            cov = r.get("interest_coverage",0) or 0
            lev_val = r.get("net_leverage",0) or 0
            pd_pct = pd_1y*100
            top_risk = max(risk["contributions_pct"],key=risk["contributions_pct"].get).replace("_"," ").title()
            if cov>10 and lev_val<2 and pd_pct<0.5:
                lvl,col = "LOW RISK","#10b981"
                txt = "Strong credit fundamentals with robust coverage and very low default probability."
            elif cov>4 and lev_val<5 and pd_pct<1.5:
                lvl,col = "MODERATE RISK","#f59e0b"
                txt = "Adequate credit metrics. Key risk drivers should be monitored for deterioration."
            else:
                lvl,col = "ELEVATED RISK","#ef4444"
                txt = "Elevated risk. Leverage is high relative to earnings. Close monitoring recommended."
            worsening = [k.replace("_"," ").title() for k,v in risk["trend_6m"].items() if v>2]
            improving = [k.replace("_"," ").title() for k,v in risk["trend_6m"].items() if v<-2]
            extra = ""
            if worsening: extra += f'<p><strong>Deteriorating:</strong> {", ".join(worsening)}</p>'
            if improving: extra += f'<p><strong>Improving:</strong> {", ".join(improving)}</p>'

            body_parts.append(f"""
<section id="sec-{sec_num}"><h2>{sec_num}. Summary and Recommendation</h2>
<div class="rec-banner" style="border-left:4px solid {col}"><div class="rec-level" style="color:{col}">{lvl}</div><p>{txt}</p></div>
<div class="prose"><h3>Key Findings</h3>
<ul><li>Rating: <strong>{lr.get('rating','NR')}</strong> ({lr.get('outlook','–')})</li>
<li>1Y PD: <strong>{pd_pct:.3f}%</strong></li>
<li>Coverage: <strong>{r.get('interest_coverage','N/A')}x</strong></li>
<li>Net leverage: <strong>{r.get('net_leverage','N/A')}x</strong></li>
<li>Top risk: <strong>{top_risk}</strong></li></ul>
{extra}</div>
<div class="disclaimer"><p><em>Generated by the Bond Analysis Agent. Not investment advice.</em></p></div>
</section>""")

        elif sec == "bond_portfolio":
            brows = "".join(f'<tr><td>{b["isin"]}</td><td>{b["coupon"]:.2f}%</td><td>{b["maturity"]}</td><td>${b["price"]:.2f}</td><td>{b["ytm"]:.3f}%</td><td>{b["spread_bps"]:.0f}</td><td>{b["modified_duration"]:.2f}</td></tr>' for b in bonds)
            body_parts.append(f"""
<section id="sec-{sec_num}"><h2>{sec_num}. Bond Portfolio</h2>
<div class="tbl-wrap"><table><thead><tr><th>ISIN</th><th>Coupon</th><th>Maturity</th><th>Price</th><th>YTM</th><th>Spread (bps)</th><th>Duration</th></tr></thead>
<tbody>{brows}</tbody></table></div>
<div class="prose"><p>{n_bonds} bonds outstanding, totalling ${total_mm:,.0f}M. Weighted average coupon: {wac}%, weighted average duration: {wad} years.</p></div>
</section>""")

    body = "\n".join(body_parts)

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Credit Analysis – {issuer['name']}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>{css}</style>
</head>
<body>
<button class="theme-btn" onclick="toggleTheme()">◑ Toggle Theme</button>
<div class="wrap">
<div class="hdr"><div><h1>Credit Analysis Report</h1>
<div style="font-size:15px;margin-top:4px">{issuer['name']} ({issuer.get('ticker','')})</div></div>
<div class="meta"><div>Generated: {now}</div><div>{issuer['sector']} · {issuer['country']}</div></div></div>
{body}
</div>
<script>function toggleTheme(){{var h=document.documentElement,c=h.getAttribute('data-theme');h.setAttribute('data-theme',c==='dark'?'light':'dark');Chart.helpers.each(Chart.instances,function(i){{i.update()}})}}</script>
</body></html>"""


if __name__ == "__main__":
    issuer_id = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    output = sys.argv[2] if len(sys.argv) > 2 else None

    # Determine sections from test case
    sections = None  # default
    if len(sys.argv) > 3:
        sections = sys.argv[3].split(",")

    data = fetch_all(issuer_id)
    html = generate_report(data, sections=sections)

    if output:
        Path(output).write_text(html)
    else:
        out_dir = SKILL_DIR.parent / "credit-report-skill-workspace" / "iteration-1"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"report_{issuer_id.lower()}.html"
        out_path.write_text(html)
        print(f"Report saved to {out_path} ({len(html):,} chars)")
