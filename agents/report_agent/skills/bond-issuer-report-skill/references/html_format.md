# HTML Report Format Reference

## Document skeleton

```html
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Credit Analysis – {Issuer Name}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
  <style>
    /* Paste contents of assets/report_styles.css here */
  </style>
</head>
<body>
  <button class="theme-btn" onclick="toggleTheme()">◑ Toggle Theme</button>
  <div class="wrap">
    <div class="hdr">
      <div>
        <h1>Credit Analysis Report</h1>
        <div style="font-size:15px;margin-top:4px">{Name} ({Ticker})</div>
      </div>
      <div class="meta">
        <div>Generated: {timestamp}</div>
        <div>{Sector} · {Country}</div>
      </div>
    </div>
    <!-- sections go here -->
  </div>
  <script>
    function toggleTheme(){
      var h=document.documentElement;
      var c=h.getAttribute('data-theme');
      h.setAttribute('data-theme', c==='dark'?'light':'dark');
      Chart.helpers.each(Chart.instances, function(i){ i.update(); });
    }
  </script>
</body>
</html>
```

## CSS theme variables

The report_styles.css in `assets/` defines all variables. Here are the critical ones:

| Variable | Light | Dark | Usage |
|----------|-------|------|-------|
| `--bg1` | `#ffffff` | `#0b1120` | Body background |
| `--bg2` | `#f8fafc` | `#131d32` | Card/section backgrounds |
| `--bgc` | `#ffffff` | `#162032` | Chart container background |
| `--tx1` | `#0f172a` | `#f1f5f9` | Primary text |
| `--tx2` | `#64748b` | `#94a3b8` | Secondary text, labels |
| `--bdr` | `#e2e8f0` | `#1e3050` | Borders, gridlines |
| `--acc` | `#3b82f6` | `#60a5fa` | Accent colour |
| `--accL` | `rgba(59,130,246,.08)` | `rgba(96,165,250,.1)` | Accent light (highlights) |

## Chart type specifications

### Line chart (spread history, PD trends)
```javascript
(()=>{
  new Chart(document.getElementById('spreadChart'), {
    type: 'line',
    data: {
      labels: [/* weekly-sampled dates */],
      datasets: [{
        label: 'Spread (bps)',
        data: [/* values */],
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59,130,246,0.06)',
        fill: true,
        tension: 0.35,
        pointRadius: 0,
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { maxTicksLimit: 12, color: 'var(--tx2)' }, grid: { color: 'var(--bdr)' } },
        y: { title: { display: true, text: 'bps', color: 'var(--tx2)' },
             grid: { color: 'var(--bdr)' }, ticks: { color: 'var(--tx2)' } }
      }
    }
  });
})();
```

### Grouped bar chart (revenue, NI, EBITDA)
```javascript
(()=>{
  new Chart(document.getElementById('revenueChart'), {
    type: 'bar',
    data: {
      labels: ['2021','2022','2023','2024'],
      datasets: [
        { label: 'Revenue ($B)', data: [...], backgroundColor: 'rgba(59,130,246,0.65)', borderRadius: 4 },
        { label: 'Net Income ($B)', data: [...], backgroundColor: 'rgba(16,185,129,0.65)', borderRadius: 4 },
        { label: 'EBITDA ($B)', data: [...], backgroundColor: 'rgba(139,92,246,0.65)', borderRadius: 4 }
      ]
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: 'var(--tx1)' } } },
      scales: {
        x: { grid: { display: false }, ticks: { color: 'var(--tx2)' } },
        y: { title: { display: true, text: '$ Billions', color: 'var(--tx2)' },
             grid: { color: 'var(--bdr)' }, ticks: { color: 'var(--tx2)' } }
      }
    }
  });
})();
```

### Doughnut chart (risk decomposition)
```javascript
(()=>{
  new Chart(document.getElementById('riskPie'), {
    type: 'doughnut',
    data: {
      labels: ['Macro Economy', 'Industry Risk', ...],
      datasets: [{
        data: [18.2, 14.5, ...],
        backgroundColor: ['#3b82f6','#8b5cf6','#ef4444','#10b981','#f59e0b','#ec4899','#6366f1'],
        borderWidth: 0,
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true,
      cutout: '55%',
      plugins: {
        legend: { position: 'bottom', labels: { color: 'var(--tx1)', padding: 12, usePointStyle: true } }
      }
    }
  });
})();
```

### Horizontal bar chart (risk trend)
```javascript
(()=>{
  var td = [1.2, -0.8, 2.5, ...]; // trend values
  new Chart(document.getElementById('riskTrend'), {
    type: 'bar',
    data: {
      labels: ['Macro Economy', 'Industry Risk', ...],
      datasets: [{
        label: '6M Change (%)',
        data: td,
        backgroundColor: td.map(v => v >= 0 ? 'rgba(239,68,68,0.6)' : 'rgba(16,185,129,0.6)'),
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: {
        x: { title: { display: true, text: 'Change (%)', color: 'var(--tx2)' },
             grid: { color: 'var(--bdr)' }, ticks: { color: 'var(--tx2)' } },
        y: { grid: { display: false }, ticks: { color: 'var(--tx2)' } }
      }
    }
  });
})();
```

## Rating badge colour map

| Rating range | Colour | Hex |
|-------------|--------|-----|
| AAA, AA+    | Teal   | `#0d9488` |
| AA, AA-     | Teal   | `#14b8a6` |
| A+          | Blue   | `#2563eb` |
| A           | Blue   | `#3b82f6` |
| A-          | Blue   | `#60a5fa` |
| BBB+        | Amber  | `#ca8a04` |
| BBB         | Amber  | `#eab308` |
| BBB-        | Amber  | `#facc15` |
| BB+         | Orange | `#ea580c` |
| BB          | Orange | `#f97316` |
| BB-         | Orange | `#fb923c` |
| B+, B, B-   | Red    | `#dc2626`, `#ef4444`, `#f87171` |
