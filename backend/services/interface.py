import torch
# 나중에 친구가 모델 주면 아래 transformers 주석을 해제할 거야!
# from transformers import AutoTokenizer, AutoModelForSequenceClassification

class PhishGuardAnalyzer:
    def __init__(self):
        # 1. 디바이스 설정 (GPU가 있으면 쓰고, 없으면 CPU)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"🧠 PyTorch 모델 로드 준비 완료 (Device: {self.device})")
        
        # =================================================================
        # ⭐️ [나중에 활성화할 구역] 친구가 파인튜닝한 모델을 주면 여기를 깨워!
        # =================================================================
        # self.tokenizer = AutoTokenizer.from_pretrained("klue/bert-base") 
        # self.model = AutoModelForSequenceClassification.from_pretrained("klue/bert-base", num_labels=2)
        # self.model.load_state_dict(torch.load("weights/phishguard_v1.pth", map_location=self.device))
        # self.model.to(self.device)
        # self.model.eval()

    def predict(self, text: str) -> dict:
        """
        수집된 웹사이트 텍스트를 분석하여 위험도 점수와 라벨을 반환합니다.
        """
        # =================================================================
        # ⭐️ [나중에 활성화할 구역] 진짜 딥러닝 추론 로직
        # =================================================================
        # if not text: return {"risk_score": 0, "label": "NORMAL"}
        # inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to(self.device)
        # with torch.no_grad():
        #     outputs = self.model(**inputs)
        # probabilities = torch.softmax(outputs.logits, dim=1)[0]
        # risk_score = int(probabilities[1].item() * 100) # 피싱일 확률을 점수로!
        # label = "PHISHING" if risk_score >= 50 else "NORMAL"
        # return {"risk_score": risk_score, "label": label}
        
        # =================================================================
        # 🚧 [현재 상태] 프론트엔드 연동 및 뼈대 테스트용 더미 로직
        # =================================================================
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in ["login", "password", "인증", "비밀번호"]):
            return {"risk_score": 85, "label": "PHISHING"}
        elif any(keyword in text_lower for keyword in ["bet", "casino", "도박", "토토"]):
            return {"risk_score": 75, "label": "GAMBLING"}
        elif any(keyword in text_lower for keyword in ["download", "apk", "다운로드"]):
            return {"risk_score": 90, "label": "MALWARE"}
        
        return {"risk_score": 15, "label": "NORMAL"}

# 서버가 켜질 때 모델이 메모리에 딱 한 번만 올라가도록 싱글톤(Singleton) 생성
analyzer = PhishGuardAnalyzer()

def analyze_text_with_ai(text: str) -> dict:
    return analyzer.predict(text)