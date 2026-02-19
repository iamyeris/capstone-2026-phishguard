from fastapi import APIRouter
import time
from schemas.payload import AnalyzeRequest

# APIRouter 객체 생성
router = APIRouter()

def stub_analyze(url: str) -> dict:
    """
    초보자용 더미 분석기 (나중에 services/ 와 ml/ 로직으로 교체될 예정!)
    """
    url_lower = url.lower()
    hits = []
    checks = []

    https_ok = url_lower.startswith("https://")
    checks.append({"key": "https", "name": "HTTPS 사용", "pass": https_ok})

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

# 기존 @app.post 대신 @router.post 사용 (경로는 main.py에서 prefix로 잡아줌)
@router.post("/")
def analyze_url(req: AnalyzeRequest):
    start = time.time()
    
    # TODO: 추후 이곳에서 services.crawler 와 ml.inference 를 호출하도록 변경
    result = stub_analyze(req.url)
    
    result["latency_ms"] = int((time.time() - start) * 1000)
    return result