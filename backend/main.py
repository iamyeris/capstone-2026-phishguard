from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
import torch

# 전역 변수로 AI 모델을 담아둘 딕셔너리 (서버 실행 내내 유지됨)
ml_models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    서버가 켜질 때(Startup) 실행되는 구간
    """
    print("🚀 서버 시작 중... AI 모델 로드 준비")
    
    # 1. 맥북 GPU(MPS) 확인 및 디바이스 설정
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"🖥️  Using device: {device}")
    
    # 2. 파인튜닝한 모델과 가중치(weights) 불러오기 (지금은 주석 처리된 예시)
    # 추후 학습이 완료된 .pth 파일 등을 여기서 불러와서 device에 올리고 추론(eval) 모드로 세팅합니다.
    # model = MyBertModel()
    # model.load_state_dict(torch.load("model_weights.pth"))
    # model.to(device) 
    # model.eval()     
    
    # 3. 모델을 전역 딕셔너리에 저장
    # ml_models["phish_checker"] = model
    
    yield # 이 시점부터 서버가 정상적으로 클라이언트의 API 요청을 받기 시작함
    
    """
    서버가 꺼질 때(Shutdown) 실행되는 구간
    """
    print("🛑 서버 종료 중... 메모리 정리")
    ml_models.clear()


# lifespan을 FastAPI 앱에 연결
app = FastAPI(title="PhishGuard API", version="0.1.0", lifespan=lifespan)

# CORS 설정 추가 (모든 출처 허용 - 개발 단계에서 편리함)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시에는 프론트엔드 도메인만 넣는 것이 좋습니다.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    url: str  # HttpUrl로 엄격하게 하고 싶으면 HttpUrl로 바꿔도 됩니다.


def stub_analyze(url: str) -> dict:
    """
    초보자용 더미 분석기:
    - url 문자열에 특정 키워드가 포함되면 점수/라벨을 다르게 반환합니다.
    - 앱 UI 개발을 위해 결과 포맷을 고정합니다.
    """
    url_lower = url.lower()
    hits = []
    checks = []

    # 기본 체크(샘플)
    https_ok = url_lower.startswith("https://")
    checks.append({"key": "https", "name": "HTTPS 사용", "pass": https_ok})

    # 키워드 기반 룰(아주 단순)
    risk_score = 10
    label = "NORMAL"
    one_line = "특이 패턴이 없습니다. 그래도 개인정보 입력은 주의하세요."

    if any(k in url_lower for k in ["login", "verify", "account", "password"]):
        hits.append("keyword_login")
        checks.append({"key": "keyword_risk", "name": "로그인/인증 유도 키워드", "pass": False})
        risk_score = 80
        label = "PHISHING"
        one_line = "로그인/인증 유도 패턴이 보입니다. 접속 및 입력을 중단하세요."

    if any(k in url_lower for k in ["bet", "casino", "slot", "toto"]):
        hits.append("keyword_gambling")
        checks.append({"key": "keyword_gambling", "name": "도박 관련 키워드", "pass": False})
        risk_score = max(risk_score, 75)
        label = "GAMBLING"
        one_line = "도박 관련 키워드가 포함되어 있습니다. 접속을 피하세요."

    if any(k in url_lower for k in ["download", ".apk", ".exe"]):
        hits.append("keyword_download")
        checks.append({"key": "download_hint", "name": "다운로드 유도", "pass": False})
        risk_score = max(risk_score, 85)
        label = "MALWARE"
        one_line = "다운로드 유도 정황이 있습니다. 악성코드 가능성이 있어 차단을 권장합니다."

    # hits가 없으면 체크 항목을 최소로 유지
    if not hits:
        checks.append({"key": "keyword_risk", "name": "위험 키워드 포함", "pass": True})

    return {
        "label": label,
        "risk_score": risk_score,
        "one_line": one_line,
        "screenshot": {"type": "none", "value": ""},
        "checks": checks,
        "evidence": {
            "model": {"name": "stub", "version": "stub-v0", "score": 0.0},
            "rules": {"version": "stub-v0", "hits": hits},
        },
        "latency_ms": 0,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    start = time.time()
    
    # TODO: 추후 ml_models["phish_checker"]를 활용하여 실제 AI 추론 로직으로 교체
    result = stub_analyze(req.url)
    
    result["latency_ms"] = int((time.time() - start) * 1000)
    return result