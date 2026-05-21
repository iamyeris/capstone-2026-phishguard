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
    EarlyStoppingCallback
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

# 2. 📊 매 에포크 로그 수집 전용 콜백
class PresentationLogCallback(TrainerCallback):
    def __init__(self, output_path="./data/presentation_logs.csv"):
        self.output_path = output_path
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

    def on_epoch_end(self, args, state, control, **kwargs):
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

    # =====================================================================
    # 🚨 [수정 포인트 1] 4-Class 1:1:1:1 황금 밸런스 데이터 로드
    # =====================================================================
    data_path = "./data/balanced_4class_train.csv" 
    print(f"[{data_path}] 데이터를 불러옵니다...")
    if not os.path.exists(data_path):
        print(f"❌ 에러: {data_path} 파일이 없습니다. 먼저 밸런싱 스크립트를 실행해 주세요.")
        return
        
    df = pd.read_csv(data_path)
    
    # 데이터가 진짜 1:1:1:1인지 눈으로 확인하는 안심 코드
    print("\n[현재 학습 데이터 라벨 분포 (1:1:1:1 확인)]")
    print(df['label'].value_counts())
    print("-" * 40)
    
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
        num_train_epochs=5,                    
        
        # =====================================================================
        # 🚨 [수정 포인트 2] 뇌 초기화 적응을 위한 학습률(Learning Rate) 상향
        # 기본값 5e-5에서 2e-4로 올려서 초반에 팍팍 배우게 만듭니다.
        # =====================================================================
        learning_rate=2e-4,                    

        per_device_train_batch_size=32,        
        per_device_eval_batch_size=32,
        warmup_steps=500,                      # 데이터가 줄었으므로 웜업 스텝도 살짝 낮춤
        weight_decay=0.01,
        
        label_smoothing_factor=0.1,            
        max_grad_norm=1.0,                     
        
        logging_steps=100,
        eval_strategy="epoch",             
        save_strategy="epoch",                 
        load_best_model_at_end=True,           
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
            # =====================================================================
            # 🚨 [수정 포인트 3] 조기 종료(Early Stopping) 임시 해제
            # 첫 에포크에서 Eval Loss가 튀더라도 5에포크 끝까지 멱살 잡고 끌고 갑니다.
            # =====================================================================
            # EarlyStoppingCallback(early_stopping_patience=1) 
        ] 
    )

    print("🚀 4-Class 황금 밸런스 파인튜닝 학습을 시작합니다!")
    trainer.train()

    # 8. 최종 결과물 강제 저장
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"✅ 학습 완료! 시력을 완전히 되찾은 4-Class 최적화 가중치를 [{output_dir}] 에 성공적으로 저장했습니다.")

if __name__ == "__main__":
    main()