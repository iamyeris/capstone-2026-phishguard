from fastapi import APIRouter
import time
import asyncio

from schemas.payload import AnalyzeRequest
from services.crawler import fetch_page_info
from services.gemini import generate_security_report
from services.interface import analyze_text_with_ai 

router = APIRouter()

def stub_analyze(url: str) -> dict:
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

@router.post("/")
async def analyze_url(req: AnalyzeRequest):
    start = time.time()
    print(f"🔍 [STEP 1] 분석 시작: {req.url}")
    
    # ------------------------------------------------------------------
    # ⚡️ [스마트 라우팅 1] 검증된 공식 도메인 즉시 통과
    # ------------------------------------------------------------------
    safe_domains = ["naver.com", "google.com", "daum.net", "github.com"]
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

    # 1. 병렬 실행 (크롤링 시작)
    crawl_task = asyncio.create_task(fetch_page_info(req.url))
    
    # 2. 크롤링 도는 동안 1차 분석 완료하기
    result = stub_analyze(req.url)
    
    # 3. 크롤링 끝날 때까지 대기
    page_data = await crawl_task
    
    site_text_for_ai = ""
    if page_data["error"]:
        print(f"⚠️ 크롤링 에러: {page_data['error']}")
        result["one_line"] = f"사이트 접속 실패: {page_data['error']}"
        result["screenshot"] = {"type": "none", "value": ""}
    else:
        print("✅ 크롤링 성공! 스크린샷 확보 완료.")
        result["screenshot"] = {"type": "base64", "value": page_data["screenshot_base64"]}
        site_text_for_ai = page_data["text"]

    # 4. PyTorch AI 텍스트 모델 추론 (Non-Blocking으로 실행!)
    if not page_data["error"] and site_text_for_ai.strip():
        print("🧠 PyTorch AI 모델 텍스트 추론 중...")
        ai_result = await asyncio.to_thread(analyze_text_with_ai, site_text_for_ai)
        
        if ai_result["risk_score"] > result["risk_score"]:
            result["risk_score"] = ai_result["risk_score"]
            result["label"] = ai_result["label"]
            result["one_line"] = "AI 분석 결과, 위험 요소가 감지되었습니다!"
        
        result["evidence"]["model"] = {
            "name": "PhishGuard-BERT", 
            "version": "v0.1-mock", 
            "score": ai_result["risk_score"]
        }

    # 5. Gemini API 리포트 생성 (위험할 때만!)
    if result["risk_score"] >= 40:
        print("🤖 위험 감지됨! Gemini AI 상세 리포트 생성 중...")
        img_data = result["screenshot"]["value"] if result["screenshot"]["type"] == "base64" else ""
        
        gemini_report = await generate_security_report(
            url=req.url, 
            risk_score=result["risk_score"], 
            site_text=site_text_for_ai,
            screenshot_base64=img_data
        )
    else:
        gemini_report = "위험 요소가 발견되지 않아 상세 리포트를 생략합니다. 개인정보 입력 시에만 주의해 주세요."
    
    result["gemini_report"] = gemini_report
    result["latency_ms"] = int((time.time() - start) * 1000)
    
    return result