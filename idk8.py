def fake_network_communication():
    print("네트워크 통신 시뮬레이션 중...")
    raise ConnectionResetError("네트워크 연결이 강제로 종료되었습니다.")

try:
    fake_network_communication()
    
except ConnectionResetError as e:
    print(f"네트워크 오류 발생 가정 : {e}")
    
except Exception as e:
    print(f"예상치 못한 오류 발생 : {e}")
    
finally:
    print("사용하던 소켓 자원을 안전하게 회수합니다.ㄴ")