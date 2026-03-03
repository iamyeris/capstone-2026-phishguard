from fastapi import APIRouter
import time
from schemas.payload import AnalyzeRequest
from services.crawler import fetch_page_info
from services.gemini import generate_security_report
from services.inference import analyze_text_with_ai # ⭐️ PyTorch 뼈대 불러오기 추가!

router = APIRouter()

def stub_analyze(url: str) -> dict:
    # (기존 팀장님이 짠 완벽한 URL 규칙 기반 더미 분석기 로직 그대로!)
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
    
    print(f"🔍 URL 크롤링 시작: {req.url}")
    # 1. 크롤러로 사이트 접속 (텍스트 & 스크린샷 획득)
    page_data = await fetch_page_info(req.url)
    
    # 2. 1차 분석 (URL 규칙 기반 - Stub)
    result = stub_analyze(req.url)
    
    # 3. 크롤링 결과 반영
    if page_data["error"]:
        print(f"⚠️ 크롤링 에러: {page_data['error']}")
        result["one_line"] = f"사이트 접속 실패: {page_data['error']}"
        result["screenshot"] = {"type": "none", "value": ""}
        site_text_for_ai = "사이트 접속 실패로 텍스트를 추출하지 못했습니다."
    else:
        print("✅ 크롤링 성공! 스크린샷 확보 완료.")
        result["screenshot"] = {"type": "base64", "value": page_data["screenshot_base64"]}
        site_text_for_ai = page_data["text"]

    # ------------------------------------------------------------------
    # ⭐️ 3-1. 하이브리드 결합: PyTorch 모델로 텍스트 분석 (새로 추가된 부분!)
    # ------------------------------------------------------------------
    if not page_data["error"]:
        print("🧠 PyTorch AI 모델 텍스트 추론 중...")
        ai_result = analyze_text_with_ai(site_text_for_ai)
        
        # URL 규칙 분석 점수와 텍스트 기반 AI 분석 점수 중 더 '위험한' 점수를 채택 (보수적 접근)
        if ai_result["risk_score"] > result["risk_score"]:
            result["risk_score"] = ai_result["risk_score"]
            result["label"] = ai_result["label"]
            result["one_line"] = "AI 텍스트 분석 결과, 위험 요소가 감지되었습니다. 주의하세요!"
        
        # 증거(evidence)에 AI 모델 결과도 남겨두기
        result["evidence"]["model"] = {
            "name": "PhishGuard-BERT", 
            "version": "v0.1-mock", 
            "score": ai_result["risk_score"]
        }
    # ------------------------------------------------------------------

    # 4. Gemini API 호출하여 리포트 생성
    print("🤖 Gemini AI 리포트 생성 중...")
    
    # Base64 데이터가 있으면 꺼내오고, 접속 실패로 없으면 빈 문자열("") 전달
    img_data = result["screenshot"]["value"] if result["screenshot"]["type"] == "base64" else ""
    
    gemini_report = await generate_security_report(
        url=req.url, 
        risk_score=result["risk_score"], 
        site_text=site_text_for_ai,
        screenshot_base64=img_data
    )
    
    # 최종 결과에 AI 리포트 항목 추가
    result["gemini_report"] = gemini_report
    
    result["latency_ms"] = int((time.time() - start) * 1000)
    return result