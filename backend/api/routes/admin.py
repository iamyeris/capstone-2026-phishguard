import os
import json
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db, redis_client
from database.models import Whitelist, ScanLog, ReportLog, Blacklist

router = APIRouter()

current_dir = os.path.dirname(os.path.abspath(__file__))  
backend_dir = os.path.dirname(os.path.dirname(current_dir))  
templates_dir = os.path.join(backend_dir, "templates")  
templates = Jinja2Templates(directory=templates_dir)

class DomainRequest(BaseModel):
    domain: str
    description: str

@router.get("/api/logs/{log_id}")
def get_log_detail(log_id: int, db: Session = Depends(get_db)):
    log = db.query(ScanLog).filter(ScanLog.id == log_id).first()
    if not log or not log.full_result: raise HTTPException(status_code=404, detail="상세 기록 정보가 없습니다.")
    return JSONResponse(content=json.loads(log.full_result))

@router.delete("/api/cache")
async def clear_cache(db: Session = Depends(get_db)):
    try:
        keys = await redis_client.keys("phishguard:cache:*")
        deleted_cache = len(keys) if keys else 0
        if keys: await redis_client.delete(*keys)
        deleted_scans = db.query(ScanLog).delete()
        deleted_reports = db.query(ReportLog).delete()
        db.commit()
        return {"status": "success", "msg": f"캐시 {deleted_cache}건, 분석 로그 {deleted_scans}건, 신고 로그 {deleted_reports}건이 모두 초기화되었습니다."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ... (화이트/블랙리스트 API는 기존과 동일) ...
@router.get("/api/whitelist")
async def get_whitelist(db: Session = Depends(get_db)):
    items = db.query(Whitelist).order_by(Whitelist.id.desc()).all()
    return [{"domain": item.domain, "description": getattr(item, 'description', '설명 없음')} for item in items]

@router.post("/api/whitelist")
async def add_whitelist(req: DomainRequest, db: Session = Depends(get_db)):
    domain_clean = req.domain.lower().replace("https://", "").replace("http://", "").replace("www.", "")
    if db.query(Whitelist).filter(Whitelist.domain == domain_clean).first():
        raise HTTPException(status_code=400, detail="이미 존재하는 도메인입니다.")
    try:
        db.add(Whitelist(domain=domain_clean))
        db.commit()
        await redis_client.sadd("phishguard:whitelist", domain_clean)
        return {"status": "success", "msg": f"{domain_clean} 추가 완료"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/whitelist/{domain}")
async def delete_whitelist(domain: str, db: Session = Depends(get_db)):
    item = db.query(Whitelist).filter(Whitelist.domain == domain).first()
    if item:
        db.delete(item)
        db.commit()
        await redis_client.srem("phishguard:whitelist", domain)
    return {"status": "success"}

@router.post("/api/blacklist")
async def add_blacklist(req: Request, db: Session = Depends(get_db)):
    body = await req.json()
    domain = body.get("domain", "").lower().replace("https://", "").replace("http://", "").replace("www.", "")
    if not domain: raise HTTPException(status_code=400, detail="도메인이 비어있습니다.")
    if db.query(Blacklist).filter(Blacklist.domain == domain).first(): return {"status": "success", "msg": "이미 등록된 도메인"}
    db.add(Blacklist(domain=domain))
    db.commit()
    await redis_client.sadd("phishguard:blacklist", domain)
    return {"status": "success"}

@router.delete("/api/blacklist/{domain}")
async def delete_blacklist(domain: str, db: Session = Depends(get_db)):
    item = db.query(Blacklist).filter(Blacklist.domain == domain).first()
    if item:
        db.delete(item)
        db.commit()
        await redis_client.srem("phishguard:blacklist", domain)
    return {"status": "success"}

# 4. 통합 대시보드 웹 뷰 (핵심 수정!)
@router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard(db: Session = Depends(get_db)):
    scans = db.query(ScanLog).order_by(ScanLog.created_at.desc()).limit(20).all()
    reports = db.query(ReportLog).order_by(ReportLog.report_count.desc()).limit(20).all()
    whites = db.query(Whitelist).order_by(Whitelist.created_at.desc()).all()
    blacks = db.query(Blacklist).order_by(Blacklist.created_at.desc()).all()

    # 🚀 [수정] JSON에서 라벨을 직접 추출하여 동적으로 뱃지 생성
    scan_rows = ""
    for s in scans:
        try:
            data = json.loads(s.full_result) if s.full_result else {}
            label = data.get("label", "Phishing" if s.is_suspicious else "Safe")
        except:
            label = "Phishing" if s.is_suspicious else "Safe"
        
        # 라벨별 한글명 및 색상 매핑
        mapping = {
            "Safe": ("정상", "badge-Safe"), "Phishing": ("위험", "badge-danger"),
            "Impersonation": ("기관 사칭", "badge-Impersonation"), "Financial": ("금융 사기", "badge-Financial"),
            "Malware": ("악성코드", "badge-Malware"), "Gambling": ("불법 도박", "badge-Gambling"),
            "Adult": ("유해 콘텐츠", "badge-Adult"), "Unknown": ("판단 보류", "badge-Unknown")
        }
        text, css = mapping.get(label, ("위험", "badge-danger"))
        
        scan_rows += (
            f"<tr class='clickable-row' onclick='openLogModal({s.id})'>"
            f"<td>{s.id}</td>"
            f"<td><div class='url-text' title='{s.url}'>{s.url}</div></td>"
            f"<td><strong>{s.risk_score}점</strong></td>"
            f"<td><span class='badge {css}'>{text}</span></td>"
            f"</tr>"
        )

    # ... (나머지 코드 생략, 대시보드 HTML 출력 부분은 아래와 같습니다) ...
    report_rows = "".join(f"<tr><td><div class='url-text'>{r.url}</div></td><td>{r.reason or '사유 없음'}</td><td><strong style='color:#d63031;'>{r.report_count}회</strong></td></tr>" for r in reports)
    white_rows = "".join(f"<tr><td style='width:350px;'>{w.domain}</td><td><button class='btn-del' onclick=\"deleteItem('whitelist', '{w.domain}')\">제거</button></td></tr>" for w in whites)
    black_rows = "".join(f"<tr><td style='width:350px;'>{b.domain}</td><td><button class='btn-del' onclick=\"deleteItem('blacklist', '{b.domain}')\">차단 해제</button></td></tr>" for b in blacks)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>실시간 모니터링 센터</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f1f2f6; margin: 0; padding: 25px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .header h1 {{ color: #2c3e50; font-size: 32px; margin: 0; }}
            .header p {{ color: #7f8c8d; font-size: 16px; margin-top: 10px; }}
            .dashboard-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(600px, 1fr)); gap: 25px; max-width: 1500px; margin: 0 auto; }}
            .card {{ background: white; border-radius: 12px; padding: 22px; box-shadow: 0 8px 16px rgba(0,0,0,0.04); }}
            h3 {{ margin-top: 0; padding-bottom: 12px; border-bottom: 2px solid #f1f2f6; color: #2c3e50; display: flex; justify-content: space-between; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #f1f2f6; font-size: 14px; }}
            th {{ background-color: #f8f9fa; color: #7f8c8d; font-weight: 600; font-size: 12px; }}
            .clickable-row {{ cursor: pointer; }}
            .clickable-row:hover {{ background-color: #edf2f7; }}
            .btn-del {{ background: #ff7675; color: white; border: none; padding: 5px 9px; border-radius: 4px; cursor: pointer; }}
            .btn-add {{ background: #0984e3; color: white; border: none; padding: 7px 14px; border-radius: 4px; cursor: pointer; }}
            input {{ padding: 6px; border: 1px solid #ccc; border-radius: 4px; width: 60%; }}
            .url-text {{ max-width: 250px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #0984e3; }}
            .empty-msg {{ text-align: center; color: #b2bec3; font-style: italic; padding: 20px; }}
            .modal {{ display: none; position: fixed; z-index: 100; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); overflow-y: auto; }}
            .modal-content {{ background: white; margin: 5% auto; padding: 25px; border-radius: 12px; width: 50%; min-width: 500px; box-shadow: 0 12px 24px rgba(0,0,0,0.2); }}
            .close {{ float: right; font-size: 28px; font-weight: bold; cursor: pointer; }}
            
            /* 🚀 세분화된 뱃지 스타일 */
            .badge {{ padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; display: inline-block; }}
            .badge-Safe {{ background-color: #e6ffed; color: #2ea043; border: 1px solid #2ea043; }}
            .badge-danger {{ background-color: #ffebe9; color: #cb2431; border: 1px solid #cb2431; }}
            .badge-Impersonation {{ background-color: #fff5eb; color: #e36209; border: 1px solid #e36209; }}
            .badge-Financial {{ background-color: #fffdef; color: #b08800; border: 1px solid #b08800; }}
            .badge-Malware {{ background-color: #ffebe9; color: #cb2431; border: 1px solid #cb2431; }}
            .badge-Gambling {{ background-color: #f6f0eb; color: #8b4513; border: 1px solid #8b4513; }}
            .badge-Adult {{ background-color: #f4ecff; color: #8a2be2; border: 1px solid #8a2be2; }}
            .badge-Unknown {{ background-color: #f6f8fa; color: #6a737d; border: 1px solid #6a737d; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🛡️ 실시간 모니터링 센터</h1>
            <p>실시간 URL 분석 현황 및 위협 요소를 모니터링합니다.</p>
            <button onclick="clearCache()" style="background-color:#e67e22; color:white; border:none; padding:8px 16px; border-radius:6px; cursor:pointer; font-weight:bold; margin-top:10px;">
                ⚡️ 분석 캐시 및 로그 초기화
            </button>
        </div>
        
        <div class="dashboard-grid">
            <div class="card">
                <h3><span>🔍 AI 분석 로그 </span> <span class="badge badge-Unknown">최근 {len(scans)}건</span></h3>
                {"<div class='empty-msg'>분석된 기록이 없습니다.</div>" if not scans else ""}
                <table style="{'display:none' if not scans else ''}">
                    <tr><th>ID</th><th>요청 URL</th><th>AI 위험도</th><th>상태</th></tr>
                    {scan_rows}
                </table>
            </div>
            
            <div class="card">
                <h3><span>🚨 사용자 신고 접수 현황</span> <span class="badge badge-Unknown">총 {len(reports)}건</span></h3>
                {"<div class='empty-msg'>접수된 신고가 없습니다.</div>" if not reports else ""}
                <table style="{'display:none' if not reports else ''}">
                    <tr><th>신고 URL</th><th>사유</th><th>누적 횟수</th></tr>
                    {report_rows}
                </table>
            </div>

            <div class="card">
                <h3><span>✅ 화이트리스트 관리</span> <span class="badge badge-Safe">보안 패스</span></h3>
                <div style="margin-bottom: 15px;">
                    <input type="text" id="whiteInput" placeholder="예: google.com">
                    <button class="btn-add" onclick="addItem('whitelist')">즉시 등록</button>
                </div>
                <table style="display:block; max-height:250px; overflow-y:auto;">
                    {white_rows}
                </table>
            </div>

            <div class="card">
                <h3><span>☠️ 블랙리스트 관리</span> <span class="badge badge-danger">강제 차단</span></h3>
                <div style="margin-bottom: 15px;">
                    <input type="text" id="blackInput" placeholder="예: bad-phishing.net">
                    <button class="btn-add" onclick="addItem('blacklist')">차단 등록</button>
                </div>
                <table style="display:block; max-height:250px; overflow-y:auto;">
                    {black_rows}
                </table>
            </div>
        </div>

        <div id="logModal" class="modal">
            <div class="modal-content">
                <span class="close" onclick="closeModal()">&times;</span>
                <h2 id="modalUrl" style="color:#2c3e50; margin-top:0;">URL 상세 정보</h2>
                <p>📊 <b>위험도 결과 점수:</b> <span id="modalScore" style="font-size:20px; font-weight:bold; color:red;">-</span> 점</p>
                <p>💡 <b>한줄 진단 평:</b> <span id="modalOneLine">-</span></p>
                <hr>
                <h4>🤖 제미나이 보안 분석 보고서</h4>
                <div id="modalReport" style="background:#f8f9fa; padding:15px; border-radius:6px; white-space:pre-wrap; font-size:13px; max-height:200px; overflow-y:auto;">-</div>
                <h4>📸 스냅샷 스크린샷 화면</h4>
                <img id="modalScreenshot" src="" alt="화면 이미지 없음" style="max-width: 100%; border: 1px solid #ddd; border-radius: 6px; margin-top: 10px;" />
            </div>
        </div>

        <script>
            async function openLogModal(logId) {{
                try {{
                    const res = await fetch(`/admin/api/logs/${{logId}}`);
                    if(!res.ok) return;
                    const data = await res.json();
                    
                    document.getElementById("modalScore").innerText = data.risk_score;
                    document.getElementById("modalOneLine").innerText = data.one_line;
                    document.getElementById("modalReport").innerText = data.gemini_report || "작성된 AI 리포트가 없습니다.";
                    
                    const img = document.getElementById("modalScreenshot");
                    if(data.screenshot && data.screenshot.value) {{
                        img.src = "data:image/png;base64," + data.screenshot.value;
                        img.style.display = "block";
                    }} else {{
                        img.style.display = "none";
                    }}
                    document.getElementById("logModal").style.display = "block";
                }} catch(e) {{ console.error(e); }}
            }}
            
            function closeModal() {{ document.getElementById("logModal").style.display = "none"; }}

            async function addItem(type) {{
                const input = document.getElementById(type === 'whitelist' ? 'whiteInput' : 'blackInput');
                const val = input.value.trim();
                if(!val) return;
                
                const url = type === 'whitelist' ? '/admin/api/whitelist' : '/admin/api/blacklist';
                const res = await fetch(url, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ domain: val, description: "수동 등록" }})
                }});
                if(res.ok) location.reload();
                else alert("등록에 실패했습니다.");
            }}

            async function deleteItem(type, domain) {{
                const url = type === 'whitelist' ? `/admin/api/whitelist/${{domain}}` : `/admin/api/blacklist/${{domain}}`;
                const res = await fetch(url, {{ method: 'DELETE' }});
                if(res.ok) location.reload();
            }}

            async function clearCache() {{
                if(confirm("모든 분석 캐시와 관제 사이트의 로그 기록(분석/신고)을 완전히 초기화하시겠습니까?\\n(화이트리스트와 블랙리스트는 안전하게 유지됩니다)")) {{
                    try {{
                        const res = await fetch('/admin/api/cache', {{ method: 'DELETE' }});
                        const data = await res.json();
                        if(res.ok) {{
                            alert("🧹 " + data.msg);
                            location.reload(); 
                        }} else {{
                            alert("초기화 실패!");
                        }}
                    }} catch(e) {{ console.error(e); }}
                }}
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)