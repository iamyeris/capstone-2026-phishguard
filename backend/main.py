from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import torch

# 방금 만든 라우터 불러오기
from api.routes import analyze

ml_models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 서버 시작 중... AI 모델 로드 준비")
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"🖥️  Using device: {device}")
    yield 
    print("🛑 서버 종료 중... 메모리 정리")
    ml_models.clear()

app = FastAPI(title="PhishGuard API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록! /analyze 로 들어오는 모든 요청을 analyze.py 로 넘김
app.include_router(analyze.router, prefix="/analyze", tags=["Analyze"])

@app.get("/health")
def health():
    return {"status": "ok"}