import os
import redis.asyncio as redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

# --- [1] SQLite 영구 저장소 세팅 ---
# backend 폴더 바로 아래에 phishguard.db 파일이 자동 생성됩니다.
SQLALCHEMY_DATABASE_URL = "sqlite:///./phishguard.db"

# SQLite는 기본적으로 다중 스레드 접속을 막기 때문에, FastAPI에서 쓰려면 check_same_thread 옵션을 꺼줘야 합니다.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 서버 시작 시 데이터베이스 테이블 자동 생성 (최초 1회)
Base.metadata.create_all(bind=engine)

# FastAPI 라우터에서 사용할 DB 세션 의존성(Dependency) 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- [2] Redis 단기 메모리 캐시 세팅 ---
# 도커 환경인지, 로컬 환경인지에 따라 Redis 호스트 주소를 자동으로 결정합니다.
# 도커로 실행 시 docker-compose.yml에 정의된 서비스 이름인 'redis'를 사용하고,
# 로컬에서 단독 실행 시 'localhost'를 사용합니다.
REDIS_HOST = os.getenv("REDIS_HOST", "redis")

# 터미널에서 redis-server가 켜져 있어야 정상 작동합니다.
# decode_responses=True로 설정하면 바이트가 아닌 문자열로 데이터를 깔끔하게 주고받습니다.
redis_client = redis.Redis(
    host=REDIS_HOST, 
    port=6379, 
    db=0, 
    decode_responses=True
)