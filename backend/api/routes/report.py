from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas.payload import ReportRequest
from models.database import get_db, Report

router = APIRouter()

@router.post("/")
def submit_report(req: ReportRequest, db: Session = Depends(get_db)):
    """
    사용자가 의심스러운 URL을 신고합니다.
    """
    new_report = Report(url=req.url, reason=req.reason)
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    
    return {"message": "신고가 성공적으로 접수되었습니다.", "report_id": new_report.id}