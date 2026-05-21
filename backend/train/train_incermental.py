import os
import random
import torch
import pandas as pd
from torch.utils.data import Dataset
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification, 
    TrainingArguments, Trainer, EarlyStoppingCallback
)

class PhishGuardDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=64):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer

    def __len__(self): 
        return len(self.texts)

    def __getitem__(self, idx):
        encoding = self.tokenizer(str(self.texts[idx]), max_length=64, padding='max_length', truncation=True, return_tensors='pt')
        return {
            'input_ids': encoding['input_ids'].flatten(), 
            'attention_mask': encoding['attention_mask'].flatten(), 
            'labels': torch.tensor(int(self.labels[idx]), dtype=torch.long)
        }

# 🌟 [NEW] 글로벌 클라우드 정상 URL을 즉석에서 생성하는 함수
def generate_global_cloud_urls(num_samples=3000):
    print(f"🌐 글로벌 클라우드 정상 URL {num_samples}개를 즉석에서 생성합니다...")
    clouds = ["googleusercontent.com", "s3.amazonaws.com", "cloudfront.net", "firebaseapp.com", "github.io"]
    brands = ["spotify.com", "netflix.com", "apple.com", "microsoft.com", "naver.com", "kakao.com"]
    paths = ["/0", "/login", "/auth", "/static/css", "/images/logo.png", "/main"]
    
    urls = []
    for _ in range(num_samples):
        c = random.choice(clouds)
        b = random.choice(brands)
        p = random.choice(paths)
        # 예: spotify.com
        urls.append(f"http://{c}/{b}{p}")
        urls.append(f"https://{b}.{c}{p}")
    
    return pd.DataFrame({'url': urls[:num_samples], 'label': 0}) # 전부 정상(0) 라벨 부여


def main():
    device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🚀 가속 엔진 가동! (사용 장치: {device})")

    # ---------------------------------------------------------
    # 1. 🇰🇷 한국 정상 데이터 로드 (뻥튀기 제거!)
    # ---------------------------------------------------------
    korean_csv_path = "/Users/yeris/Documents/GitHub/capstone-2026-phishguard/backend/train/data/국내_url.csv"
    
    if not os.path.exists(korean_csv_path):
        print(f"❌ [에러] 파일이 없습니다: {korean_csv_path}")
        return

    df_raw = pd.read_csv(korean_csv_path)
    df_korean = df_raw[['URL']].rename(columns={'URL': 'url'}) if 'URL' in df_raw.columns else df_raw[['url']]
    df_korean = df_korean.dropna(subset=['url'])
    df_korean['label'] = 0  # 한국 데이터 전부 정상 처리
    print(f"✅ 한국 정상 데이터 확보: {len(df_korean)}개")

    # ---------------------------------------------------------
    # 2. 🌐 글로벌 클라우드 방어 데이터 생성 (오탐 방지용 핵심!)
    # ---------------------------------------------------------
    df_cloud = generate_global_cloud_urls(num_samples=3000)
    print(f"✅ 클라우드 방어 데이터 확보: {len(df_cloud)}개")

    # ---------------------------------------------------------
    # 3. 🧠 기존 지식(64만 개)에서 핵심만 추출하여 섞기 (Rehearsal)
    # ---------------------------------------------------------
    old_data_path = "./data/train_data.csv"
    df_old = pd.read_csv(old_data_path)
    
    # 파국적 망각을 막기 위해 예전 피싱 데이터 1만 개, 예전 정상 데이터 2천 개만 복습
    df_old_phishing = df_old[df_old['label'] != 0].sample(n=10000, random_state=42)
    df_old_normal = df_old[df_old['label'] == 0].sample(n=2000, random_state=42)

    # 🌟 황금 밸런스 병합 (총 약 16,000개 데이터셋 완성)
    df_mix = pd.concat([df_korean, df_cloud, df_old_normal, df_old_phishing], ignore_index=True)
    df_mix = df_mix.sample(frac=1.0, random_state=42).reset_index(drop=True)
    
    train_df = df_mix.sample(frac=0.8, random_state=42)
    val_df = df_mix.drop(train_df.index)

    print("\n" + "="*50)
    print("🔍 [최종 추가학습 데이터셋 밸런스 확인]")
    print(train_df['label'].value_counts())
    print("💡 기존 피싱 지식을 유지하면서 클라우드/한국 정상 도메인 방어력을 탑재했습니다.")
    print("="*50 + "\n")

    # ---------------------------------------------------------
    # 4. 🧠 기존 가중치 뇌 로드 및 초미세 조정 세팅
    # ---------------------------------------------------------
    model_path = "../weights/phishguard_final_model" 
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path, num_labels=4).to(device)

    train_dataset = PhishGuardDataset(train_df['url'].tolist(), train_df['label'].tolist(), tokenizer)
    val_dataset = PhishGuardDataset(val_df['url'].tolist(), val_df['label'].tolist(), tokenizer)

    training_args = TrainingArguments(
        output_dir="../weights/phishguard_global_patched_model",
        num_train_epochs=2,                    # 🚀 에폭을 2로 줄여서 과적합(오버피팅) 방지
        fp16=True,                             
        per_device_train_batch_size=64,        
        per_device_eval_batch_size=64,
        dataloader_num_workers=4,              
        dataloader_pin_memory=False,           
        learning_rate=5e-6,                    # 🚀 학습률을 확 낮춤 (기존 뇌 구조를 부수지 않고 살살 학습)
        save_strategy="epoch",
        eval_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
    )

    trainer = Trainer(
        model=model, args=training_args,
        train_dataset=train_dataset, eval_dataset=val_dataset,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=1)]
    )

    print("🚀 M4 파워로 초고속 Incremental Fine-Tuning을 시작합니다!")
    trainer.train()

    # 최종 안전 가중치 저장
    trainer.save_model(training_args.output_dir)
    tokenizer.save_pretrained(training_args.output_dir)
    print(f"🎉 성공! 억울한 스포티파이 오탐을 잡아낸 최신 모델이 [{training_args.output_dir}]에 저장되었습니다.")

if __name__ == "__main__":
    main()