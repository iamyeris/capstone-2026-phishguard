import os
import torch
import pandas as pd
from torch.utils.data import Dataset
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    TrainingArguments, 
    Trainer, 
    TrainerCallback,
    EarlyStoppingCallback # 🚀 과적합 방지용 브레이크
)

# 1. 커스텀 데이터셋 클래스
class PhishGuardDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=64):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = int(self.labels[idx])
        
        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

# 2. 📊 매 에포크 로그 수집 전용 콜백 (저장 방해 로직 제거)
class PresentationLogCallback(TrainerCallback):
    def __init__(self, output_path="./data/presentation_logs.csv"):
        self.output_path = output_path
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

    def on_epoch_end(self, args, state, control, **kwargs):
        """1 에포크가 끝날 때마다 작동하여 로그를 병합합니다."""
        raw_logs = state.log_history
        if not raw_logs: return

        epoch_metrics = {}
        for log in raw_logs:
            if "epoch" not in log: continue
            epoch = round(log["epoch"], 2)
            if epoch not in epoch_metrics:
                epoch_metrics[epoch] = {"epoch": epoch, "learning_rate": None, "train_loss": None, "grad_norm": None, "eval_loss": None}
            
            if "loss" in log: epoch_metrics[epoch]["train_loss"] = log["loss"]
            if "grad_norm" in log: epoch_metrics[epoch]["grad_norm"] = log["grad_norm"]
            if "learning_rate" in log: epoch_metrics[epoch]["learning_rate"] = log["learning_rate"]
            if "eval_loss" in log: epoch_metrics[epoch]["eval_loss"] = log["eval_loss"]

        cleaned_logs = sorted(epoch_metrics.values(), key=lambda x: x["epoch"])
        log_df = pd.DataFrame(cleaned_logs)

        if not log_df.empty:
            log_df.to_csv(self.output_path, index=False)
            print(f"📊 통합 로그 업데이트 완료 -> {self.output_path}")

def main():
    # 3. 디바이스 설정 (M4)
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    print(f"🚀 사용할 디바이스: {device}")

    # 4. 전체 데이터 로드 및 분할
    data_path = "./data/train_data.csv"
    print(f"[{data_path}] 데이터를 불러옵니다...")
    if not os.path.exists(data_path):
        print(f"❌ 에러: {data_path} 파일이 없습니다. prepare_data.py를 먼저 실행해 주세요.")
        return
        
    df = pd.read_csv(data_path)
    
    # 데이터 분할 (80% 학습, 20% 검증)
    train_df = df.sample(frac=0.8, random_state=42)
    val_df = df.drop(train_df.index)
    
    train_texts = train_df['url'].tolist()
    train_labels = train_df['label'].tolist()
    val_texts = val_df['url'].tolist()
    val_labels = val_df['label'].tolist()

    print(f"📊 학습 데이터 수: {len(train_texts)}개 / 검증 데이터 수: {len(val_texts)}개")

    # 5. 모델 및 토크나이저 로드
    model_name = "CrabInHoney/urlbert-tiny-v4-phishing-classifier"
    print(f"[{model_name}] 모델과 토크나이저를 로드합니다...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # 🚀 [핵심 변경] num_labels를 4로 변경! (다중 분류 선언)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, 
        num_labels=4, 
        ignore_mismatched_sizes=True 
    ).to(device)

    train_dataset = PhishGuardDataset(train_texts, train_labels, tokenizer)
    val_dataset = PhishGuardDataset(val_texts, val_labels, tokenizer)

    # 6. 🛡️ 과적합 방지가 적용된 학습 인자 설정
    output_dir = "../weights/phishguard_final_model"
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=5,                    # 🚀 65만 개는 5에포크면 충분!
        per_device_train_batch_size=32,        # 🚀 M4 가속 활용 배치 사이즈 업그레이드
        per_device_eval_batch_size=32,
        warmup_steps=1000,
        weight_decay=0.01,
        
        # 🛡️ 99점 확신병 치료제
        label_smoothing_factor=0.1,            # 1. 과도한 확신 방지
        max_grad_norm=1.0,                     # 2. 학습 지진(폭발) 방지
        
        logging_steps=100,
        eval_strategy="epoch",             
        save_strategy="epoch",                 # Early Stopping을 위해 필수
        load_best_model_at_end=True,           # 3. 최적기(eval_loss 최저점) 가중치로 자동 복원
        metric_for_best_model="eval_loss",
        greater_is_better=False
    )

    # 7. 트레이너 초기화
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        callbacks=[
            PresentationLogCallback(), 
            EarlyStoppingCallback(early_stopping_patience=1) # 🚀 eval_loss 1번 튀면 바로 종료!
        ] 
    )

    print("🚀 65만 개 4-Class 대용량 파인튜닝 학습을 시작합니다!")
    trainer.train()

    # 8. 최종 결과물 강제 저장 (가장 똑똑한 순간의 뇌가 저장됨)
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"✅ 학습 완료! 4-Class 최적화 최종 가중치 모델을 [{output_dir}] 에 성공적으로 저장했습니다.")

if __name__ == "__main__":
    main()