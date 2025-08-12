from rest_framework import serializers
from .models import Conversation, Message, DeliveryReceipt


class MessageSerializer(serializers.ModelSerializer):
    """메시지 직렬화 클래스 - JSON과 모델 간 변환"""
    
    class Meta:
        model = Message
        # API 응답에 포함될 필드들
        fields = ['id', 'sender_id', 'content', 'message_type', 'created_at', 'updated_at', 'is_deleted']
        # 읽기 전용 필드들 (API 요청시 수정 불가)
        read_only_fields = ['id', 'created_at', 'updated_at']


class ConversationSerializer(serializers.ModelSerializer):
    """대화방 직렬화 클래스 - 메시지 목록과 마지막 메시지 정보 포함"""
    
    # 대화방에 속한 모든 메시지들을 중첩된 형태로 포함
    messages = MessageSerializer(many=True, read_only=True)
    
    # 대화방의 마지막 메시지 정보 (커스텀 필드)
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ['id', 'participant1_id', 'participant2_id', 'created_at', 'updated_at', 'is_active', 'messages', 'last_message']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_last_message(self, obj):
        """대화방의 마지막 메시지를 반환하는 메서드"""
        # 삭제되지 않은 메시지 중 가장 최근 메시지 조회
        last_message = obj.messages.filter(is_deleted=False).order_by('-created_at').first()
        if last_message:
            return MessageSerializer(last_message).data
        return None


class DeliveryReceiptSerializer(serializers.ModelSerializer):
    """메시지 읽음 확인 직렬화 클래스"""
    
    class Meta:
        model = DeliveryReceipt
        fields = ['id', 'message', 'user_id', 'status', 'timestamp']
        read_only_fields = ['id', 'timestamp']