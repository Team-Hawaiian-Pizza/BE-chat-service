#!/bin/bash
# Docker 컨테이너 시작 스크립트

set -e

echo "🚀 채팅 서비스 시작 중..."

# 환경변수 확인
echo "📋 환경 설정 확인:"
echo "  - DEBUG: ${DEBUG:-True}"
echo "  - DB_ENGINE: ${DB_ENGINE:-django.db.backends.sqlite3}"
echo "  - DB_HOST: ${DB_HOST:-localhost}"
echo "  - REDIS_HOST: ${REDIS_HOST:-127.0.0.1}"

# 데이터베이스 연결 대기 (MySQL 사용시)
if [[ "${DB_ENGINE}" == *"mysql"* ]]; then
    echo "⏳ MySQL 데이터베이스 연결 대기 중..."
    
    # MySQL 연결 확인 함수
    check_mysql() {
        python -c "
import MySQLdb
import sys
try:
    conn = MySQLdb.connect(
        host='${DB_HOST}', 
        port=${DB_PORT:-3306}, 
        user='${DB_USER}', 
        passwd='${DB_PASSWORD}'
    )
    conn.close()
    print('✅ MySQL 연결 성공')
except Exception as e:
    print(f'❌ MySQL 연결 실패: {e}')
    sys.exit(1)
        "
    }
    
    # 최대 30초 동안 연결 시도
    for i in {1..30}; do
        if check_mysql; then
            break
        fi
        echo "  재시도 중... ($i/30)"
        sleep 1
    done
fi

# Redis 연결 확인 (선택사항)
if [[ "${REDIS_HOST}" != "" ]]; then
    echo "⏳ Redis 연결 확인 중..."
    python -c "
import redis
try:
    r = redis.Redis(host='${REDIS_HOST}', port=${REDIS_PORT:-6379})
    r.ping()
    print('✅ Redis 연결 성공')
except Exception as e:
    print(f'⚠️ Redis 연결 실패 (계속 진행): {e}')
    "
fi

# 데이터베이스 마이그레이션
echo "🔄 데이터베이스 마이그레이션 실행 중..."
python manage.py migrate --noinput

# 정적 파일 수집 (프로덕션)
if [[ "${DEBUG}" == "False" ]]; then
    echo "📁 정적 파일 수집 중..."
    python manage.py collectstatic --noinput
fi

# 슈퍼유저 생성 (개발용)
if [[ "${DEBUG}" == "True" ]] && [[ "${DJANGO_SUPERUSER_USERNAME}" != "" ]]; then
    echo "👤 슈퍼유저 생성 중..."
    python manage.py createsuperuser --noinput || echo "슈퍼유저가 이미 존재합니다."
fi

echo "✅ 초기화 완료!"
echo "🎯 서버 시작: $@"

# 전달받은 명령어 실행
exec "$@"