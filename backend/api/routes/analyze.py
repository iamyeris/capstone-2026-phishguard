from fastapi import APIRouter
import time
from schemas.payload import AnalyzeRequest
from services.crawler import fetch_page_info
from services.gemini import generate_security_report # ⭐️ 추가됨!

router = APIRouter()

# ... (기존에 있던 def stub_analyze 부분은 그대로 둡니다) ...

@router.post("/")
async def analyze_url(req: AnalyzeRequest):
    start = time.time()
    
    print(f"🔍 URL 크롤링 시작: {req.url}")
    # 1. 크롤러로 사이트 접속 (텍스트 & 스크린샷 획득)
    page_data = await fetch_page_info(req.url)
    
    # 2. 1차 분석 (현재는 stub 룰 기반, 추후 PyTorch 교체)
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

    # 4. ⭐️ Gemini API 호출하여 리포트 생성 (새로 추가된 부분!)
    print("🤖 Gemini AI 리포트 생성 중...")
    gemini_report = await generate_security_report(
        url=req.url, 
        risk_score=result["risk_score"], 
        site_text=site_text_for_ai
    )
    # 최종 결과에 AI 리포트 항목 추가
    result["gemini_report"] = gemini_report
    
    result["latency_ms"] = int((time.time() - start) * 1000)
    return result