import pandas as pd
import kagglehub
import os

print("🌐 Kaggle에서 피싱 데이터셋을 다운로드하는 중...")
# 1. kagglehub를 이용한 자동 다운로드
dataset_path = kagglehub.dataset_download("sid321axn/malicious-urls-dataset")
print(f"✅ 다운로드 완료! 원본 데이터 위치: {dataset_path}")

original_file = os.path.join(dataset_path, "malicious_phish.csv")

print(f"\n[{original_file}] 파일을 읽어옵니다...")
try:
    df = pd.read_csv(original_file)
except FileNotFoundError:
    print(f"❌ 에러: 파일을 찾을 수 없습니다!")
    exit()

# 2. 🚀 [변경됨] 4-Class 다중 분류 매핑
# 이진 분류(0,1)의 한계를 깨기 위해 4개의 정밀한 클래스로 나눕니다.
mapping = {
    'benign': 0,        # 정상
    'defacement': 1,    # 악성 (웹사이트 위변조)
    'phishing': 2,      # 악성 (피싱)
    'malware': 3        # 악성 (악성코드)
}

print("🔄 데이터 라벨을 4개의 클래스(0, 1, 2, 3)로 세분화 변환합니다...")
df['label'] = df['type'].map(mapping)
df = df.dropna(subset=['label']) # 혹시 모를 매핑 누락(NaN) 데이터 제거
df['label'] = df['label'].astype(int)
df = df[['url', 'label']]

# 3. 🇰🇷 팀장님의 '한국형 비기' 추가 (피싱이므로 label을 '2'로 설정!)
print("🇰🇷 한국형 피싱 URL 데이터를 수동으로 추가합니다...")
korean_data = [
    {"url": "http://spo-prosecutor-safe.kr", "label": 2},
    {"url": "http://police-check-login.net", "label": 2},
    {"url": "http://mogafe-family-safety.com", "label": 2}, 
    {"url": "http://kb-bank-loan-check.com", "label": 2}, 
    {"url": "http://shinhan-security-auth.net", "label": 2},
    {"url": "http://woori-card-verfiy.co.kr", "label": 2},
    {"url": "http://toto-win-777.net", "label": 2},       
    {"url": "http://adult-secret-site.xyz", "label": 2},  
]

df_korean = pd.DataFrame(korean_data)
df_final = pd.concat([df, df_korean], ignore_index=True)

# 4. 🚀 [변경됨] 제한 해제 및 풀 셔플링
# 6만 개 제한을 풀고 전체 65만 개를 100% 사용하여 섞어줍니다!
print("🌪️ 65만 개 전체 데이터를 셔플링합니다...")
df_final = df_final.sample(frac=1.0, random_state=42).reset_index(drop=True)

# 5. 최종 결과 저장 
output_dir = "./data"
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "train_data.csv")

df_final.to_csv(output_file, index=False)
print(f"\n🎉 완벽해! 총 {len(df_final)}개의 4-Class 데이터가 [{output_file}]에 얌전히 저장되었습니다.")
print("\n📊 [최종 클래스 분포]")
print("0:정상 | 1:위변조 | 2:피싱 | 3:악성코드")
print(df_final['label'].value_counts())