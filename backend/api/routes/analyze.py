import time
import asyncio
import json
import re
import os
import joblib
import pandas as pd
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

# 기존 모듈
from schemas.payload import AnalyzeRequest
from services.crawler import fetch_page_info
from services.gemini import generate_security_report
from services.interface import dashboard_manager
from database.connection import get_db, redis_client
from database.models import ScanLog, ReportLog 

import whois
from datetime import datetime, timedelta
import urllib.parse

router = APIRouter()

# ---------------------------------------------------------
# 🚀 1. 점수 양극화 함수
# ---------------------------------------------------------
def polarize_score(score: int) -> int:
    if score <= 30: return max(5, int(score * 0.5))
    elif score >= 70: return min(99, score + 15)
    else: return min(85, score + 25) if score >= 50 else max(15, score - 20) 

# ---------------------------------------------------------
# 🚀 2. 에러 메시지 정제 함수
# ---------------------------------------------------------
def clean_error_message(err_str: str) -> str:
    if not err_str: return "알 수 없는 오류"
    err_lower = err_str.lower()
    if "err_name_not_resolved" in err_lower: return "도메인(DNS)을 찾을 수 없습니다."
    if "err_connection_timed_out" in err_lower or "timeout" in err_lower: return "서버 응답 시간 초과"
    if "err_connection_refused" in err_lower: return "서버에서 연결을 거부했습니다."
    if "invalid url" in err_lower: return "유효하지 않은 URL 형식입니다."
    if "err_cert" in err_lower: return "보안 인증서(SSL) 오류"
    clean_str = err_str.split("Call log:")[0].split(" at ")[0].replace("Page.goto:", "").strip()
    return clean_str if len(clean_str) < 40 else clean_str[:37] + "..."

# ---------------------------------------------------------
# 🚀 3. URL 기반 1차 임시 분류 (빠른 응답용)
# ---------------------------------------------------------
def determine_threat_type(url: str, is_malware_ext: bool) -> str:
    url_lower = url.lower()
    if is_malware_ext: return "Malware"
    if any(kw in url_lower for kw in ['casino', 'toto', 'bet', 'gamble', 'slot', 'race']): return "Gambling"
    if any(kw in url_lower for kw in ['porn', 'sex', 'xxx', 'adult', 'av']): return "Adult"
    if any(kw in url_lower for kw in ['gov', 'police', 'minwon', 'hometax', 'scourt']): return "Impersonation"
    if any(kw in url_lower for kw in ['bank', 'card', 'loan', 'pay', 'finance', 'kb', 'shinhan']): return "Financial"
    return "Phishing"

# ---------------------------------------------------------
# 🚀 4. [NEW] 제미나이 리포트 기반 최종 분류 (진짜 결론 도출)
# ---------------------------------------------------------
def extract_label_from_gemini(report_text: str, default_label: str) -> str:
    if not report_text: return default_label
    
    # 띄어쓰기를 무시하고 제미나이의 문맥 키워드를 검사합니다.
    text = report_text.lower().replace(" ", "") 
    
    if any(k in text for k in ["gambling", "불법도박", "도박", "카지노", "토토", "사설"]): return "Gambling"
    if any(k in text for k in ["adult", "유해콘텐츠", "음란", "성인물", "19금"]): return "Adult"
    if any(k in text for k in ["impersonation", "기관사칭", "공공기관", "정부기관", "사칭"]): return "Impersonation"
    if any(k in text for k in ["financial", "금융사기", "대출사기", "은행사칭", "투자사기"]): return "Financial"
    if any(k in text for k in ["malware", "악성코드", "랜섬웨어", "바이러스", "apk"]): return "Malware"
    if any(k in text for k in ["safe", "정상", "안전한사이트", "위험성없음", "안전합니다"]): return "Safe"
    if any(k in text for k in ["unknown", "판단보류", "분석불가"]): return "Unknown"
    if any(k in text for k in ["phishing", "일반피싱", "피싱사이트", "계정탈취"]): return "Phishing"
    
    return default_label # 매칭되는 키워드가 없으면 1차로 판별한 라벨 유지

# ---------------------------------------------------------
# 🌲 랜덤 포레스트 모델 로드
# ---------------------------------------------------------
RF_MODEL_PATH = "/app/weights/phishguard_rf_model.pkl" 
try:
    rf_model = joblib.load(RF_MODEL_PATH)
except Exception:
    rf_model = None

