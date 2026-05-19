import csv
import os
import sys

# 프로젝트 최상위 경로를 path에 추가하여 모듈을 찾을 수 있게 함 (경로 에러 방지)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.connection import SessionLocal
from backend.database.models import Whitelist

def insert_direct_data(db):
    """Method 1: 파이썬 코드로 직접 밀어넣기 (소량 데이터 테스트용)"""
    print("🚀 [Method 1] 파이썬 하드코딩 데이터 삽입 시작...")
    
    initial_domains = [
        {"domain": "korea.kr", "description": "대한민국 정부 포털"},
        {"domain": "data.go.kr", "description": "공공데이터포털"},
    ]

    count = 0
    for item in initial_domains:
        # 이미 DB에 존재하는지 확인 (중복 삽입 방지)
        exists = db.query(Whitelist).filter(Whitelist.domain == item["domain"]).first()
        if not exists:
            new_domain = Whitelist(domain=item["domain"], description=item["description"])
            db.add(new_domain)
            count += 1
            
    db.commit()
    print(f"✅ 직접 데이터 {count}개 삽입 완료!\n")


def insert_csv_data(db, csv_file_path):
    """Method 2: CSV 파일 읽어서 대량으로 임포트하기 (실무용)"""
    print(f"🚀 [Method 2] CSV 파일({csv_file_path}) 임포트 시작...")
    
    if not os.path.exists(csv_file_path):
        print(f"⚠️ 에러: {csv_file_path} 파일을 찾을 수 없습니다.")
        return

    count = 0
    # UTF-8 인코딩으로 CSV 파일 열기
    with open(csv_file_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file) # 첫 줄(domain, description)을 Key로 인식
        
        for row in reader:
            domain = row.get("domain", "").strip()
            description = row.get("description", "").strip()
            
            if not domain:
                continue # 도메인이 비어있으면 건너뜀

            # 중복 체크
            exists = db.query(Whitelist).filter(Whitelist.domain == domain).first()
            if not exists:
                new_domain = Whitelist(domain=domain, description=description)
                db.add(new_domain)
                count += 1
                
    db.commit()
    print(f"✅ CSV 데이터 {count}개 삽입 완료!")

if __name__ == "__main__":
    # DB 세션 열기
    db = SessionLocal()
    
    try:
        # --- 원하는 방식을 주석 해제해서 사용하세요! ---
        
        # 1. 직접 하드코딩한 데이터 넣기
        insert_direct_data(db)
        
        # 2. CSV 파일에서 가져오기 (경로는 본인 환경에 맞게 수정)
        csv_path = "../data/processed/whitelist.csv" # 또는 "whitelist.csv"
        insert_csv_data(db, csv_path)
        
    except Exception as e:
        print(f"🚨 데이터 삽입 중 에러 발생: {e}")
        db.rollback() # 에러 나면 저장 취소
    finally:
        db.close() # DB 작업 끝내기