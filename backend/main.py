from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import torch

# 라우터 및 서비스 불러오기
from api.routes import analyze, report
from services.interface import PhishGuardAnalyzer

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 서버 시작 중... AI 모델 로드 준비")
    # ⭐️ 핵심: 전역 변수가 아닌 app.state에 모델을 탑재합니다.
    # 이렇게 해야 워커(Worker) 충돌 없이 안전하게 메모리를 관리할 수 있습니다.
    app.state.ai_analyzer = PhishGuardAnalyzer()
    
    yield 
    
    print("🛑 서버 종료 중... 메모리 정리")
    app.state.ai_analyzer = None

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
app.include_router(report.router, prefix="/report", tags=["Report"]) # report 라우터 추가!

@app.get("/health")
def health():
    return {"status": "ok"}