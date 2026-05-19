import time
import asyncio
import json
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

# 기존 모듈
from schemas.payload import AnalyzeRequest
from services.crawler import fetch_page_info
from services.gemini import generate_security_report
from services.interface import dashboard_manager

# DB 및 Redis 모듈
from database.connection import get_db, redis_client
from database.models import ScanResult

import whois
from datetime import datetime, timedelta
import urllib.parse

def is_newly_created_domain(url: str) -> bool:
    try:
        domain = urllib.parse.urlparse(url if "://" in url else f"http://{url}").netloc
        if not domain: return False
        domain_info = whois.whois(domain)
        creation_date = domain_info.creation_date
        if isinstance(creation_date, list): creation_date = creation_date[0]
        if creation_date:
            age = datetime.now() - creation_date
            if age < timedelta(days=1): return True
    except Exception: pass
    return False

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
    return {
        "label": label, "risk_score": risk_score, "one_line": one_line,
        "screenshot": {"type": "none", "value": ""}, "checks": checks,
        "evidence": {"model": {"name": "stub", "version": "stub-v0", "score": 0.0}, "rules": {"version": "stub-v0", "hits": hits}},
        "latency_ms": 0,
    }

# 🌟 메인 엔드포인트 (스트리밍 완전 제거! 딜레이 추가!)
@router.post("/")
async def analyze_url(req: AnalyzeRequest, request: Request, db: Session = Depends(get_db)):
    start = time.time()
    target_url = req.url.strip().lower()
    print(f"🔍 [STEP 1] 분석 시작: {target_url}")
    
    # 📢 [대시보드] 1단계
    await dashboard_manager.broadcast_status(
        step="1단계", msg=f"분석 요청 수신. Redis 캐시 검증 중... ({target_url[:25]}...)", 
        active_nodes=["node-req", "node-cache"]
    )
    await asyncio.sleep(1.0) # 🎬 시연용 1초 대기

    # --- Fast Paths ---
    parsed_domain = urllib.parse.urlparse(req.url if "://" in req.url else f"http://{req.url}").netloc
    parsed_domain = parsed_domain.replace("www.", "")
    if await redis_client.sismember("phishguard:whitelist", parsed_domain):
        await dashboard_manager.broadcast_status(step="완료", msg="✅ 화이트리스트 통과!", status="done", done_nodes=["node-req", "node-cache"])
        return {"label": "NORMAL", "risk_score": 5, "is_suspicious": False, "one_line": "안전한 공식 사이트입니다.", "latency_ms": int((time.time() - start) * 1000)}

    redis_key = f"phishguard:cache:{target_url}"
    try:
        cached_result = await redis_client.get(redis_key)
        if cached_result:
            await dashboard_manager.broadcast_status(step="완료", msg="⚡️ Redis 캐시 Hit!", status="done", done_nodes=["node-req", "node-cache"])
            return json.loads(cached_result)
    except Exception: pass

    # ------------------------------------------------------------------
    # 🧠 [정밀 분석] 2단계
    # ------------------------------------------------------------------
    await dashboard_manager.broadcast_status(
        step="2단계", msg="Cache Miss! 🧠 BERT 추론 및 🕸️ 크롤러 병렬 기동 시작...", 
        done_nodes=["node-req", "node-cache"], active_nodes=["node-bert", "node-crawl"]
    )
    await asyncio.sleep(2.0) # 🎬 시연용 2초 대기
    
    ai_analyzer = request.app.state.ai_analyzer
    crawl_task = asyncio.create_task(fetch_page_info(req.url))
    result = stub_analyze(req.url)
    
    ai_result = await asyncio.to_thread(ai_analyzer.predict, req.url)
    result["is_suspicious"] = ai_result.get("is_suspicious", False)
    if ai_result["risk_score"] > result["risk_score"]:
        result["risk_score"] = ai_result["risk_score"]
        result["one_line"] = "AI 정밀 분석 결과, 위험 요소가 감지되었습니다!"
    
    result["evidence"]["model"] = {"name": "PhishGuard-BERT", "version": "v0.1-stable", "score": ai_result["risk_score"]}
    
    page_data = await crawl_task
    site_text_for_ai = ""
    
    if page_data["error"]:
        await dashboard_manager.broadcast_status(step="완료", msg=f"접속 불가 사이트 ({page_data['error']})", status="done", done_nodes=["node-bert", "node-crawl", "node-db"])
        result["label"] = "UNKNOWN"
        result["risk_score"] = 0
        result["one_line"] = "접속할 수 없는 웹사이트입니다."
        return result

    result["screenshot"] = {"type": "base64", "value": page_data["screenshot_base64"]}
    site_text_for_ai = page_data["text"]

    # ------------------------------------------------------------------
    # 🤖 [DB 저장 및 Gemini 리포트] 3단계
    # ------------------------------------------------------------------
    await dashboard_manager.broadcast_status(
        step="3단계", msg=f"병렬 분석 완료 (AI 위험도: {result['risk_score']}점). DB 저장 및 Gemini 리포트 판독 중...", 
        done_nodes=["node-bert", "node-crawl"], active_nodes=["node-db", "node-gemini"]
    )
    await asyncio.sleep(2.0) # 🎬 시연용 2초 대기

    if result["risk_score"] >= 40:
        img_data = result["screenshot"]["value"] if result["screenshot"]["type"] == "base64" else ""
        gemini_report = await generate_security_report(url=req.url, risk_score=result["risk_score"], site_text=site_text_for_ai, screenshot_base64=img_data)
    else:
        gemini_report = "정밀 분석 결과 특이사항이 발견되지 않았습니다."
    
    result["gemini_report"] = gemini_report
    result["latency_ms"] = int((time.time() - start) * 1000)
    
    try:
        db.add(ScanResult(url=target_url, is_suspicious=result.get("is_suspicious", False), risk_score=result["risk_score"]))
        db.commit()
        await redis_client.set(name=redis_key, value=json.dumps(result), ex=86400)
    except Exception: pass

    # 📢 최종 완료 방송
    await dashboard_manager.broadcast_status(
        step="완료", msg=f"✨ 파이프라인 완주! 클라이언트로 최종 리포트 반환 완료.", 
        status="done", done_nodes=["node-db", "node-gemini"]
    )
    
    return result

class ReportRequest(BaseModel):
    url: str

@router.post("/report/")
async def report_url(req: ReportRequest):
    target_url = req.url.strip().lower()
    report_count_key = f"phishguard:report_count:{target_url}"
    cache_key = f"phishguard:cache:{target_url}"
    try:
        new_count = await redis_client.incr(report_count_key)
        await dashboard_manager.broadcast_status(step="신고 DB", msg=f"사용자 신고 접수됨! (현재 {new_count}회 누적)", active_nodes=["node-db"])
        if new_count >= 5:
            await redis_client.delete(cache_key)
        return {"status": "success", "msg": f"신고가 접수되었습니다.", "current_count": new_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))