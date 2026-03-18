import torch
import os
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
from datasets import load_dataset
import numpy as np
from sklearn.metrics import accuracy_score, f1_score

# 1. M4 맥북 GPU(MPS) 가속 설정
# M4 칩의 성능을 최대한 활용합니다.
device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")
print(f"🚀 현재 사용 중인 장치: {device}")

# 2. 모델과 토크나이저 불러오기
model_name = "elba-ai/urlbert"
tokenizer = AutoTokenizer.from_pretrained(model_name)

# ⭐️ 수정 포인트: num_labels를 2에서 8로 변경!
model = AutoModelForSequenceClassification.from_pretrained(
    model_name, 
    num_labels=8 
).to(device)

# 3. 데이터셋 로드
# CSV 파일의 label 칸에 0~7 숫자가 들어있어야 합니다.
data_path = "./data/train_data.csv"
dataset = load_dataset('csv', data_files={'train': data_path})
dataset = dataset['train'].train_test_split(test_size=0.2)

# 4. 전처리 함수
def tokenize_function(examples):
    return tokenizer(examples['url'], padding="max_length", truncation=True, max_length=128)

tokenized_datasets = dataset.map(tokenize_function, batched=True)

# 5. 평가 지표 설정 (멀티 클래스 최적화)
def compute_metrics(pred):
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)
    acc = accuracy_score(labels, preds)
    # ⭐️ 수정 포인트: 멀티 클래스이므로 average를 'weighted'로 변경합니다.
    f1 = f1_score(labels, preds, average='weighted')
    return {'accuracy': acc, 'f1': f1}

# 6. 훈련 설정 (M4에 최적화)
training_args = TrainingArguments(
    output_dir="../weights/phishguard_temp",
    num_train_epochs=5,              # 카테고리가 많아졌으므로 학습 횟수를 5회로 살짝 늘렸어요.
    per_device_train_batch_size=16,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    logging_dir='./logs',
    use_mps_device=True,             # M4 가속 활성화
    load_best_model_at_end=True,     # 가장 성적이 좋은 모델을 최종 선택
)

# 7. 훈련 시작
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets['train'],
    eval_dataset=tokenized_datasets['test'],
    compute_metrics=compute_metrics,
)

print("🎓 8단계 분류 학습을 시작합니다. 맥북이 조금 뜨거워질 수 있어요!")
trainer.train()

# 8. 최종 결과물 저장
save_path = "../weights/phishguard_final_model"
model.save_pretrained(save_path)
tokenizer.save_pretrained(save_path)
print(f"✅ 학습 완료! 모델이 {save_path}에 저장되었습니다.")