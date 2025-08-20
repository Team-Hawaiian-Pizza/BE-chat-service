from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
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


class MessagePaginatedSerializer(serializers.ModelSerializer):
    """페이지네이션용 메시지 직렬화 클래스 - 읽음 상태 포함"""
    
    delivery_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ['id', 'sender_id', 'content', 'message_type', 'created_at', 'updated_at', 'delivery_status']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_delivery_status(self, obj):
        """메시지별 읽음 상태 정보 반환"""
        receipts = obj.delivery_receipts.all()
        return [
            {
                'user_id': receipt.user_id,
                'status': receipt.status,
                'timestamp': receipt.timestamp
            }
            for receipt in receipts
        ]


class ConversationDetailSerializer(serializers.ModelSerializer):
    """대화방 상세 정보 직렬화 클래스 - 메시지는 별도 API로 분리"""
    
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ['id', 'participant1_id', 'participant2_id', 'created_at', 'updated_at', 'is_active', 'last_message', 'unread_count']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_last_message(self, obj):
        """대화방의 마지막 메시지를 반환"""
        last_message = obj.messages.filter(is_deleted=False).order_by('-created_at').first()
        if last_message:
            return MessagePaginatedSerializer(last_message).data
        return None
    
    def get_unread_count(self, obj):
        """읽지 않은 메시지 수 반환 (요청 user 기준)"""
        request = self.context.get('request')
        if request and hasattr(request, 'user_id'):
            user_id = getattr(request, 'user_id')
            return obj.messages.filter(
                is_deleted=False,
                delivery_receipts__user_id=user_id,
                delivery_receipts__status__in=['sent', 'delivered']
            ).count()
        return 0


class MessagePagination(PageNumberPagination):
    """메시지 페이지네이션 클래스"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100