import json
import logging
from datetime import datetime
from django.conf import settings

# 로거 인스턴스 생성 (이벤트 발행 로깅용)
logger = logging.getLogger(__name__)


def publish_message_created_event(message):
    """
    message.created 이벤트를 발행 - MSA 이벤트 드리븐 아키텍처의 핵심
    다른 서비스들(ai-service 등)이 이 이벤트를 구독하여 후속 처리 수행
    """
    # MSA 표준 이벤트 스키마 구조
    event_data = {
        'event_type': 'message.created',  # 이벤트 타입
        'timestamp': datetime.now().isoformat(),  # 발생 시각
        'data': {
            # 메시지 관련 정보들
            'message_id': str(message.id),  # UUID를 문자열로 변환
            'conversation_id': str(message.conversation.id),
            'sender_id': message.sender_id,
            'content': message.content,
            'message_type': message.message_type,
            'created_at': message.created_at.isoformat(),
        }
    }
    
    # 현재는 로깅으로 구현 (실제 환경에서는 메시지 브로커 사용)
    logger.info(f"Publishing event: {json.dumps(event_data, indent=2)}")
    
    # TODO: 프로덕션 환경에서 구현해야 할 것들
    # - RabbitMQ 또는 Apache Kafka를 통한 이벤트 발행
    # - 이벤트 발행 실패 시 재시도 로직
    # - 이벤트 스키마 검증 및 버전 관리
    # - 이벤트 순서 보장 및 중복 처리
    
    return event_data


def publish_conversation_created_event(conversation):
    """
    conversation.created 이벤트 발행 - 새 대화방 생성 시 발생
    알림 서비스나 통계 서비스에서 활용 가능
    """
    event_data = {
        'event_type': 'conversation.created',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'conversation_id': str(conversation.id),
            'participant1_id': conversation.participant1_id,
            'participant2_id': conversation.participant2_id,
            'created_at': conversation.created_at.isoformat(),
        }
    }
    
    logger.info(f"Publishing event: {json.dumps(event_data, indent=2)}")
    return event_data