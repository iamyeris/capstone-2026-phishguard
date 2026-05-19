from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from services.interface import dashboard_manager

router = APIRouter()

# 🖥️ 1. 실시간 중계용 고품격 아키텍처 대시보드 UI
@router.get("/")
async def get_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PhishGuard | Live Pipeline Monitoring</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Fira+Code:wght@400&display=swap');

            :root {
                --bg-color: #0f172a;
                --card-bg: #1e293b;
                --node-idle: #334155;
                --node-active: #3b82f6;
                --node-done: #10b981;
                --accent-blue: #4285F4;
                --text-main: #f8fafc;
                --text-dim: #94a3b8;
            }

            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { 
                background-color: var(--bg-color); 
                color: var(--text-main); 
                font-family: 'Inter', sans-serif; 
                height: 100vh; 
                display: flex; 
                flex-direction: column; 
                padding: 40px; 
                overflow: hidden;
            }

            /* --- Header --- */
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }
            .header h2 { font-weight: 600; letter-spacing: -0.5px; font-size: 24px; display: flex; align-items: center; gap: 12px; }
            .header h2 i { color: var(--accent-blue); }
            .status-badge { 
                background: rgba(15, 23, 42, 0.6); 
                padding: 8px 18px; 
                border-radius: 30px; 
                font-size: 13px; 
                border: 1px solid #334155; 
                backdrop-filter: blur(10px);
                display: flex; align-items: center; gap: 8px;
            }
            .dot { width: 8px; height: 8px; border-radius: 50%; background: #94a3b8; }
            .dot.online { background: #10b981; box-shadow: 0 0 10px #10b981; animation: pulse 2s infinite; }

            /* --- Pipeline Visualizer --- */
            .pipeline-container {
                background: var(--card-bg);
                padding: 60px 40px;
                border-radius: 24px;
                border: 1px solid rgba(255,255,255,0.05);
                display: flex;
                justify-content: space-between;
                align-items: center;
                position: relative;
                margin-bottom: 40px;
                box-shadow: 0 20px 50px rgba(0,0,0,0.3);
            }

            /* 하단 라벨 (Read, Process, Activate) */
            .stage-label-container {
                position: absolute; bottom: 15px; left: 0; width: 100%;
                display: flex; justify-content: space-around;
                pointer-events: none;
            }
            .stage-label {
                font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 2px;
                padding: 4px 12px; border-radius: 4px; color: var(--text-dim); background: rgba(0,0,0,0.2);
            }

            .node-group { display: flex; flex-direction: column; gap: 20px; align-items: center; z-index: 2; }
            
            .node {
                background: var(--node-idle);
                min-width: 160px; padding: 20px; border-radius: 16px;
                border: 1px solid rgba(255,255,255,0.1);
                text-align: center; font-weight: 600; font-size: 14px;
                transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
                color: var(--text-dim);
                display: flex; flex-direction: column; gap: 8px;
            }
            .node i { font-size: 20px; margin-bottom: 4px; }

            /* 상태별 스타일 */
            .node.active { 
                background: var(--node-active); 
                color: white; 
                transform: translateY(-5px) scale(1.05);
                box-shadow: 0 0 30px rgba(59, 130, 246, 0.5);
                border-color: #60a5fa;
            }
            .node.done { 
                background: var(--node-done); 
                color: white; 
                transform: scale(1);
                box-shadow: 0 0 20px rgba(16, 185, 129, 0.2);
                border-color: #34d399;
            }

            /* 커넥터 화살표 */
            .connector { color: #334155; font-size: 20px; transition: color 0.5s; }
            .connector.highlight { color: var(--accent-blue); }

            /* --- Terminal Log --- */
            .terminal {
                flex-grow: 1;
                background: #000000;
                border-radius: 16px;
                border: 1px solid #334155;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            }
            .terminal-header {
                background: #1e293b; padding: 10px 20px;
                display: flex; align-items: center; gap: 8px;
                border-bottom: 1px solid #334155;
            }
            .term-dot { width: 12px; height: 12px; border-radius: 50%; }
            .term-box { flex-grow: 1; padding: 20px; overflow-y: auto; font-family: 'Fira Code', monospace; }
            
            .log-entry { margin-bottom: 8px; display: flex; gap: 15px; animation: slideIn 0.3s ease-out; }
            .log-ts { color: #64748b; min-width: 90px; }
            .log-msg { color: #e2e8f0; }
            .log-msg.step { color: var(--accent-blue); font-weight: 600; }
            .log-divider { height: 1px; background: #334155; margin: 15px 0; }

            @keyframes pulse {
                0% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.5); opacity: 0.4; }
                100% { transform: scale(1); opacity: 1; }
            }

            @keyframes slideIn {
                from { opacity: 0; transform: translateX(-10px); }
                to { opacity: 1; transform: translateX(0); }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h2><i class="fa-solid fa-shield-halved"></i> PhishGuard Live Infrastructure</h2>
            <div class="status-badge">
                <div class="dot online" id="dot-status"></div>
                <span id="conn-status">📡 관제 시스템 연결 대기 중...</span>
            </div>
        </div>

        <div class="pipeline-container">
            <div class="stage-label-container">
                <div class="stage-label">Read / Input</div>
                <div class="stage-label" style="margin-left: 50px;">Transform / Process</div>
                <div class="stage-label">Sink / Activate</div>
            </div>

            <div class="node-group">
                <div class="node" id="node-req"><i class="fa-solid fa-cloud-arrow-down"></i>요청 접수</div>
            </div>
            
            <i class="fa-solid fa-chevron-right connector" id="arr-1"></i>

            <div class="node-group">
                <div class="node" id="node-cache"><i class="fa-solid fa-bolt-lightning"></i>캐시 검증</div>
            </div>

            <i class="fa-solid fa-chevron-right connector" id="arr-2"></i>

            <div class="node-group">
                <div class="node" id="node-bert"><i class="fa-solid fa-brain"></i>BERT AI 추론</div>
                <div class="node" id="node-crawl"><i class="fa-solid fa-spider"></i>격리 브라우저 캡처</div>
            </div>

            <i class="fa-solid fa-chevron-right connector" id="arr-3"></i>

            <div class="node-group">
                <div class="node" id="node-db"><i class="fa-solid fa-database"></i>병합 및 영구 저장</div>
            </div>

            <i class="fa-solid fa-chevron-right connector" id="arr-4"></i>

            <div class="node-group">
                <div class="node" id="node-gemini"><i class="fa-solid fa-robot"></i>Gemini 리포트</div>
            </div>
        </div>

        <div class="terminal">
            <div class="terminal-header">
                <div class="term-dot" style="background: #ff5f56;"></div>
                <div class="term-dot" style="background: #ffbd2e;"></div>
                <div class="term-dot" style="background: #27c93f;"></div>
                <span style="margin-left: 10px; font-size: 13px; color: #94a3b8;">phishguard-pipeline-monitor — bash</span>
            </div>
            <div class="term-box" id="log-box">
                <div class="log-entry"><span class="log-ts">SYSTEM</span> <span class="log-msg">준비 완료. API 요청 수신 대기 중...</span></div>
            </div>
        </div>

        <script>
            const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
            const socket = new WebSocket(wsProtocol + window.location.host + "/dashboard/ws");

            socket.onopen = () => {
                document.getElementById('conn-status').innerText = "LIVE STREAMING ACTIVE";
                document.getElementById('dot-status').className = "dot online";
            };

            socket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                const logBox = document.getElementById('log-box');
                const now = new Date().toLocaleTimeString('en-GB', { hour12: false });
                
                // 새로운 트랜잭션 수신 시 UI 초기화
                if (data.step === "1단계") {
                    document.querySelectorAll('.node').forEach(el => el.className = 'node');
                    document.querySelectorAll('.connector').forEach(el => el.className = 'fa-solid fa-chevron-right connector');
                    logBox.innerHTML += `<div class="log-divider"></div>`;
                }

                // 로그 출력
                logBox.innerHTML += `
                    <div class="log-entry">
                        <span class="log-ts">${now}</span>
                        <span class="log-msg ${data.step ? 'step' : ''}">[${data.step || 'INFO'}] ${data.msg}</span>
                    </div>`;
                logBox.scrollTop = logBox.scrollHeight;

                // 노드 조명 및 화살표 하이라이트 제어
                if (data.active_nodes) {
                    data.active_nodes.forEach(id => {
                        const node = document.getElementById(id);
                        if(node) node.className = 'node active';
                    });
                }
                
                if (data.done_nodes) {
                    data.done_nodes.forEach(id => {
                        const node = document.getElementById(id);
                        if(node) node.className = 'node done';
                        
                        // 화살표 하이라이트 로직 (단순 구현)
                        if(id === 'node-req') document.getElementById('arr-1').classList.add('highlight');
                        if(id === 'node-cache') document.getElementById('arr-2').classList.add('highlight');
                        if(id === 'node-bert' || id === 'node-crawl') document.getElementById('arr-3').classList.add('highlight');
                        if(id === 'node-db') document.getElementById('arr-4').classList.add('highlight');
                    });
                }
            };

            socket.onclose = () => {
                document.getElementById('conn-status').innerText = "CONNECTION LOST";
                document.getElementById('dot-status').className = "dot";
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# 📡 2. 대시보드 화면용 웹소켓 수신 전용 터널 엔드포인트
@router.websocket("/ws")
async def dashboard_websocket_endpoint(websocket: WebSocket):
    await dashboard_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        dashboard_manager.disconnect(websocket)