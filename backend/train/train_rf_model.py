import pandas as pd
import urllib.parse
import re
import time
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# ---------------------------------------------------------
# 1. 🔍 [핵심] URL에서 팩트(Feature)를 숫자로 뽑아내는 함수
# ---------------------------------------------------------
def extract_features(url):
    if not isinstance(url, str):
        url = str(url)
        
    url_lower = url.lower()
    
    # 🌟 만약 파싱에 실패하더라도 반환할 수 있도록 기본값 미리 세팅
    features = {
        'url_length': len(url),
        'domain_length': 0,
        'num_dots': 0,
        'num_hyphens': 0,
        'has_at_symbol': 0,
        'is_ip_address': 0,
        'has_suspicious_keyword': 0,
        'has_malware_ext': 0,
        'is_trusted_cloud': 0
    }
    
    # 🌟 위험한 파싱 작업은 try 블록 안에 가둡니다.
    try:
        parsed = urllib.parse.urlparse(url_lower if "://" in url_lower else f"http://{url_lower}")
        domain = parsed.netloc

        features['domain_length'] = len(domain)
        features['num_dots'] = domain.count('.')
        features['num_hyphens'] = domain.count('-')
        features['has_at_symbol'] = 1 if '@' in parsed.netloc else 0
        features['is_ip_address'] = 1 if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", domain.split(':')[0]) else 0
        
        trusted_clouds = ['googleusercontent.com', 'amazonaws.com', 'cloudfront.net', 'github.io']
        features['is_trusted_cloud'] = 1 if any(domain.endswith(c) for c in trusted_clouds) else 0
    except Exception:
        # 쓰레기 데이터라서 파싱 에러가 나면 그냥 기본값(0)을 유지하고 부드럽게 넘어감
        pass

    # 텍스트 단순 검색은 파싱 성공 여부와 상관없이 무조건 실행
    suspicious_keywords = ['login', 'verify', 'update', 'account', 'secure', 'banking', 'confirm', 'free']
    features['has_suspicious_keyword'] = 1 if any(kw in url_lower for kw in suspicious_keywords) else 0
    
    malware_extensions = ['.apk', '.exe', '.zip', '.rar', '.bin']
    features['has_malware_ext'] = 1 if any(url_lower.endswith(ext) for ext in malware_extensions) else 0

    return features

# ---------------------------------------------------------
# 2. 🚀 메인 훈련 프로세스
# ---------------------------------------------------------
def main():
    start_time = time.time()
    data_path = "./data/train_data.csv" # 기존 60만개 데이터 경로 지정
    
    print(f"📥 1. 데이터 로드 중... ({data_path})")
    if not os.path.exists(data_path):
        print("❌ [에러] 데이터를 찾을 수 없습니다. 경로를 확인해주세요.")
        return
        
    df = pd.read_csv(data_path)
    # 결측치 제거
    df = df.dropna(subset=['url', 'label'])
    
    # 테스트용으로 너무 오래 걸리면 아래 줄의 주석을 풀고 샘플링해서 먼저 돌려보세요
    # df = df.sample(n=100000, random_state=42) 
    
    print(f"⚙️ 2. {len(df)}개 URL의 특징(Feature) 추출 중... (CPU 풀가동, 1~2분 소요)")
    # URL 컬럼을 돌면서 특징 딕셔너리를 뽑아내고, DataFrame으로 변환
    features_df = pd.DataFrame(df['url'].apply(extract_features).tolist())
    
    # 입력 데이터(X)와 정답 라벨(y) 분리
    X = features_df
    y = df['label']
    
    print("✂️ 3. 학습/검증 데이터 8:2 분할 중...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("🧠 4. 랜덤 포레스트 훈련 시작! (M4 깡패 성능을 믿어보세요)")
    # 트리 100개, CPU 코어 전부 사용(n_jobs=-1)
    rf_model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf_model.fit(X_train, y_train)
    
    print("📊 5. 검증 데이터로 성능 평가 중...")
    y_pred = rf_model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"🎯 최종 정확도(Accuracy): {acc * 100:.2f}%\n")
    print(classification_report(y_test, y_pred))
    
    print("💡 [모델 채점 기준 (Feature Importance)]")
    importances = pd.DataFrame({
        'Feature': X.columns,
        'Importance': rf_model.feature_importances_
    }).sort_values(by='Importance', ascending=False)
    print(importances)
    
    # ---------------------------------------------------------
    # 3. 💾 학습된 모델 가중치 파일 저장
    # ---------------------------------------------------------
    output_dir = "../weights"
    os.makedirs(output_dir, exist_ok=True)
    model_save_path = os.path.join(output_dir, "phishguard_rf_model.pkl")
    
    joblib.dump(rf_model, model_save_path)
    
    elapsed = time.time() - start_time
    print(f"\n🎉 모든 작업 완료! ({elapsed:.1f}초 소요)")
    print(f"저장된 모델 경로: {model_save_path}")

if __name__ == "__main__":
    main()