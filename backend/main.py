import os
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import torch

from api.routes import analyze, report, admin, dashboard
from services.interface import PhishGuardAnalyzer
from database.connection import SessionLocal, redis_client
from database.models import Whitelist

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 서버 시작 중... AI 모델 로드 준비")
    # ⭐️ 전역 변수가 아닌 app.state에 모델을 탑재합니다.
    app.state.ai_analyzer = PhishGuardAnalyzer()
    
    # 📥 [통합] 서버가 시작될 때 SQLite의 화이트리스트를 Redis 메모리로 로드합니다.
    print("📥 SQLite 화이트리스트 데이터를 Redis에 로드하는 중...")
    db = SessionLocal()
    try:
        domains = db.query(Whitelist.domain).all()
        domain_list = [d[0] for d in domains]
        
        if domain_list:
            await redis_client.delete("phishguard:whitelist")
            await redis_client.sadd("phishguard:whitelist", *domain_list)
            print(f"✅ 화이트리스트 {len(domain_list)}개 도메인이 Redis에 성공적으로 로드되었습니다!")
        else:
            print("ℹ️ DB에 등록된 화이트리스트가 없습니다.")
    except Exception as e:
        print(f"⚠️ 화이트리스트 로드 실패: {e}")
    finally:
        db.close()
    
    yield 
    
    print("🛑 서버 종료 중... 메모리 정리")
    app.state.ai_analyzer = None

# 🟢 딱 한 번만 깔끔하게 app 선언!
app = FastAPI(title="PhishGuard API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(analyze.router, prefix="/analyze", tags=["Analyze"])
app.include_router(report.router, prefix="/report", tags=["Report"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

@app.get("/health")
def health():
    return {"status": "ok"}

print("🔥🔥🔥 이 코드가 터미널에 안 뜨면 다른 파일을 실행 중인 겁니다! 🔥🔥🔥")
print(f"현재 등록된 주소 개수: {len(app.routes)}")