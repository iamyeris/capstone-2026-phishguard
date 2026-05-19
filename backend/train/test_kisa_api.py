import requests
import pandas as pd
import json

def test_kisa_api():
    # 1. API 키 및 기본 설정 (알려준 Decoding 인증키 적용)
    # 실제 서비스에서는 .env 파일로 숨기는 것 잊지 마!
    api_key = "7de6f367a6129ffb26876bef95a2882be89025f29d5757775e5f0cafd84c8906"
    
    # ⚠️ 공공데이터포털 상세 페이지에서 확인한 정확한 URL로 변경해야 해!
    # 보통 아래와 같은 형식을 띱니다. (15109780은 네임스페이스 ID)
    api_url = "https://api.odcloud.kr/api/15109780/v1/uddi:7de6f367a6129ffb26876bef95a2882be89025f29d5757775e5f0cafd84c8906"
    
    print("🚀 KISA 피싱 사이트 API 호출 테스트 시작...")
    
    params = {
        'page': 1,
        'perPage': 10,  # 테스트용이니까 일단 10개만 가볍게!
        'serviceKey': api_key,
        'returnType': 'JSON'
    }
    
    try:
        # API 요청 보내기
        response = requests.get(api_url, params=params)
        response.raise_for_status() # 에러가 나면 여기서 멈춤
        
        result = response.json()
        
        # 전체 JSON 응답 구조를 예쁘게 출력해서 확인 (어떤 필드명으로 URL이 오는지 파악하기 위함)
        print("\n✅ [API 응답 성공] JSON 구조 확인:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 만약 'data'라는 리스트 안에 정보가 담겨 온다면 추출 테스트
        if 'data' in result:
            print(f"\n총 {len(result['data'])}개의 데이터 항목을 찾았습니다.")
            # 첫 번째 데이터의 키(필드명)들을 확인
            if len(result['data']) > 0:
                print(f"데이터 필드 목록: {list(result['data'][0].keys())}")
                
    except requests.exceptions.RequestException as e:
        print(f"\n❌ API 호출 중 에러 발생: {e}")
        print("URL이 정확한지, 인증키 사용 등록이 승인되었는지 확인해 주세요.")

if __name__ == "__main__":
    test_kisa_api()