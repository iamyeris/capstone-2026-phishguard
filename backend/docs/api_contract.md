# API Contract: Analyze URL

## Endpoint
- `POST /analyze`

---

## Request (JSON)

```json
{
  "url": "https://example.com/path"
}

---

## Response (JSON)

{
  "label": "NORMAL|PHISHING|GAMBLING|IMPERSONATION|MALWARE|UNREACHABLE|SUSPICIOUS",
  "risk_score": 0,
  "one_line": "string",
  "screenshot": {
    "type": "none|url|base64",
    "value": ""
  },
  "checks": [
    { "key": "https", "name": "HTTPS 사용", "pass": true }
  ],
  "evidence": {
    "model": { "name": "stub", "version": "stub-v0", "score": 0.0 },
    "rules": { "version": "stub-v0", "hits": [] }
  },
  "latency_ms": 0
}