# ---------------------------------------------------------
# 🔍 URL 특징 추출 함수
# ---------------------------------------------------------
def extract_features(url: str) -> dict:
    url_lower = url.lower()
    features = {
        'url_length': len(url), 'domain_length': 0, 'num_dots': 0, 'num_hyphens': 0,
        'has_at_symbol': 0, 'is_ip_address': 0, 'has_suspicious_keyword': 0,
        'has_malware_ext': 0, 'is_trusted_cloud': 0
    }
    try:
        parsed = urllib.parse.urlparse(url_lower if "://" in url_lower else f"http://{url_lower}")
        domain = parsed.netloc
        features['domain_length'] = len(domain)
        features['num_dots'] = domain.count('.')
        features['num_hyphens'] = domain.count('-')
        features['has_at_symbol'] = 1 if '@' in parsed.netloc else 0
        features['is_ip_address'] = 1 if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", domain.split(':')[0]) else 0
        trusted_clouds = ['googleusercontent.com', 'amazonaws.com', 'cloudfront.net', 'github.io']
        features['is_trusted_cloud'] = 1 if any(domain.endswith(c) for c in trusted_clouds) else 0
    except Exception: pass
    suspicious_keywords = ['login', 'verify', 'update', 'account', 'secure', 'banking', 'confirm', 'free']
    features['has_suspicious_keyword'] = 1 if any(kw in url_lower for kw in suspicious_keywords) else 0
    malware_extensions = ['.apk', '.exe', '.zip', '.rar', '.bin']
    features['has_malware_ext'] = 1 if any(url_lower.endswith(ext) for ext in malware_extensions) else 0
    return features

