### 📋 개요

WaytoWay의 실시간 채팅 서비스를 위한 RESTful API 및 WebSocket 명세서입니다.

### 프로젝트 정보

- **서비스명**: WaytoWay-BE-Chat
- **아키텍처**: MSA (Microservice Architecture) 고려해서 만듬 !
- **Base URL**: `http://localhost:8000`
- **WebSocket URL**: `ws://localhost:8000`

---

## 🛠️ 기술 스택

### Backend Framework

- **Django 5.2.5**: Python 웹 프레임워크
- **Django REST Framework 3.15.2**: RESTful API 구현
- **Django Channels 4.1.0**: WebSocket 실시간 통신

### Database & Cache

- **MySQL 8.0**: 메인 데이터베이스
- **Redis 7**: 캐시 및 WebSocket 채널 레이어
- **SQLite3**: 개발 환경용 대체 데이터베이스

### Infrastructure

- **Docker & Docker Compose**: 컨테이너화 및 오케스트레이션
- **Gunicorn**: WSGI 서버
- **Daphne**: ASGI 서버 (WebSocket 지원)

