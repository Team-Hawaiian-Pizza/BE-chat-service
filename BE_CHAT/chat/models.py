from django.db import models
from django.utils import timezone
import uuid


class Conversation(models.Model):
    """
    1대1 대화방 모델
    두 사용자 간의 채팅방을 나타내는 모델
    MSA 아키텍처를 고려하여 core-service의 user_id를 직접 참조하지 않고 문자열로 저장
    하지만 실제로는 core ERD의 user 테이블과 연결되어야 함
    """
    
    # UUID를 Primary Key로 사용하는게 분산 환경에서는 좋겠지만 
    # 혹시 나중에 정수형으로 바꿔야 할 수도 있어서 일단 UUID로...
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # core service의 user 테이블과 연결되는 부분
    # 외래키로 하고 싶지만 MSA에서는 string이 맞는듯
    # 나중에 API 호출로 사용자 정보 가져와야 함
    participant1_id = models.CharField(max_length=255, db_index=True)
    
    # 두 번째 참여자도 동일하게 처리
    # core ERD 보니까 user 테이블에 friendship도 있던데
    # 친구 관계 확인도 나중에 해야할듯
    participant2_id = models.CharField(max_length=255, db_index=True)
    
    # 언제 대화방이 생성됐는지 추적용
    # 나중에 통계 뽑을 때도 필요할거 같음
    created_at = models.DateTimeField(default=timezone.now)
    
    # 마지막 메시지 시간 추적하려고 넣었는데
    # 메시지가 올 때마다 업데이트 되겠네
    updated_at = models.DateTimeField(auto_now=True)
    
    # 대화방 비활성화 기능
    # 사용자가 대화방 나가기 하면 False로 바꿀 예정
    is_active = models.BooleanField(default=True)
    
    # core ERD의 brand와 연결할 수도 있을듯
    # 브랜드 관련 대화방인 경우 brand_id 저장
    # 일단 null=True로 해두고 나중에 필요하면 사용
    brand_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    
    # 대화방 유형을 구분하기 위해 추가
    # 일반 유저 간 대화인지, 브랜드 상담인지 구분용
    conversation_type = models.CharField(
        max_length=20, 
        choices=[
            ('user_to_user', '일반 사용자 간 대화'),
            ('user_to_brand', '사용자-브랜드 상담'),
            ('group', '그룹 채팅'),  # 나중에 확장 가능성
        ],
        default='user_to_user'
    )

    class Meta:
        # 실제 데이터베이스 테이블명 지정
        db_table = 'conversations'
        
        # 같은 두 사용자 간에는 하나의 대화방만 존재하도록 제약 조건 설정
        # 근데 participant1과 2가 바뀌면 다른 걸로 인식할 수도 있어서 
        # 뷰에서 조회할 때 OR 조건으로 찾아야겠음
        unique_together = ['participant1_id', 'participant2_id']
        
        # 인덱스 최적화
        # 사용자별 대화방 목록 조회가 많이 일어날 것 같아서
        # 각각 인덱스 걸어둠
        indexes = [
            # 참여자 조합 검색용 (대화방 중복 체크)
            models.Index(fields=['participant1_id', 'participant2_id']),
            # 최근 업데이트 순 정렬용 (대화방 목록)
            models.Index(fields=['updated_at']),
            # 대화방 유형별 검색용
            models.Index(fields=['conversation_type', 'is_active']),
            # 브랜드 관련 대화방 검색용
            models.Index(fields=['brand_id', 'is_active']),
            # 사용자별 활성 대화방 목록 (성능 중요)
            models.Index(fields=['participant1_id', 'is_active', 'updated_at']),
            models.Index(fields=['participant2_id', 'is_active', 'updated_at']),
        ]

    def __str__(self):
        """관리자 페이지나 디버깅 시 표시될 문자열"""
        return f"Conversation {self.id}: {self.participant1_id} - {self.participant2_id}"


class Message(models.Model):
    """
    메시지 모델
    대화방 내에서 주고받는 개별 메시지를 저장
    텍스트, 이미지, 파일 등 다양한 타입의 메시지 지원
    core ERD의 user와 연동 고려해야 함
    """
    
    # 메시지 타입들
    # 나중에 스티커, 위치 공유 등도 추가할 수 있을듯
    MESSAGE_TYPES = [
        ('text', 'Text'),      
        ('image', 'Image'),    
        ('file', 'File'),
        ('sticker', 'Sticker'),  # 나중에 확장
        ('location', 'Location'),  # 위치 공유
        ('brand_card', 'Brand Card'),  # 브랜드 카드 (core ERD의 brand 연동)
    ]

    # UUID 쓰는게 나은가 고민됨
    # 메시지는 엄청 많이 생길텐데 성능상 어떨까
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 대화방 참조
    # CASCADE로 해도 되나? 혹시 나중에 대화방 삭제해도 메시지는 남겨둬야 할 수도...
    # 일단 CASCADE로 하고 나중에 필요하면 PROTECT로 변경
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    
    # 발송자 ID - core service의 user와 연결
    # API 호출로 사용자 정보 가져와야 함
    sender_id = models.CharField(max_length=255, db_index=True)
    
    # 메시지 내용
    # 이미지나 파일은 URL로 저장할 예정
    # S3나 CDN 경로가 들어갈듯
    content = models.TextField()
    
    # 메시지 타입
    message_type = models.CharField(max_length=15, choices=MESSAGE_TYPES, default='text')
    
    # 메시지 생성 시각
    # 페이지네이션에서 중요한 필드
    created_at = models.DateTimeField(default=timezone.now)
    
    # 메시지 수정 기능용
    # 나중에 메시지 편집 기능 추가하면 사용
    updated_at = models.DateTimeField(auto_now=True)
    
    # 소프트 삭제
    # 메시지 삭제해도 DB에는 남겨둠
    is_deleted = models.BooleanField(default=False)
    
    # 답장 기능을 위한 필드
    # 특정 메시지에 대한 답장인지 추적
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')
    
    # 브랜드 관련 메시지인 경우
    # core ERD의 brand와 연결될 수 있음
    brand_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    
    # 메시지 순서 보장을 위한 필드
    # 동시에 여러 메시지가 오면 created_at만으로는 순서 보장이 안될 수 있어서
    sequence_number = models.BigIntegerField(null=True, blank=True, db_index=True)

    class Meta:
        # 실제 데이터베이스 테이블명
        db_table = 'messages'
        
        # 인덱스 설정
        # 페이지네이션 때문에 인덱스가 정말 중요함
        indexes = [
            # 페이지네이션용 - 가장 중요한 인덱스
            # 대화방별로 시간 역순으로 조회하는 경우가 많음
            models.Index(fields=['conversation', 'is_deleted', '-created_at']),
            # 발송자별 메시지 조회용
            models.Index(fields=['sender_id', 'created_at']),
            # 메시지 타입별 검색용 (이미지만 보기 등)
            models.Index(fields=['conversation', 'message_type', 'is_deleted']),
            # 답장 관련 조회용
            models.Index(fields=['reply_to']),
            # 브랜드 관련 메시지 조회용
            models.Index(fields=['brand_id', 'created_at']),
            # 순서 보장용 인덱스
            models.Index(fields=['conversation', 'sequence_number']),
            # 전체 메시지 시간순 조회 (관리자용)
            models.Index(fields=['created_at']),
        ]
        
        # 정렬 기본값
        # 최신 메시지가 먼저 오도록
        ordering = ['-created_at']

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
