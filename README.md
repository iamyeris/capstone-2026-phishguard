# capstone-2026-phishguard 

AI 기반 피싱·스미싱 예방 애플리케이션(캡스톤 디자인) 레포지토리입니다. 

---
## ✨ 핵심 기능 (Key Features)

- **Real-time Web Crawling:** Playwright를 활용하여 격리된 환경에서 사이트에 접속, 텍스트와 스크린샷을 즉각 수집합니다.
- **AI Security Report:** Gemini 1.5 Flash 모델이 분석 결과(위험 점수, 텍스트)를 바탕으로 사용자 친화적인 보안 권고 리포트를 생성합니다.
- **Hybrid Analysis Engine:** 규칙 기반(Stub) 분석과 딥러닝(PyTorch) 모델을 결합하여 정확도를 높였습니다.
- **Visual Evidence:** 분석 시점의 사이트 화면을 캡처하여 사용자에게 시각적 증거(Base64 스크린샷)를 제공합니다.

---
## 📂 프로젝트 구조 (Project Structure)

```
backend/
 ├── main.py            # FastAPI 앱 진입점 및 서버 설정
 ├── api/               # API 엔드포인트 관리 (routes.py)
 ├── schemas/           # Pydantic 데이터 모델 (payload.py)
 ├── services/          # 비즈니스 로직 레이어
 │    ├── crawler.py    # Playwright 기반 비동기 웹 크롤러
 │    └── gemini.py     # Gemini API 연동 및 AI 리포트 생성기
 └── requirements.txt   # 의존성 (torch, fastapi, playwright 등)
```
---
## 🛠 기술 스택 (Tech Stack)
- *Framework*: FastAPI

- *Language*: Python 3.10+

- *AI/ML*: PyTorch, Google Gemini API

- *Automation*: Playwright (Chromium)

- *Environment*: Ubuntu / macOS (Apple Silicon 호환)

---
## 백엔드 실행

### 1) 가상환경 생성/활성화
```bash
cd capstone-2026-phishguard/backend
python3 -m venv .venv
source .venv/bin/activate
```

### 2) 의존성 최신화
```bash
python -m pip install -U pip
python -m pip install -r backend/requirements.txt 
```
### 3) 브라우저 설치 (최초 1회)
```bash
playwright install chromium
```

### 4) 환경 변수(.env) 설정
루트 폴더 또는 `backend` 폴더 안에 `.env` 파일을 생성하고, 아래와 같이 API 키를 입력(하드코딩 절대 금지!)
*(현재는 UI 더미 테스트가 가능하도록 예외 처리가 되어 있어, 키가 당장 없어도 서버 구동 및 테스트는 가능합니다.)*

```env
GEMINI_API_KEY=디스코드_채팅방에_올려뒀어요_복붙해주세용
```

### 5) 서버 실행 
```
cd backend
uvicorn main:app --reload
```
