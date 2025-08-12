from django.urls import path
from . import consumers

# WebSocket URL 라우팅 설정 (Django Channels)
websocket_urlpatterns = [
    # 실시간 채팅용 WebSocket 엔드포인트
    # ws://localhost:8000/ws/chat/{conversation_id}/ 형태로 연결
    path('ws/chat/<uuid:conversation_id>/', consumers.ChatConsumer.as_asgi()),
]