# ---------------------------------------------------------
# 🌟 메인 엔드포인트
# ---------------------------------------------------------
@router.post("/")
async def analyze_url(req: AnalyzeRequest, request: Request, db: Session = Depends(get_db)):
    
    async def event_generator():
        start = time.time()
        target_url = req.url.strip().lower()
        
        await dashboard_manager.broadcast_status(step="1단계", msg=f"분석 요청 수신. 검증 파이프라인 가동... ({target_url[:25]}...)", active_nodes=["node-req", "node-cache"])

        parsed_domain = urllib.parse.urlparse(target_url if "://" in target_url else f"http://{target_url}").netloc
        parsed_domain = parsed_domain.replace("www.", "")
        
        # 🚀 1. 블랙리스트 검증
        if await redis_client.sismember("phishguard:blacklist", parsed_domain):
            await dashboard_manager.broadcast_status(step="완료", msg="☠️ 블랙리스트 즉시 차단!", status="done", done_nodes=["node-req", "node-cache"])
            fast_result = {
                "status": "complete", "label": "Phishing", "risk_score": 100, "is_suspicious": True,
                "one_line": "🚨 관제 센터에 의해 영구 차단된 치명적인 악성 사이트입니다. 절대 접속하지 마세요!",
                "checks": [], "reasons": ["☠️ PhishGuard 블랙리스트에 등록된 위험 도메인입니다."],
                "gemini_report": "관제 센터에 의해 강제 차단된 도메인이므로 심층 AI 분석을 생략합니다.", 
                "latency_ms": int((time.time() - start) * 1000)
            }
            try:
                db.add(ScanLog(url=target_url, is_suspicious=True, risk_score=100, full_result=json.dumps(fast_result)))
                db.commit()
            except Exception: pass
            yield f"data: {json.dumps(fast_result)}\n\n"
            return

        # 🚀 2. 화이트리스트 검증
        if await redis_client.sismember("phishguard:whitelist", parsed_domain):
            await dashboard_manager.broadcast_status(step="완료", msg="✅ 화이트리스트 통과!", status="done", done_nodes=["node-req", "node-cache"])
            fast_result = {
                "status": "complete", "label": "Safe", "risk_score": 0, "is_suspicious": False,
                "one_line": "✅ PhishGuard 관제 센터에서 안전성을 100% 보장하는 공식 사이트입니다.",
                "checks": [], "reasons": ["🛡️ PhishGuard 화이트리스트 검증을 통과했습니다."],
                "gemini_report": "안전성이 검증된 공식 도메인이므로 심층 AI 분석을 생략합니다.", 
                "latency_ms": int((time.time() - start) * 1000)
            }
            try:
                db.add(ScanLog(url=target_url, is_suspicious=False, risk_score=0, full_result=json.dumps(fast_result)))
                db.commit()
            except Exception: pass
            yield f"data: {json.dumps(fast_result)}\n\n"
            return

        # 🚀 3. 캐시 통과
        redis_key = f"phishguard:cache:{target_url}"
        try:
            cached_result = await redis_client.get(redis_key)
            if cached_result:
                await dashboard_manager.broadcast_status(step="완료", msg="⚡️ Redis 캐시 Hit!", status="done", done_nodes=["node-req", "node-cache"])
                fast_result = json.loads(cached_result)
                fast_result["status"] = "complete"
                try:
                    db.add(ScanLog(url=target_url, is_suspicious=fast_result.get("is_suspicious", False), risk_score=fast_result.get("risk_score", 0), full_result=cached_result))
                    db.commit()
                except Exception: pass
                yield f"data: {json.dumps(fast_result)}\n\n"
                return
        except Exception: pass

        await dashboard_manager.broadcast_status(step="2단계", msg="Cache Miss! 🌲 RF & 🧠 BERT 병렬 채점 시작...", done_nodes=["node-req", "node-cache"], active_nodes=["node-bert", "node-crawl"])
        
        ai_analyzer = request.app.state.ai_analyzer
        crawl_task = asyncio.create_task(fetch_page_info(target_url))
        
        rf_risk_score = 50 
        rf_hits, reasons, checks = [], [], []
        
        if rf_model:
            features = extract_features(target_url)
            proba = rf_model.predict_proba(pd.DataFrame([features]))[0] 
            rf_risk_score = int((1.0 - proba[0]) * 100)
            
            if features['url_length'] >= 70: reasons.append("⚠️ URL 길이가 비정상적으로 깁니다.")
            if features['num_dots'] >= 3: reasons.append("⚠️ 서브도메인을 과도하게 사용했습니다.")
            if features['is_ip_address'] == 1: 
                reasons.append("🚨 IP 주소가 직접 노출되어 위험합니다.")
                rf_hits.append("IP Address Detected")
            if features['has_suspicious_keyword'] == 1: reasons.append("⚠️ 탈취를 유도하는 의심 키워드가 포함되어 있습니다.")
            if features['has_malware_ext'] == 1: reasons.append("🚨 악성코드 설치 확장자가 포함되어 있습니다.")
            if features['is_trusted_cloud']: rf_hits.append("Trusted Cloud Infra")
        
        ai_result = await asyncio.to_thread(ai_analyzer.predict, target_url)
        bert_score = int(ai_result.get("risk_score", 0))
        
        raw_final_score = int((rf_risk_score * 0.3) + (bert_score * 0.7))
        final_1st_score = polarize_score(raw_final_score)
        
        if "Trusted Cloud Infra" in rf_hits:
            final_1st_score = min(final_1st_score, 15)
            reasons.append("✅ 글로벌 클라우드 인프라 주소로 확인되어 안전 처리되었습니다.")
        if any(portal in parsed_domain for portal in ["naver.com", "daum.net", "google.com"]):
            final_1st_score = min(final_1st_score, 10)
            reasons.append("✅ 검증된 대형 포털 공식 도메인으로 확인되어 안전 처리되었습니다.")

        # 1차 임시 분류 (빠른 스트리밍 응답용)
        if final_1st_score >= 40:
            label_status = determine_threat_type(target_url, features['has_malware_ext'] == 1)
            one_line_msg = f"⚡️ 1차 AI 위험도 점수 산출 완료. 상세 분석 진행 중... (위험도: {final_1st_score}점)"
        else:
            label_status = "Safe"
            one_line_msg = "✅ 보안 검사를 통과한 안전한 사이트입니다."

        result = {
            "label": label_status, "risk_score": final_1st_score, "is_suspicious": final_1st_score >= 40,
            "one_line": one_line_msg, "screenshot": {"type": "none", "value": ""},
            "checks": checks, "reasons": reasons,
            "evidence": { "model": {"name": "PhishGuard-RF-Ensemble", "version": "v2.0", "rf_score": rf_risk_score, "bert_score": bert_score}, "rules": {"hits": rf_hits} }
        }
        
        first_chunk = result.copy()
        first_chunk["status"] = "processing"
        yield f"data: {json.dumps(first_chunk)}\n\n"

        # 🕸️ 3단계: 크롤러 에러 시 예외 처리
        page_data = await crawl_task
        
