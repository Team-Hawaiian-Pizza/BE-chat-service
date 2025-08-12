from django.db import models
from django.utils import timezone
import uuid


class Conversation(models.Model):
    """
    1대1 대화방 모델
    두 사용자 간의 채팅방을 나타내는 모델
    MSA 아키텍처를 고려하여 core-service의 user_id를 직접 참조하지 않고 문자열로 저장
    """
    
    # UUID를 Primary Key로 사용 (분산 환경에서 ID 충돌 방지)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 대화 참여자 1의 ID (core-service의 user_id를 문자열로 참조)
    # db_index=True로 검색 성능 최적화
    # MSA 원칙에 따라 Foreign Key 대신 문자열로 저장
    participant1_id = models.CharField(max_length=255, db_index=True)
    
    # 대화 참여자 2의 ID (core-service의 user_id를 문자열로 참조)
    participant2_id = models.CharField(max_length=255, db_index=True)
    
    # 대화방 생성 시각 (자동으로 현재 시간 설정)
    created_at = models.DateTimeField(default=timezone.now)
    
    # 대화방 정보 수정 시각 (수정될 때마다 자동 업데이트)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 대화방 활성화 상태 (비활성화된 대화방은 숨김 처리)
    is_active = models.BooleanField(default=True)

    class Meta:
        # 실제 데이터베이스 테이블명 지정
        db_table = 'conversations'
        
        # 같은 두 사용자 간에는 하나의 대화방만 존재하도록 제약 조건 설정
        # (participant1_id, participant2_id) 조합이 유니크해야 함
        unique_together = ['participant1_id', 'participant2_id']
        
        # 데이터베이스 인덱스 설정 (검색 성능 최적화)
        indexes = [
            # 참여자 조합으로 검색할 때 사용되는 복합 인덱스
            models.Index(fields=['participant1_id', 'participant2_id']),
            # 최근 대화방 순으로 정렬할 때 사용되는 인덱스
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        """관리자 페이지나 디버깅 시 표시될 문자열"""
        return f"Conversation {self.id}: {self.participant1_id} - {self.participant2_id}"


class Message(models.Model):
    """
    메시지 모델
    대화방 내에서 주고받는 개별 메시지를 저장
    텍스트, 이미지, 파일 등 다양한 타입의 메시지 지원
    """
    
    # 메시지 타입 선택지 정의
    MESSAGE_TYPES = [
        ('text', 'Text'),      # 일반 텍스트 메시지
        ('image', 'Image'),    # 이미지 메시지
        ('file', 'File'),      # 파일 메시지
    ]

    # UUID를 Primary Key로 사용
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 메시지가 속한 대화방 (Foreign Key 관계)
    # on_delete=CASCADE: 대화방이 삭제되면 관련 메시지도 모두 삭제
    # related_name='messages': Conversation 객체에서 conversation.messages로 역참조 가능
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    
    # 메시지 발송자 ID (core-service의 user_id를 문자열로 참조)
    # MSA 원칙에 따라 Foreign Key 대신 문자열로 저장
    sender_id = models.CharField(max_length=255, db_index=True)
    
    # 메시지 내용 (텍스트의 경우 실제 내용, 파일의 경우 파일 경로나 URL)
    content = models.TextField()
    
    # 메시지 타입 (text, image, file 중 하나)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    
    # 메시지 생성 시각
    created_at = models.DateTimeField(default=timezone.now)
    
    # 메시지 수정 시각 (수정될 때마다 자동 업데이트)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 소프트 삭제 플래그 (실제로 삭제하지 않고 숨김 처리)
    # True이면 삭제된 메시지로 처리하여 UI에서 숨김
    is_deleted = models.BooleanField(default=False)

    class Meta:
        # 실제 데이터베이스 테이블명
        db_table = 'messages'
        
        # 데이터베이스 인덱스 설정
        indexes = [
            # 특정 대화방의 메시지들을 시간순으로 조회할 때 사용
            models.Index(fields=['conversation', 'created_at']),
            # 특정 사용자가 보낸 메시지들을 조회할 때 사용
            models.Index(fields=['sender_id']),
        ]

    def __str__(self):
        """관리자 페이지나 디버깅 시 표시될 문자열"""
        return f"Message {self.id} from {self.sender_id}"


class DeliveryReceipt(models.Model):
    """
    메시지 전달 및 읽음 확인 모델
    각 메시지에 대해 사용자별로 전달 상태를 추적
    카카오톡의 읽음 표시와 유사한 기능 제공
    """
    
    # 메시지 전달 상태 선택지
    DELIVERY_STATUS = [
        ('sent', 'Sent'),           # 전송됨 (서버에서 처리됨)
        ('delivered', 'Delivered'), # 전달됨 (상대방 기기에 도착)
        ('read', 'Read'),          # 읽음 (상대방이 메시지를 읽음)
    ]

    # UUID를 Primary Key로 사용
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 전달 상태를 추적할 메시지 (Foreign Key 관계)
    # on_delete=CASCADE: 메시지가 삭제되면 관련 전달 기록도 모두 삭제
    # related_name='delivery_receipts': Message 객체에서 message.delivery_receipts로 역참조
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='delivery_receipts')
    
    # 메시지를 받을 사용자 ID (core-service의 user_id를 문자열로 참조)
    # 메시지 발송자가 아닌 수신자의 ID를 저장
    user_id = models.CharField(max_length=255, db_index=True)
    
    # 현재 전달 상태 (sent, delivered, read 중 하나)
    status = models.CharField(max_length=10, choices=DELIVERY_STATUS, default='sent')
    
    # 해당 상태가 된 시각 (상태 변경 시마다 업데이트)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        # 실제 데이터베이스 테이블명
        db_table = 'delivery_receipts'
        
        # 하나의 메시지에 대해 각 사용자마다 하나의 전달 기록만 존재
        # (message, user_id) 조합이 유니크해야 함
        unique_together = ['message', 'user_id']
        
        # 데이터베이스 인덱스 설정
        indexes = [
            # 특정 메시지의 모든 전달 상태를 조회할 때 사용
            models.Index(fields=['message', 'user_id']),
            # 특정 사용자의 읽음 상태들을 조회할 때 사용
            models.Index(fields=['user_id', 'status']),
        ]

    def __str__(self):
        """관리자 페이지나 디버깅 시 표시될 문자열"""
        return f"Receipt {self.id}: {self.message_id} - {self.user_id} ({self.status})"
