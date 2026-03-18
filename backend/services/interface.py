import torch
import os
# 에러 나는 줄을 try-except로 감싸서 에러가 나도 무시하게 만듭니다.
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
except ImportError:
    print("⚠️ AI 라이브러리를 못 찾았지만, 발표를 위해 서버를 강제로 실행합니다!")
    # 아래에 더미 클래스를 아주 간단하게 만들어버립니다.
    class AutoTokenizer:
        @classmethod
        def from_pretrained(cls, *args, **kwargs): return cls()
    class AutoModelForSequenceClassification:
        @classmethod
        def from_pretrained(cls, *args, **kwargs): return cls()
class PhishGuardAnalyzer:
    def __init__(self):
        # 1. M4 맥북 전용 디바이스 설정 (MPS 가속)
        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")
        else:
            self.device = torch.device("cpu")
        
        print(f"🚀 PhishGuard AI 로드 완료 (사용 장치: {self.device})")

        # 2. 결과 맵핑 사전 (팀장님이 정하신 8단계 규칙!)
        self.RESULT_MAP = {
            0: {"label": "정상", "color": "#4CAF50", "desc": "안심 이용"},
            1: {"label": "일반 피싱", "color": "#F44336", "desc": "계정 유출 주의"},
            2: {"label": "기관 사칭", "color": "#FF9800", "desc": "법적 피해 경고"},
            3: {"label": "금융 사기", "color": "#FFEB3B", "desc": "금전 갈취 위험"},
            4: {"label": "악성코드", "color": "#D32F2F", "desc": "기기 해킹 위험"},
            5: {"label": "불법 도박", "color": "#795548", "desc": "불법 경로 차단"},
            6: {"label": "유해 콘텐츠", "color": "#9C27B0", "desc": "유해 환경 주의"},
            7: {"label": "판단 보류", "color": "#9E9E9E", "desc": "데이터 부족/분석 불가"}
        }

        # 3. 모델 로드 (학습 완료 후 weights 폴더에 모델이 있을 때 활성화)
        self.model_path = "../weights/phishguard_final_model"
        
        if os.path.exists(self.model_path):
            print("🧠 파인튜닝된 모델을 불러옵니다...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_path, 
                num_labels=8  # ⭐️ 8개 카테고리 설정!
            ).to(self.device)
            self.model.eval()
            self.is_ai_ready = True
        else:
            print("⚠️ 모델 파일이 없어 더미(Dummy) 로직으로 동작합니다.")
            self.is_ai_ready = False

    def predict(self, text: str) -> dict:
        if not text:
            return self.RESULT_MAP[7] # 텍스트 없으면 '판단 보류'

        # --- [A] 진짜 AI 추론 로직 (모델이 있을 때만 작동) ---
        if self.is_ai_ready:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=128).to(self.device)
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # 확률이 가장 높은 번호(0~7) 뽑기
            prediction = torch.argmax(outputs.logits, dim=1).item()
            
            # 확률값(0~1)을 위험 점수(0~100)로 변환 (예시로 단순 계산)
            probs = torch.softmax(outputs.logits, dim=1)[0]
            risk_score = int(torch.max(probs).item() * 100) if prediction != 0 else 10
            
            result = self.RESULT_MAP[prediction].copy()
            result["risk_score"] = risk_score
            return result

        # --- [B] 더미 로직 (모델 학습 전 테스트용) ---
        text_lower = text.lower()

        # 진짜 네이버 주소인 경우는 정상으로 처리
        if text_lower in ["naver.com", "www.naver.com"]:
            res = self.RESULT_MAP[0].copy() # 정상
            res["risk_score"] = 5
        elif any(kw in text_lower for kw in ["login-naver", "naver-secure", "verify"]):
            # 네이버를 사칭하는 듯한 수상한 조합만 피싱으로!
            res = self.RESULT_MAP[1].copy() # 일반 피싱
            res["risk_score"] = 95
        else:
            res = self.RESULT_MAP[0].copy() # 기본은 정상
            res["risk_score"] = 10
                    
        return res

# 싱글톤 인스턴스 생성
analyzer = PhishGuardAnalyzer()

def analyze_text_with_ai(text: str) -> dict:
    return analyzer.predict(text)