# ---------------------------------------------------------
        # 🕸️ 3단계: 크롤러 에러 시 예외 처리 (수정된 버전)
        # ---------------------------------------------------------
        page_data = await crawl_task
        
        if page_data["error"]:
            clean_err = clean_error_message(page_data["error"]) 
            
            await dashboard_manager.broadcast_status(
                step="완료", 
                msg=f"접속 불가 사이트 ({clean_err})", 
                status="done", 
                done_nodes=["node-req", "node-cache", "node-bert", "node-crawl", "node-db"]
            )
            
            # 🚀 [수정] 접속 불가 시 위험도 점수가 낮아도 무조건 'Unknown' 라벨 부여
            result["status"] = "complete"
            result["label"] = "Unknown" 
            result["is_suspicious"] = False
            result["one_line"] = f"⚠️ 사이트에 접속할 수 없습니다. ({clean_err})"
            result["gemini_report"] = f"웹사이트 접속에 실패({clean_err})하여 페이지 렌더링 및 심층 AI 분석을 진행할 수 없습니다."
            
            try:
                db.add(ScanLog(
                    url=target_url, 
                    is_suspicious=result.get("is_suspicious", False), 
                    risk_score=result["risk_score"],
                    full_result=json.dumps(result)
                ))
                db.commit()
                await redis_client.set(name=redis_key, value=json.dumps(result), ex=86400)
            except Exception as e: pass
                
            yield f"data: {json.dumps(result)}\n\n"
            return

        result["screenshot"] = {"type": "base64", "value": page_data["screenshot_base64"]}
        site_text_for_ai = page_data["text"]

        await dashboard_manager.broadcast_status(step="3단계", msg=f"병렬 분석 완료. Gemini 리포트 판독 중...", done_nodes=["node-bert", "node-crawl"], active_nodes=["node-db", "node-gemini"])

        # 🚀 [핵심] 제미나이가 내린 최종 판결로 라벨 덮어쓰기!
        if result["risk_score"] >= 40:
            gemini_report = await generate_security_report(url=target_url, risk_score=result["risk_score"], site_text=site_text_for_ai, screenshot_base64=result["screenshot"]["value"])
            
            # 제미나이의 문맥을 읽어 최종 분류 확정
            final_label = extract_label_from_gemini(gemini_report, result["label"])
            result["label"] = final_label
            
            # 확정된 라벨에 맞춰 한줄 요약도 완벽하게 교체
            if final_label == "Impersonation": result["one_line"] = f"🚨 공공기관 사칭이 의심됩니다. (위험도: {result['risk_score']}점)"
            elif final_label == "Financial": result["one_line"] = f"🚨 금융/대출 사기 위험이 감지되었습니다. (위험도: {result['risk_score']}점)"
            elif final_label == "Malware": result["one_line"] = f"🚨 악성코드 다운로드 위험이 있습니다. (위험도: {result['risk_score']}점)"
            elif final_label == "Gambling": result["one_line"] = f"🚨 불법 도박 사이트로 의심됩니다. (위험도: {result['risk_score']}점)"
            elif final_label == "Adult": result["one_line"] = f"🚨 유해 콘텐츠 사이트입니다. (위험도: {result['risk_score']}점)"
            elif final_label == "Unknown": result["one_line"] = f"⚠️ 위험 요소가 모호하여 판단이 보류되었습니다. (위험도: {result['risk_score']}점)"
            elif final_label == "Safe": 
                result["one_line"] = "✅ 제미나이 정밀 검사 결과 안전한 사이트로 판명되었습니다."
                result["is_suspicious"] = False
            else: result["one_line"] = f"🚨 일반 피싱 및 계정 탈취 위험이 감지되었습니다. (위험도: {result['risk_score']}점)"
        else:
            gemini_report = "정밀 분석 결과 특이사항이 발견되지 않았습니다."
        
        result["gemini_report"] = gemini_report
        result["latency_ms"] = int((time.time() - start) * 1000)
        result["status"] = "complete" 
        
        try:
            db.add(ScanLog(url=target_url, is_suspicious=result.get("is_suspicious", False), risk_score=result["risk_score"], full_result=json.dumps(result)))
            db.commit()
            await redis_client.set(name=redis_key, value=json.dumps(result), ex=86400)
        except Exception as e: pass

        await dashboard_manager.broadcast_status(step="완료", msg=f"✨ 파이프라인 완주! 클라이언트로 최종 리포트 반환 완료.", status="done", done_nodes=["node-db", "node-gemini"])
        yield f"data: {json.dumps(result)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ---------------------------------------------------------
# 🚨 사용자 신고 접수 API
# ---------------------------------------------------------
class ReportRequest(BaseModel):
    url: str
    reason: Optional[str] = None 

@router.post("/report/")
async def report_url(req: ReportRequest, db: Session = Depends(get_db)):
    target_url = req.url.strip().lower()
    report_count_key = f"phishguard:report_count:{target_url}"
    cache_key = f"phishguard:cache:{target_url}"
    try:
        new_count = await redis_client.incr(report_count_key)
        await dashboard_manager.broadcast_status(step="신고 DB", msg=f"사용자 신고 접수됨! (현재 {new_count}회 누적)", active_nodes=["node-db"])
        if new_count >= 5: await redis_client.delete(cache_key)
        existing_report = db.query(ReportLog).filter(ReportLog.url == target_url).first()
        if existing_report:
            existing_report.report_count = new_count
            if req.reason: existing_report.reason = req.reason 
        else:
            db.add(ReportLog(url=target_url, reason=req.reason, report_count=new_count))
        db.commit()
        return {"status": "success", "msg": f"신고가 접수되었습니다.", "current_count": new_count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))