from django.urls import path
from . import views

# chat 앱의 URL 라우팅 설정
urlpatterns = [
    # 웹 UI (임시 프론트엔드)
    path('', views.chat_index, name='chat-index'),  # 채팅 메인 화면
    
    # MSA 외부 제공 API (다른 서비스에서 호출)
    path('conversations/<uuid:id>/', views.ConversationDetailView.as_view(), name='conversation-detail'),
    
    # 내부 서비스 API들
    path('users/<str:user_id>/conversations/', views.user_conversations, name='user-conversations'),  # 사용자 대화방 목록
    path('conversations/', views.create_conversation, name='create-conversation'),  # 대화방 생성
    
    # 메시지 관련 API
    path('conversations/<uuid:conversation_id>/messages/', views.conversation_messages, name='conversation-messages'),  # 메시지 목록 (기존)
    path('conversations/<uuid:conversation_id>/messages/paginated/', views.conversation_messages_paginated, name='conversation-messages-paginated'),  # 페이지네이션 메시지 목록
    path('conversations/<uuid:conversation_id>/messages/before/', views.conversation_messages_before, name='conversation-messages-before'),  # 특정 메시지 이전 조회
    path('conversations/<uuid:conversation_id>/messages/after/', views.conversation_messages_after, name='conversation-messages-after'),  # 특정 메시지 이후 조회
    path('conversations/<uuid:conversation_id>/messages/send/', views.send_message, name='send-message'),  # 메시지 전송
    path('messages/<uuid:message_id>/read/', views.mark_message_as_read, name='mark-message-read'),  # 메시지 읽음 처리
]