import pandas as pd
import requests
import time

def create_benchmark_dataset():
    print("🚀 벤치마크 데이터 수집을 시작합니다. (약 5~10초 소요)")
    start_time = time.time()
    
    # ---------------------------------------------------------
    # 1. 악성(Phishing) URL 수집 (Label: 1)
    # ---------------------------------------------------------
    print("\n📥 [1/3] OpenPhish에서 최신 글로벌 피싱 URL 500개 수집 중...")
    try:
        # 봇 차단을 막기 위한 헤더 추가
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        phish_url = "https://openphish.com/feed.txt"
        phish_response = requests.get(phish_url, headers=headers)
        phish_response.raise_for_status()
        
        phish_list = phish_response.text.splitlines()[:500]
        df_phish = pd.DataFrame({'url': phish_list, 'label': 1})
        print(f"  ✅ 피싱 데이터 {len(df_phish)}개 수집 완료!")
    except Exception as e:
        print(f"  ❌ 피싱 데이터 수집 실패: {e}")
        return
    
    # ---------------------------------------------------------
    # 2. 정상(Benign) URL 수집 (Label: 0)
    # ---------------------------------------------------------
    print("\n📥 [2/3] Tranco 리스트에서 정상 웹사이트 수집 중...")
    try:
        # Tranco 최신 Top 100만 리스트 (압축파일 형태로 바로 읽어옵니다)
        tranco_url = "https://tranco-list.eu/top-1m.csv.zip"
        df_tranco_full = pd.read_csv(tranco_url, names=['rank', 'domain'])
        
        # 도메인 앞에 https://www. 를 붙여서 완벽한 URL 형태로 변환
        df_tranco_full['url'] = "https://www." + df_tranco_full['domain']
        
        # A. 글로벌 최상위 정상 사이트 500개 추출
        df_benign_global = df_tranco_full.head(500)[['url']].copy()
        df_benign_global['label'] = 0
        
        # B. 한국형(.kr) 최상위 정상 사이트 500개 추출 (교수님 방어용 필살기!)
        df_kr = df_tranco_full[df_tranco_full['domain'].str.endswith('.kr')]
        df_benign_kr = df_kr.head(500)[['url']].copy()
        df_benign_kr['label'] = 0
        
        print(f"  ✅ 글로벌 정상 {len(df_benign_global)}개, 한국 정상 {len(df_benign_kr)}개 수집 완료!")
    except Exception as e:
        print(f"  ❌ 정상 데이터 수집 실패: {e}")
        return
    
    # ---------------------------------------------------------
    # 3. 데이터 병합 및 셔플링 후 저장
    # ---------------------------------------------------------
    print("\n✂️ [3/3] 데이터를 섞고 CSV로 저장하는 중...")
    # 피싱 500 + 글로벌 정상 500 + 한국 정상 500 = 총 1500개
    final_df = pd.concat([df_phish, df_benign_global, df_benign_kr])
    
    # 데이터 순서 무작위로 섞기 (머신러닝 평가의 기본)
    final_df = final_df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # CSV 파일로 저장
    save_path = 'final_benchmark.csv'
    final_df.to_csv(save_path, index=False)
    
    elapsed = time.time() - start_time
    print("\n" + "="*40)
    print(f"🎉 벤치마크 데이터셋 생성 성공! ({elapsed:.1f}초 소요)")
    print(f"📁 저장된 파일: {save_path}")
    print("="*40)
    print("[데이터 구성]")
    print(final_df['label'].value_counts().rename(index={0: '정상 (0)', 1: '피싱 (1)'}))

if __name__ == "__main__":
    create_benchmark_dataset()