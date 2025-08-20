# 다단계 빌드를 사용한 프로덕션용 Dockerfile
FROM python:3.11-slim as builder

# 시스템 패키지 업데이트 및 필수 도구 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 프로덕션 이미지
FROM python:3.11-slim

# 메타데이터
LABEL maintainer="Way-to-Way Chat Service"
LABEL description="Real-time chat service with WebSocket support"

# 시스템 패키지 (런타임만 필요한 것들)
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 비특권 사용자 생성
RUN useradd --create-home --shell /bin/bash chatapp

# 빌더에서 Python 패키지 복사
COPY --from=builder /root/.local /home/chatapp/.local

# 작업 디렉토리 설정
WORKDIR /app

# 애플리케이션 코드 복사 (민감한 정보 제외)
COPY BE_CHAT/ ./
COPY chat_db_schema.sql ./

# .env 파일이나 민감한 정보는 복사하지 않음
# 환경변수로 런타임에 주입할 예정

# 정적 파일 디렉토리 생성
RUN mkdir -p static logs

# 권한 설정
RUN chown -R chatapp:chatapp /app
USER chatapp

# 환경변수 설정
ENV PATH="/home/chatapp/.local/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=BE_CHAT.settings

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/chat/ || exit 1

# 시작 스크립트 복사
COPY --chown=chatapp:chatapp docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

# 컨테이너 시작 명령 (WebSocket 지원을 위해 daphne 사용)
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "BE_CHAT.asgi:application"]