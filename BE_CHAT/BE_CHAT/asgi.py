"""
ASGI config for BE_CHAT project - Django Channels용 비동기 설정
HTTP와 WebSocket 프로토콜을 모두 처리할 수 있도록 구성
"""

import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

# Django 설정 모듈 지정 및 초기화
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BE_CHAT.settings')
django.setup()

# Django 초기화 후 import
from chat.routing import websocket_urlpatterns

# HTTP 애플리케이션 먼저 초기화
django_asgi_app = get_asgi_application()

# 프로토콜별 라우터 설정
application = ProtocolTypeRouter({
    # 일반 HTTP 요청 처리 (REST API)
    "http": django_asgi_app,
    
    # WebSocket 요청 처리 (실시간 채팅)
    "websocket": AuthMiddlewareStack(  # 인증 미들웨어 적용
        URLRouter(
            websocket_urlpatterns  # chat/routing.py의 WebSocket URL 패턴들
        )
    ),
})
