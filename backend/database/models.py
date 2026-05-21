from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
import os

# SQLite 데이터베이스 파일의 경로 설정
SQLALCHEMY_DATABASE_URL = "sqlite:///./phishguard.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ScanLog(Base):
    """🔍 사용자가 분석 요청한 URL 기록"""
    __tablename__ = "scan_logs"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    is_suspicious = Column(Boolean)
    risk_score = Column(Integer)
    # 분석 당시의 전체 결과(제미나이 리포트, 스크린샷 등)를 JSON 형태로 통째로 저장
    full_result = Column(Text, nullable=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ReportLog(Base):
    """🚨 사용자가 피싱이라고 신고한 기록"""
    __tablename__ = "report_logs"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    # 사용자의 신고 사유 저장
    reason = Column(String, nullable=True)
    report_count = Column(Integer, default=1) # 누적 신고 횟수
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Whitelist(Base):
    """✅ 무조건 안전한 사이트 (네이버, 구글 등)"""
    __tablename__ = "whitelist"
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Blacklist(Base):
    """☠️ 무조건 차단할 악성 사이트"""
    __tablename__ = "blacklist"
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# DB에 테이블 생성
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()