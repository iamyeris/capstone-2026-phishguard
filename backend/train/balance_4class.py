import pandas as pd

def balance_4class_dataset():
    print("📥 데이터 로드 및 4-Class 밸런싱을 시작합니다...")
    df = pd.read_csv("./data/train_data.csv").dropna(subset=['url', 'label'])
    
    df0 = df[df['label'] == 0]
    df1 = df[df['label'] == 1]
    df2 = df[df['label'] == 2]
    df3 = df[df['label'] == 3]
    
    # 4개 그룹 중 가장 개수가 적은 그룹의 수(아마 3번 악성코드)를 찾습니다.
    min_count = min(len(df0), len(df1), len(df2), len(df3)) 
    
    print(f"⚖️ 각 클래스당 {min_count}개씩 샘플링하여 1:1:1:1 비율을 맞춥니다...")
    
    df_balanced = pd.concat([
        df0.sample(n=min_count, random_state=42),
        df1.sample(n=min_count, random_state=42),
        df2.sample(n=min_count, random_state=42),
        df3.sample(n=min_count, random_state=42)
    ]).sample(frac=1, random_state=42).reset_index(drop=True)
    
    save_path = "./data/balanced_4class_train.csv"
    df_balanced.to_csv(save_path, index=False)
    print(f"✅ 4-Class 황금 밸런스 데이터셋 완성! (총 {len(df_balanced)}개) -> {save_path}")

if __name__ == "__main__":
    balance_4class_dataset()