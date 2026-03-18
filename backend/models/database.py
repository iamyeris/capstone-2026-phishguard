from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

# SQLite 데이터베이스 파일의 경로 설정 (로컬 환경)
SQLALCHEMY_DATABASE_URL = "sqlite:///./phishguard.db"

# 데이터베이스 엔진 생성
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 세션 생성 (데이터베이스 작업 단위)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 베이스 모델 정의 (모든 테이블은 이 클래스를 상속받습니다)
Base = declarative_base()

class Pattern(Base):
    """
    위험 URL 패턴을 저장하는 테이블
    """
    __tablename__ = "patterns"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True)      # 악성/의심 URL
    pattern_type = Column(String)                      # 패턴 유형 (예: PHISHING, GAMBLING 등)
    risk_score = Column(Integer, default=100)          # 해당 패턴의 위험도

class Report(Base):
    """
    사용자의 신고 내역을 저장하는 테이블
    """
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)                   # 사용자가 신고한 의심 URL
    reason = Column(String)                            # 사용자가 작성한 신고 사유
    is_processed = Column(Boolean, default=False)      # 관리자가 검토했는지 여부 (추후 확장용)

# 데이터베이스에 테이블 생성 (처음 실행 시 파일 생성됨)
Base.metadata.create_all(bind=engine)

def get_db():
    """
    각 API 요청마다 데이터베이스 세션을 제공하고 닫는 제너레이터
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()