# 멀티스테이지 빌드
FROM node:18-alpine AS frontend-builder

# 프론트엔드 빌드
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Python 백엔드
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 백엔드 코드 복사
COPY backend/ ./

# 프론트엔드 빌드 결과 복사
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# 빌드 파일 확인을 위한 디버그
RUN ls -la frontend/
RUN ls -la frontend/build/
RUN find . -name "index.html" -type f

# 포트 설정
EXPOSE $PORT

# 앱 실행
CMD ["python", "app/main.py"]
