import pandas as pd

# 데이터 불러오기
df = pd.read_csv("backend/train/data/train_data.csv")

# 1. 네이버가 도대체 몇 번으로 학습되었는지 확인
print("🔍 네이버 데이터 확인:")
print(df[df['url'].str.contains("naver.com")].head(5))

# 2. 각 라벨(0~3)별로 어떤 사이트들이 들어있는지 3개씩 뽑아보기
print("\n📊 라벨별 샘플 데이터 확인:")
for i in range(4):
    print(f"\n--- [Label {i}] ---")
    print(df[df['label'] == i]['url'].head(3).tolist())