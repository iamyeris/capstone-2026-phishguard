from typing import Optional
from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    url: str                # 분석할 URL
    text: Optional[str] = None  # (선택) 분석할 텍스트 내용
    
class ReportRequest(BaseModel):
    url: str
    reason: Optional[str] = "사용자 직접 신고"
