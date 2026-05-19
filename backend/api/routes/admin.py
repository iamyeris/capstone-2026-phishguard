import os
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db, redis_client
from database.models import Whitelist

router = APIRouter()

# 📂 [경로 수정] 서버 실행 위치에 상관없이 templates 폴더를 정확히 잡도록 절대 경로로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))  # backend/api/routes
backend_dir = os.path.dirname(os.path.dirname(current_dir))  # backend
templates_dir = os.path.join(backend_dir, "templates")  # backend/templates

templates = Jinja2Templates(directory=templates_dir)

class DomainRequest(BaseModel):
    domain: str
    description: str

# 1. 🖥️ 관리자 웹페이지 화면 띄워주기
@router.get("/", response_class=HTMLResponse)
async def get_admin_page(request: Request):
    # 🟢 [버그 수정] 최신 FastAPI 스펙에 맞게 request와 name을 키워드 인자로 명확히 지정합니다.
    return templates.TemplateResponse(request=request, name="admin.html")

# 2. 📊 화이트리스트 목록 조회 API
@router.get("/api/whitelist")
async def get_whitelist(db: Session = Depends(get_db)):
    items = db.query(Whitelist).order_by(Whitelist.id.desc()).all()
    return [{"domain": item.domain, "description": item.description} for item in items]

# 3. ➕ 화이트리스트 실시간 추가 (DB + Redis 동시 업데이트)
@router.post("/api/whitelist")
async def add_whitelist(req: DomainRequest, db: Session = Depends(get_db)):
    domain_clean = req.domain.lower().replace("https://", "").replace("http://", "").replace("www.", "")
    
    # DB에 중복 확인
    exists = db.query(Whitelist).filter(Whitelist.domain == domain_clean).first()
    if exists:
        raise HTTPException(status_code=400, detail="이미 존재하는 도메인입니다.")

    try:
        # [1] SQLite 영구 장부에 추가
        new_domain = Whitelist(domain=domain_clean, description=req.description)
        db.add(new_domain)
        db.commit()
        
        # [2] Redis 메모리에 즉시 반영 (무중단 업데이트의 핵심!)
        await redis_client.sadd("phishguard:whitelist", domain_clean)
        
        return {"status": "success", "msg": f"{domain_clean} 추가 완료"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# 4. 🗑️ 화이트리스트 실시간 삭제
@router.delete("/api/whitelist/{domain}")
async def delete_whitelist(domain: str, db: Session = Depends(get_db)):
    item = db.query(Whitelist).filter(Whitelist.domain == domain).first()
    if not item:
        raise HTTPException(status_code=404, detail="도메인을 찾을 수 없습니다.")

    try:
        # [1] SQLite 영구 장부에서 삭제
        db.delete(item)
        db.commit()
        
        # [2] Redis 메모리에서 즉시 삭제
        await redis_client.srem("phishguard:whitelist", domain)
        
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))