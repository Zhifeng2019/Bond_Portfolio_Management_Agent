# Credit Report Agent

An LLM-driven agent that uses the **credit-report-skill** to produce HTML credit analysis reports. Users send natural-language requests (e.g. "Analyze Apple" or "Create a report for Tesla focusing on risk decomposition"), and the agent:

1. Loads the skill (SKILL.md + CSS + references) into the LLM's system prompt
2. Sends the user's request along with 9 data-fetching tool schemas
3. Runs an **agentic tool_use loop** — the LLM decides which tools to call, the agent executes them and feeds results back
4. The LLM writes the HTML report following the skill's formatting rules
5. The agent extracts the HTML and returns it to the caller

Because the LLM reads the skill dynamically and decides the report structure, users can request custom layouts, extra sections, or different analytical focus — and the LLM adapts.

## Quick Start

```bash
cd report_agent

# Install dependencies
pip install -r requirements.txt

# Set your Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...

# Run the server
uvicorn report_agent.api.app:app --reload --port 8000
```

Then call the API:

```bash
# Get a token
TOKEN=$(curl -s -X POST http://localhost:8000/api/agent/token \
  -H "Content-Type: application/json" \
  -d '{"username":"analyst","password":"analyst123"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Generate a report
curl -X POST http://localhost:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"Create a credit analysis report for Apple"}' \
  | python -c "import sys,json; r=json.load(sys.stdin); open('report.html','w').write(r.get('report_html','')); print(r['content'])"
```

## Architecture

```
User: "Analyze TSLA, skip the peer comparison"
              │
              ▼
    ┌─────────────────────────────────────────────┐
    │  FastAPI  (api/app.py)                      │
    │  POST /api/agent/chat                       │
    └──────────────┬──────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────────────┐
    │  Agent  (agent.py)                          │
    │                                             │
    │  1. Load skill → system prompt              │
    │     ┌─────────────────────────────┐         │
    │     │ SKILL.md + CSS + references │         │
    │     └─────────────────────────────┘         │
    │                                             │
    │  2. Send to LLM with 9 tool schemas         │
    │     ┌────────────────────┐                  │
    │     │  Anthropic API     │                  │
    │     │  (Claude Sonnet)   │                  │
    │     └────────┬───────────┘                  │
    │              │                              │
    │  3. Agentic tool_use loop                   │
    │     LLM: "call get_financials(TSLA)"        │
    │     Agent: executes → returns data          │
    │     LLM: "call get_risk_decomposition(TSLA)"│
    │     Agent: executes → returns data          │
    │     LLM: "call get_spread_history(TSLA)"    │
    │     Agent: executes → returns data          │
    │     ...                                     │
    │                                             │
    │  4. LLM writes HTML report                  │
    │     (following SKILL.md instructions)        │
    │                                             │
    │  5. Agent extracts HTML, returns it          │
    └──────────────┬──────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────────────┐
    │  Data Tools  (data_tools.py)                │
    │                                             │
    │  USE_MOCK=true  → mock_data/                │
    │  USE_MOCK=false → real backend APIs          │
    │    (GET /api/data/issuers/{id}/...)          │
    └─────────────────────────────────────────────┘
```

## File Structure

```
report_agent/
├── agent.py              # LLM agentic loop, skill loader, issuer resolver
├── config.py             # USE_MOCK toggle, API keys, LLM settings
├── data_tools.py         # 9 tool functions + LLM schema formatter
├── requirements.txt
├── tests.py              # 7 end-to-end tests
├── api/
│   └── app.py            # FastAPI routes (token, issuers, report, chat)
└── mock_data/
    └── mock_issuer_data.py  # Deterministic mock data for 5 issuers

# The skill folder (sibling directory):
credit-report-skill/
├── SKILL.md              # Instructions the LLM reads
├── assets/
│   └── report_styles.css # CSS included verbatim in reports
└── references/
    ├── api_reference.md  # Full API endpoint docs
    └── html_format.md    # Chart.js patterns, HTML skeleton
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/agent/token` | Get JWT Bearer token |
| GET | `/api/agent/issuers` | List available issuers |
| POST | `/api/agent/report` | Generate report (issuer_id + optional instructions) |
| POST | `/api/agent/chat` | Chat interface (natural language → report or text) |

### POST /api/agent/chat

```json
{"message": "Analyze Apple"}
```

Response (when report is generated):
```json
{
  "type": "report",
  "content": "Report generated successfully.",
  "issuer_id": "AAPL",
  "issuer_name": "Apple Inc.",
  "report_html": "<!DOCTYPE html>...",
  "generated_at": "2026-03-27T10:00:00Z",
  "tool_log": [
    {"round": 1, "tool": "get_issuer_profile", "input": {"issuer_id": "AAPL"}, "ok": true},
    {"round": 1, "tool": "get_credit_ratings", "input": {"issuer_id": "AAPL"}, "ok": true},
    ...
  ]
}
```

### Example requests

```json
// Default 4-section report
{"message": "Create a credit analysis report for Apple"}

// Custom structure
{"message": "Analyze Tesla, but only include executive summary and risk decomposition"}

// Extra section
{"message": "Full credit report for JPM, add a bond portfolio section with duration analysis"}

// Different focus
{"message": "Compare Goldman Sachs with its peers, focus on leverage and coverage ratios"}
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required) | Your Anthropic API key |
| `LLM_MODEL` | `claude-sonnet-4-20250514` | Model to use |
| `LLM_MAX_TOKENS` | `16000` | Max output tokens per LLM call |
| `MAX_TOOL_ROUNDS` | `10` | Max tool_use loop iterations |
| `USE_MOCK` | `true` | `true` = mock data, `false` = call real backend |
| `API_BASE_URL` | `http://localhost:8000` | Backend URL (when USE_MOCK=false) |
| `API_TOKEN` | (empty) | Bearer token for backend APIs |
| `SKILL_DIR` | `../credit-report-skill` | Path to the skill folder |

## Frontend Integration

In your existing `services/api.ts`:

```typescript
export const reportService = {
  async chat(message: string): Promise<ChatResponse> {
    const res = await apiFetch<ChatResponse>('/agent/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
    return res.data;
  },
};
```

When `response.type === 'report'`, render `response.report_html` in an iframe — it's a self-contained HTML document.

## Running Tests

```bash
PYTHONPATH=/path/to/project python report_agent/tests.py
```
