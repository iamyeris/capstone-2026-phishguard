# 1. Playwright 공식 파이썬 이미지 (브라우저 의존성 포함)
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# 2. 작업 디렉토리 설정 (도커 컨테이너 내부의 폴더)
WORKDIR /app

# 3. 파이썬 로그 버퍼링 해제 (터미널에서 로그를 실시간으로 보기 위함)
ENV PYTHONUNBUFFERED=1

# 🚨 [추가된 부분] 리눅스 시스템 패키지 설치 (whois 포함)
RUN apt-get update && apt-get install -y \
    whois \
    && rm -rf /var/lib/apt/lists/*

# 4. 의존성 설치
COPY requirements.txt .
# 무거운 GPU 대신 CPU 전용 PyTorch 설치로 경량화
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt -f https://download.pytorch.org/whl/cpu/torch_stable.html

# 5. 소스 코드 및 모델 가중치(weights) 복사
COPY . .

# 6. Playwright 브라우저 마이너 업데이트 및 설정 (선택적 안정화)
RUN playwright install chromium

# 7. FastAPI 서버 실행
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]