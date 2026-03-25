from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    url: str
    user_id: str = "anonymous"

class ReportRequest(BaseModel):
    url: str
    reason: str