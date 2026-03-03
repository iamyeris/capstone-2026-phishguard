# 1. Playwright 공식 파이썬 이미지 사용 (브라우저 의존성 완벽 해결)
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 환경 변수 설정 (파이썬 로그가 버퍼링 없이 바로 출력되도록)
ENV PYTHONUNBUFFERED=1

# 4. 패키지 설치 파일 복사 및 설치
COPY requirements.txt .
# 💡 꿀팁: 도커 컨테이너는 보통 CPU를 쓰므로, 무거운 GPU용 PyTorch 대신 CPU 전용을 설치하여 용량을 확 줄입니다.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt -f https://download.pytorch.org/whl/cpu/torch_stable.html

# 5. 소스 코드 전체 복사
COPY . .
    
# 6. FastAPI 서버 실행 (포트 8000)
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]