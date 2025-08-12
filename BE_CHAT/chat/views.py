from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404, render
from django.db.models import Q
from .models import Conversation, Message, DeliveryReceipt
from .serializers import ConversationSerializer, MessageSerializer, DeliveryReceiptSerializer
from .events import publish_message_created_event
import json


class ConversationDetailView(generics.RetrieveAPIView):
    """특정 대화방 조회 - MSA 외부 제공 API"""
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    lookup_field = 'id'  # URL에서 id 파라미터로 조회


@api_view(['GET'])
def user_conversations(request, user_id):
    """특정 유저의 모든 대화방 조회"""
    # user_id가 participant1 또는 participant2인 활성화된 대화방들 조회
    conversations = Conversation.objects.filter(
        Q(participant1_id=user_id) | Q(participant2_id=user_id),
        is_active=True
    ).order_by('-updated_at')  # 최근 업데이트된 순으로 정렬
    
    serializer = ConversationSerializer(conversations, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def create_conversation(request):
    """새로운 대화방 생성 (중복 방지 로직 포함)"""
    participant1_id = request.data.get('participant1_id')
    participant2_id = request.data.get('participant2_id')
    
    # 필수 파라미터 검증
    if not participant1_id or not participant2_id:
        return Response({'error': 'participant1_id와 participant2_id가 필요합니다.'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # 이미 존재하는 대화방인지 확인 (순서 상관없이 검색)
    existing_conversation = Conversation.objects.filter(
        Q(participant1_id=participant1_id, participant2_id=participant2_id) |
        Q(participant1_id=participant2_id, participant2_id=participant1_id)
    ).first()
    
    # 기존 대화방이 있으면 그대로 반환
    if existing_conversation:
        serializer = ConversationSerializer(existing_conversation)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    # 새 대화방 생성
    conversation = Conversation.objects.create(
        participant1_id=participant1_id,
        participant2_id=participant2_id
    )
    
    serializer = ConversationSerializer(conversation)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def conversation_messages(request, conversation_id):
    """대화방의 메시지 목록 조회 (삭제되지 않은 메시지만)"""
    conversation = get_object_or_404(Conversation, id=conversation_id)
    # 삭제되지 않은 메시지들만 시간순으로 조회
    messages = conversation.messages.filter(is_deleted=False).order_by('created_at')
    
    serializer = MessageSerializer(messages, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def send_message(request, conversation_id):
    """메시지 전송 (이벤트 발행 포함)"""
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    # 요청 데이터에 conversation 정보 추가
    data = request.data.copy()
    data['conversation'] = conversation.id
    
    serializer = MessageSerializer(data=data)
    if serializer.is_valid():
        # 메시지 저장
        message = serializer.save(conversation=conversation)
        
        # MSA 이벤트 발행 (다른 서비스들이 구독할 수 있음)
        publish_message_created_event(message)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
def mark_message_as_read(request, message_id):
    """메시지를 읽음으로 표시 (읽음 확인 시스템)"""
    message = get_object_or_404(Message, id=message_id)
    user_id = request.data.get('user_id')
    
    # 필수 파라미터 검증
    if not user_id:
        return Response({'error': 'user_id가 필요합니다.'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # 기존 기록이 있으면 업데이트, 없으면 새로 생성
    receipt, created = DeliveryReceipt.objects.update_or_create(
        message=message,
        user_id=user_id,
        defaults={'status': 'read'}  # 상태를 'read'로 설정
    )
    
    serializer = DeliveryReceiptSerializer(receipt)
    return Response(serializer.data)


def chat_index(request):
    """
    채팅 메인 화면 - 간단한 웹 UI 제공
    Django 템플릿을 사용한 기본적인 채팅 인터페이스
    프론트엔드 개발 전까지 임시로 사용
    """
    return render(request, 'chat/index.html')
