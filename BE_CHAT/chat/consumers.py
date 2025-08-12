import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.shortcuts import get_object_or_404
from .models import Conversation, Message
from .serializers import MessageSerializer
from .events import publish_message_created_event


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket 채팅 소비자 - 실시간 채팅 기능 제공
    Django Channels를 사용한 비동기 WebSocket 처리
    """
    
    async def connect(self):
        """클라이언트 WebSocket 연결 처리"""
        # URL에서 conversation_id 추출
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        # 그룹명 생성 (같은 대화방의 모든 연결을 묶음)
        self.conversation_group_name = f'chat_{self.conversation_id}'
        
        # 대화방이 실제로 존재하는지 확인
        conversation = await self.get_conversation(self.conversation_id)
        if not conversation:
            await self.close()  # 존재하지 않으면 연결 종료
            return
        
        # 대화방 그룹에 현재 연결 추가
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )
        
        # WebSocket 연결 수락
        await self.accept()
        
        # 연결 즉시 기존 대화 기록 전송
        await self.send_conversation_history()

    async def disconnect(self, close_code):
        """클라이언트 WebSocket 연결 해제 처리"""
        # 대화방 그룹에서 현재 연결 제거
        await self.channel_layer.group_discard(
            self.conversation_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """클라이언트로부터 메시지 수신 처리"""
        try:
            # JSON 파싱
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            # 메시지 타입에 따른 처리 분기
            if message_type == 'chat_message':
                await self.handle_chat_message(text_data_json)  # 채팅 메시지
            elif message_type == 'mark_as_read':
                await self.handle_mark_as_read(text_data_json)  # 읽음 처리
            elif message_type == 'typing':
                await self.handle_typing(text_data_json)  # 타이핑 상태
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format'
            }))

    async def handle_chat_message(self, data):
        sender_id = data.get('sender_id')
        content = data.get('content')
        message_type = data.get('message_type', 'text')
        
        if not sender_id or not content:
            await self.send(text_data=json.dumps({
                'error': 'sender_id와 content가 필요합니다.'
            }))
            return
        
        # 메시지를 데이터베이스에 저장
        message = await self.create_message(
            conversation_id=self.conversation_id,
            sender_id=sender_id,
            content=content,
            message_type=message_type
        )
        
        if message:
            # 메시지를 그룹의 모든 멤버에게 브로드캐스트
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'chat_message',
                    'message': await self.serialize_message(message)
                }
            )
            
            # 이벤트 발행 (비동기)
            await self.publish_message_event(message)

    async def handle_mark_as_read(self, data):
        message_id = data.get('message_id')
        user_id = data.get('user_id')
        
        if message_id and user_id:
            await self.mark_message_as_read(message_id, user_id)
            
            # 읽음 상태를 그룹에 알림
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'message_read',
                    'message_id': message_id,
                    'user_id': user_id
                }
            )

    async def handle_typing(self, data):
        user_id = data.get('user_id')
        is_typing = data.get('is_typing', False)
        
        # 타이핑 상태를 다른 참가자에게 알림
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'typing_status',
                'user_id': user_id,
                'is_typing': is_typing
            }
        )

    # 그룹 메시지 핸들러들
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))

    async def message_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_read',
            'message_id': event['message_id'],
            'user_id': event['user_id']
        }))

    async def typing_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing_status',
            'user_id': event['user_id'],
            'is_typing': event['is_typing']
        }))

    # 데이터베이스 작업들
    @database_sync_to_async
    def get_conversation(self, conversation_id):
        try:
            return Conversation.objects.get(id=conversation_id, is_active=True)
        except Conversation.DoesNotExist:
            return None

    @database_sync_to_async
    def create_message(self, conversation_id, sender_id, content, message_type):
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            message = Message.objects.create(
                conversation=conversation,
                sender_id=sender_id,
                content=content,
                message_type=message_type
            )
            return message
        except Conversation.DoesNotExist:
            return None

    @database_sync_to_async
    def serialize_message(self, message):
        serializer = MessageSerializer(message)
        return serializer.data

    @database_sync_to_async
    def get_conversation_messages(self, conversation_id):
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            messages = conversation.messages.filter(is_deleted=False).order_by('created_at')
            serializer = MessageSerializer(messages, many=True)
            return serializer.data
        except Conversation.DoesNotExist:
            return []

    @database_sync_to_async
    def mark_message_as_read(self, message_id, user_id):
        from .models import DeliveryReceipt
        try:
            message = Message.objects.get(id=message_id)
            receipt, created = DeliveryReceipt.objects.update_or_create(
                message=message,
                user_id=user_id,
                defaults={'status': 'read'}
            )
            return receipt
        except Message.DoesNotExist:
            return None

    @database_sync_to_async
    def publish_message_event(self, message):
        publish_message_created_event(message)

    async def send_conversation_history(self):
        messages = await self.get_conversation_messages(self.conversation_id)
        await self.send(text_data=json.dumps({
            'type': 'conversation_history',
            'messages': messages
        }))