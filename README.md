# VOCORD 🎙️

> 실시간 음성→텍스트 변환 채팅 앱 (Discord 스타일)

## 소개

VOCORD는 **Push-to-Talk(PTT)** 방식으로 음성을 녹음하고, **Gemini API**를 활용해 실시간으로 텍스트로 변환하여 채팅방에 표시하는 웹 애플리케이션입니다.

## 주요 기능

- 🎙️ **PTT 음성 채팅** — 지정 키를 누르는 동안 녹음, 놓으면 자동 STT 변환
- ⌨️ **PTT 키 커스터마이징** — 원하는 키로 변경 가능
- 👥 **친구 시스템** — 친구 추가, 수락, 원클릭 초대
- 💬 **1:1 / 그룹 채팅방** — 실시간 WebSocket 통신
- 🖼️ **프로필 이미지** — 말풍선 옆에 표시
- 🟡 **자리 비움 상태** — 마이페이지에서 토글
- 🗑️ **방 자동 삭제** — 마지막 유저 퇴장 시 자동 정리

## 기술 스택

| 영역 | 기술 |
|------|------|
| Backend | FastAPI, SQLAlchemy, SQLite, WebSocket |
| Frontend | Vanilla JS, HTML, CSS |
| 인증 | JWT (python-jose) |
| STT | Google Gemini API |

## 실행 방법

```bash
# 1. 가상환경 생성 & 활성화
python -m venv venv
venv\Scripts\activate  # Windows

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 환경변수 설정 (.env 파일 생성)
echo SECRET_KEY=your-secret-key > .env

# 4. 서버 실행
uvicorn server.main:app --reload --port 8000
```

## 환경변수

`.env` 파일을 생성하세요:

```
SECRET_KEY=your-secret-key-here
```

Gemini API Key는 웹 UI에서 직접 입력합니다.
