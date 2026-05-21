import os
import json  # 🚀 json 임포트 추가!
import torch
from fastapi import WebSocket
from typing import List  # 🚀 위로 끌어올림!

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
except ImportError:
    print("⚠️ AI 라이브러리를 못 찾았습니다. 가상환경 세팅을 확인해주세요.")

class PhishGuardAnalyzer:
    def __init__(self):
        # 1. 디바이스 설정 (Mac MPS, Linux Cuda/CPU 모두 대응)
        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")
        else:
            self.device = torch.device("cpu")
        
        print(f"🚀 PhishGuard AI 로드 준비 (사용 장치: {self.device})")

        # 2. 🟢 모델 파일 위치 동적 추적
        current_dir = os.path.dirname(os.path.abspath(__file__))  # backend/services
        backend_dir = os.path.dirname(current_dir)                # backend
        self.model_path = os.path.join(backend_dir, "weights", "phishguard_global_patched_model")

        # 3. 모델 로드 검증
        if os.path.exists(self.model_path):
            print(f"🟢 [성공] 진짜 파인튜닝된 모델을 찾았습니다! 경로: {self.model_path}")
            print("🧠 PhishGuard URL 모델 가중치를 뇌에 불러옵니다...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_path, 
                num_labels=4,
                ignore_mismatched_sizes=True
            ).to(self.device)
            self.model.eval() # 추론 모드로 전환
            self.is_ai_ready = True
        else:
            print(f"❌ [경로 오류] 모델 가중치를 찾지 못했습니다.")
            print(f"   - 시도한 경로: {self.model_path}")
            print("⚠️ 가중치가 없어 임시 더미(Dummy) 로직으로 우회 동작합니다.")
            self.is_ai_ready = False

    def predict(self, url: str) -> dict:
        if not url:
            return {"status": "error", "is_suspicious": False, "risk_score": 0, "msg": "URL이 없습니다."}

        # --- [A] 진짜 AI 추론 로직 ---
        if self.is_ai_ready:
            inputs = self.tokenizer(url, return_tensors="pt", truncation=True, max_length=64).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            probs = torch.softmax(outputs.logits, dim=1)[0]
            
            safe_prob = probs[0].item()
            danger_prob = 1.0 - safe_prob # 전체(1.0)에서 정상 확률을 뺀 나머지
            
            print(f"\n🔮 [AI 모델의 진짜 속마음] 정상 확률: {safe_prob:.4f} / 통합 위험 확률: {danger_prob:.4f}")
            print(f"   [상세 클래스별 확률] {probs.tolist()}") # 디버깅용 전체 확률 출력
            
            risk_score = float(danger_prob * 100)
            is_suspicious = True if risk_score >= 50 else False
            
            return {
                "status": "success",
                "is_suspicious": is_suspicious,
                "risk_score": risk_score
            }

        # --- [B] 더미 로직 ---
        url_lower = url.lower()
        if url_lower in ["naver.com", "www.naver.com"]:
            return {"status": "success", "is_suspicious": False, "risk_score": 5}
        else:
            return {"status": "success", "is_suspicious": True, "risk_score": 90}
            

class DashboardWebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_status(self, step: str, msg: str, status: str = "active", active_nodes: list = None, done_nodes: list = None):
        """연결된 모든 대시보드 화면에 현재 서버 상태를 실시간 전송합니다."""
        print(f"📡 [방송국] 대시보드 {len(self.active_connections)}개에 송출 중... 단계: {step}")
        payload = {
            "step": step,
            "msg": msg,
            "status": status,
            "active_nodes": active_nodes or [],
            "done_nodes": done_nodes or []
        }
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(payload))
            except Exception:
                pass

analyzer = PhishGuardAnalyzer()
dashboard_manager = DashboardWebSocketManager()

def analyze_url_with_ai(url: str) -> dict:
    return analyzer.predict(url)