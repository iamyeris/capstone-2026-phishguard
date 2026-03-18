import pandas as pd

# 1. 캐글에서 다운로드한 파일 불러오기 (파일명 확인!)
# 보통 다운로드하면 malicious_phish.csv 일 거예요.
original_file = "./data/malicious_phish.csv" 
df = pd.read_csv(original_file)

# 2. 우리만의 8단계 규칙으로 자동 변환 (매핑)
# 캐글 레이블 -> 우리 번호
mapping = {
    'benign': 0,      # 정상
    'phishing': 1,    # 일반 피싱
    'malware': 4,     # 악성코드
    'defacement': 0,  # 정상 취급
    'Other': 7  # 판단 보류
}

# 'type' 열을 읽어서 우리 'label'로 변환
df['label'] = df['type'].map(mapping)
# 필요한 열(url, label)만 남기기
df = df[['url', 'label']]

# 3. ⭐️ 팀장님의 '한국형 비기' 추가하기
# 여기에 한국형 사례 몇 개만 샘플로 넣어볼게요. 
# 나중에 팀장님이 더 많이 수집해서 여기 리스트에 추가하면 됩니다!
korean_data = [
    {"url": "http://spo-prosecutor-safe.kr", "label": 2},  # 기관 사칭
    {"url": "http://police-check-login.net", "label": 2},
    {"url": "http://kb-bank-loan-check.com", "label": 3},  # 금융 사기
    {"url": "http://toto-win-777.net", "label": 5},       # 불법 도박
    {"url": "http://adult-secret-site.xyz", "label": 6},  # 유해 콘텐츠
]

# 한국 데이터를 기존 데이터 밑에 합치기
df_korean = pd.DataFrame(korean_data)
df_final = pd.concat([df, df_korean], ignore_index=True)

# 4. 데이터가 너무 많으면 M4라도 힘드니까 3만 개만 뽑기 (선택 사항)
df_final = df_final.sample(n=30000, random_state=42)

# 5. 최종 결과 저장!
df_final.to_csv("./data/train_data.csv", index=False)
print("✅ 데이터 변환 완료! 이제 훈련을 시작할 수 있습니다.")