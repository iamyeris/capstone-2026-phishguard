from fastapi import APIRouter, Request, HTTPException
import time
import asyncio

from schemas.payload import AnalyzeRequest
from services.crawler import fetch_page_info
from services.gemini import generate_security_report
# 기존 개별 함수 호출 대신 인터페이스 구조를 활용하기 위해 import 수정 가능

router = APIRouter()

def stub_analyze(url: str) -> dict:
    """기본 규칙 기반 1차 스크리닝 (Stub 로직)"""
    url_lower = url.lower()
    hits = []
    checks = []

    https_ok = url_lower.startswith("https://")
    checks.append({"key": "https", "name": "HTTPS 사용", "pass": https_ok})

    risk_score = 10
    label = "NORMAL"
    one_line = "특이 패턴이 없습니다. 그래도 개인정보 입력은 주의하세요."

    # 키워드 기반 단순 필터링
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

@router.post("/")
async def analyze_url(req: AnalyzeRequest, request: Request):
    """
    URL 분석 통합 엔드포인트
    - request: FastAPI Request 객체를 통해 app.state에 접근합니다.
    """
    start = time.time()
    print(f"🔍 [STEP 1] 분석 시작: {req.url}")
    
    # ------------------------------------------------------------------
    # ⚡️ [스마트 라우팅 1] 검증된 공식 도메인 즉시 통과
    # ------------------------------------------------------------------
    safe_domains = ["naver.com", "google.com", "daum.net", "github.com", "apple.com"]
    if any(domain in req.url.lower() for domain in safe_domains):
        return {
            "label": "NORMAL",
            "risk_score": 5,
            "one_line": "검증된 안전한 공식 사이트입니다.",
            "screenshot": {"type": "none", "value": ""},
            "checks": [{"key": "whitelist", "name": "공식 사이트", "pass": True}],
            "evidence": {"model": {"name": "whitelist", "version": "1.0", "score": 0.0}, "rules": {"version": "1.0", "hits": []}},
            "gemini_report": "안전이 보장된 공식 도메인이므로 상세 AI 분석을 생략합니다. 안심하고 이용하세요.",
            "latency_ms": int((time.time() - start) * 1000)
        }

    # ------------------------------------------------------------------
    # ⚙️ [준비] main.py에서 로드한 AI 분석기 가져오기
    # ------------------------------------------------------------------
    ai_analyzer = request.app.state.ai_analyzer

    # 1. 병렬 실행 시작 (크롤링 task 생성)
    crawl_task = asyncio.create_task(fetch_page_info(req.url))
    
    # 2. 크롤링이 도는 동안 CPU를 사용하는 1차 규칙 분석(Stub) 수행
    result = stub_analyze(req.url)
    
    # 3. 크롤링 결과 대기
    page_data = await crawl_task
    
    site_text_for_ai = ""
    if page_data["error"]:
        print(f"⚠️ 크롤링 에러: {page_data['error']}")
        result["one_line"] = f"사이트 접속 실패: {page_data['error']}"
        result["screenshot"] = {"type": "none", "value": ""}
    else:
        print("✅ 크롤링 성공! 데이터 확보 완료.")
        result["screenshot"] = {"type": "base64", "value": page_data["screenshot_base64"]}
        site_text_for_ai = page_data["text"]

    # 4. 🧠 PyTorch AI 모델 텍스트 추론 (메모리에 로드된 모델 활용)
    if not page_data["error"] and site_text_for_ai.strip():
        print("🧠 PhishGuard-BERT 모델 추론 중...")
        
        # 모델 추론은 무거운 작업이므로 asyncio.to_thread를 사용하여 이벤트 루프를 방해하지 않습니다.
        # ai_analyzer.analyze_text는 PhishGuardAnalyzer 클래스 내부의 메서드라고 가정합니다.
        ai_result = await asyncio.to_thread(ai_analyzer.analyze, site_text_for_ai)
        
        # 더 높은 위험 점수가 나오면 업데이트
        if ai_result["risk_score"] > result["risk_score"]:
            result["risk_score"] = ai_result["risk_score"]
            result["label"] = ai_result["label"]
            result["one_line"] = "AI 정밀 분석 결과, 위험 요소가 감지되었습니다!"
        
        result["evidence"]["model"] = {
            "name": "PhishGuard-BERT", 
            "version": "v0.1-stable", 
            "score": ai_result["risk_score"]
        }

    # 5. 🤖 Gemini API 리포트 생성 (위험도가 중간 이상일 때만 호출)
    if result["risk_score"] >= 40:
        print("🤖 상세 분석 대상 선정! Gemini AI 리포트 생성 중...")
        img_data = result["screenshot"]["value"] if result["screenshot"]["type"] == "base64" else ""
        
        # Gemini 분석 호출 (비동기)
        gemini_report = await generate_security_report(
            url=req.url, 
            risk_score=result["risk_score"], 
            site_text=site_text_for_ai,
            screenshot_base64=img_data
        )
    else:
        gemini_report = "정밀 분석 결과 특이사항이 발견되지 않았습니다. 개인정보 보호 수칙을 준수해 주세요."
    
    # 최종 결과 조립
    result["gemini_report"] = gemini_report
    result["latency_ms"] = int((time.time() - start) * 1000)
    
    print(f"✨ [분석 완료] Score: {result['risk_score']} / Latency: {result['latency_ms']}ms")
    return result