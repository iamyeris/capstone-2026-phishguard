# capstone-2026-phishguard 

AI 기반 피싱·스미싱 예방 애플리케이션(캡스톤 디자인) 레포지토리입니다. 

---

## 구성
- `backend/` : FastAPI 기반 분석 API (stub 버전)
  - `POST /analyze` : URL 입력 → label/risk_score/checks 등을 고정 포맷으로 반환
  - `GET /health` : 헬스체크
- `backend/docs/api_contract.md` : 앱/UI 개발자와의 API 계약서(요청/응답 JSON 구조)

---

## 백엔드 실행

### 1) 가상환경 생성/활성화
```bash
cd capstone-2026-phishguard
python3 -m venv .venv
source .venv/bin/activate
```

### 2) 의존성 설치
```bash
python -m pip install -U pip
python -m pip install -r backend/requirements.txt 
```

### 3) 서버 실행 
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000``
```
