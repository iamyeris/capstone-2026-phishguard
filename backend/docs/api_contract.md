# API Contract: Analyze URL

## Endpoint
- `POST /analyze`

---

## Request (JSON)

```json
{
  "url": "[https://example.com/path](https://example.com/path)",
  "user_id": "string (optional, 사용자 식별용 UUID)" 
}

---

## Response (JSON)

{
  "label": "NORMAL|PHISHING|GAMBLING|IMPERSONATION|MALWARE|UNREACHABLE|SUSPICIOUS",
  "risk_score": 85,
  "one_line": "다운로드 유도 정황이 있습니다. 악성코드 가능성이 있어 차단을 권장합니다.",
  "gemini_report": "AI 분석 결과, 해당 사이트는 메인 화면에 사설 토토 배너를 포함하고 있으며... (상세 분석 내용 또는 빈 문자열)",
  "screenshot": {
    "type": "none|url|base64",
    "value": "/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBx..."
  },
  "checks": [
    { "key": "https", "name": "HTTPS 사용", "pass": true },
    { "key": "keyword_risk", "name": "로그인/인증 유도 키워드", "pass": false }
  ],
  "evidence": {
    "model": { "name": "PhishGuard-BERT", "version": "v0.1-mock", "score": 85.0 },
    "rules": { "version": "stub-v0", "hits": ["keyword_download"] }
  },
  "latency_ms": 1250
}

