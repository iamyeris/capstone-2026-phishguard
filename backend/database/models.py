from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ScanResult(Base):
    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), index=True, nullable=False)
    is_suspicious = Column(Boolean, nullable=False)
    risk_score = Column(Float, nullable=False)
    
    # 서버 시간 기준으로 분석된 시간이 자동 저장됩니다.
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
    
class Whitelist(Base):
    __tablename__ = "whitelist_domains"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(255), unique=True, index=True, nullable=False) # 예: "naver.com"
    description = Column(String(255), nullable=True) # 예: "네이버 공식 포털"
    created_at = Column(DateTime(timezone=True), server_default=func.now())