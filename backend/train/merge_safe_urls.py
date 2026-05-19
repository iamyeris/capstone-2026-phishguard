import pandas as pd
import os

def merge_korean_safe_urls():
    # 1. 파일 경로 설정 (🚀 엑셀 파일명으로 변경!)
    existing_data_path = "backend/train/data/train_data.csv"   # 기존 65만개 4-Class 데이터
    new_safe_data_path = "backend/train/data/국내_url.xlsx"     # 🚀 팀장님의 엑셀 파일!

    print(f"📥 기존 학습 데이터({existing_data_path})를 불러옵니다...")
    try:
        df_existing = pd.read_csv(existing_data_path)
    except FileNotFoundError:
        print("❌ 기존 train_data.csv 파일을 찾을 수 없습니다. prepare_data.py를 먼저 돌려주세요!")
        return

    print(f"📥 새로운 한국형 정상 엑셀 데이터({new_safe_data_path})를 불러옵니다...")
    try:
        # 🚀 핵심: read_csv 가 아니라 read_excel 로 엑셀을 바로 읽어옵니다!
        df_new_safe = pd.read_excel(new_safe_data_path, header=None, names=['url'])
    except FileNotFoundError:
        print(f"❌ {new_safe_data_path} 파일을 찾을 수 없습니다. data 폴더 안에 엑셀 파일을 넣어주세요!")
        return
    except Exception as e:
        print(f"❌ 엑셀 파일을 읽는 중 에러가 발생했습니다: {e}")
        print("💡 팁: 터미널에 'pip install openpyxl'을 입력했는지 확인해주세요!")
        return

    # 2. 1000개의 새로운 URL에 '정상(0)' 라벨 일괄 부여!
    df_new_safe['label'] = 0
    df_new_safe = df_new_safe.dropna(subset=['url'])
    print(f"✅ 성공적으로 {len(df_new_safe)}개의 정상(0) 라벨링을 완료했습니다.")

    # 3. 기존 데이터와 완벽하게 합체!
    print("🔄 기존 데이터에 엑셀 데이터를 주입하고 전체 셔플링합니다...")
    df_final = pd.concat([df_existing, df_new_safe], ignore_index=True)
    df_final = df_final.sample(frac=1.0, random_state=42).reset_index(drop=True)

    # 4. 덮어쓰기 저장 (최종본은 다시 모델이 읽기 편한 csv로 저장!)
    df_final.to_csv(existing_data_path, index=False)
    print(f"\n🎉 병합 완료! 총 {len(df_final)}개의 데이터가 [{existing_data_path}]에 덮어씌워졌습니다.")
    
    print("\n📊 [최종 클래스 분포 업데이트]")
    print("0:정상 | 1:위변조 | 2:피싱 | 3:악성코드")
    print(df_final['label'].value_counts())

if __name__ == "__main__":
    merge_korean_safe_urls()