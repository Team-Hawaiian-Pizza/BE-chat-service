"""
ASGI config for BE_CHAT project - Django Channels용 비동기 설정
HTTP와 WebSocket 프로토콜을 모두 처리할 수 있도록 구성
"""

import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from chat.routing import websocket_urlpatterns

# Django 설정 모듈 지정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BE_CHAT.settings')

# 프로토콜별 라우터 설정
application = ProtocolTypeRouter({
    # 일반 HTTP 요청 처리 (REST API)
    "http": get_asgi_application(),
    
    # WebSocket 요청 처리 (실시간 채팅)
    "websocket": AuthMiddlewareStack(  # 인증 미들웨어 적용
        URLRouter(
            websocket_urlpatterns  # chat/routing.py의 WebSocket URL 패턴들
        )
    ),
})
