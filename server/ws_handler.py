# server/ws_handler.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import jwt, JWTError
import json
import traceback

from .database import database, users, room_members
from .config import SECRET_KEY, ALGORITHM

router = APIRouter()

# 방별 활성 WebSocket 연결 관리
# { room_id: { username: WebSocket, ... } }
active_connections: dict[int, dict[str, WebSocket]] = {}


async def get_user_from_token(token: str):
    """WebSocket용 JWT 검증"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            print("  → JWT에 'sub' 없음")
            return None
        query = users.select().where(users.c.username == username)
        user = await database.fetch_one(query)
        if user is None:
            print(f"  → DB에서 유저 '{username}' 찾을 수 없음")
        return user
    except JWTError as e:
        print(f"  → JWT 검증 실패: {e}")
        return None
    except Exception as e:
        print(f"  → 토큰 처리 중 오류: {e}")
        traceback.print_exc()
        return None


async def broadcast_to_room(room_id: int, message: dict, exclude_user: str = None):
    """같은 방의 모든 유저에게 메시지 전송 (exclude_user 제외)"""
    if room_id not in active_connections:
        return
    disconnected = []
    for username, ws in list(active_connections[room_id].items()):
        if username != exclude_user:
            try:
                await ws.send_text(json.dumps(message, ensure_ascii=False))
            except Exception:
                disconnected.append(username)
    # 끊어진 연결 정리
    for username in disconnected:
        if username in active_connections.get(room_id, {}):
            del active_connections[room_id][username]


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: int):
    print(f"\n🔌 WebSocket 연결 요청: 방 {room_id}")

    # ★ 핵심: 먼저 accept() 한 뒤에 검증!
    # accept() 전에 close()하면 클라이언트에서 "failed:" 에러 발생
    await websocket.accept()
    print("  → accept() 완료")

    # 1. 쿼리 파라미터에서 토큰 추출
    token = websocket.query_params.get("token")
    if not token:
        print("  → 토큰 없음, 연결 종료")
        await websocket.send_text(json.dumps({"type": "error", "text": "토큰이 필요합니다"}))
        await websocket.close(code=4001)
        return

    # 2. JWT 토큰 검증
    print(f"  → 토큰 검증 중... (앞 20자: {token[:20]}...)")
    user = await get_user_from_token(token)
    if not user:
        print("  → 인증 실패, 연결 종료")
        await websocket.send_text(json.dumps({"type": "error", "text": "인증 실패"}))
        await websocket.close(code=4001)
        return

    username = user.username
    profile_image = f"/uploads/{user.profile_image}" if user.profile_image else None
    print(f"  → ✅ 인증 성공: {username}")

    # 3. 방 연결 목록에 추가 (프로필 정보 포함)
    if room_id not in active_connections:
        active_connections[room_id] = {}
    active_connections[room_id][username] = websocket

    # 유저 프로필 캐시 (방별)
    if not hasattr(websocket_endpoint, '_profiles'):
        websocket_endpoint._profiles = {}
    if room_id not in websocket_endpoint._profiles:
        websocket_endpoint._profiles[room_id] = {}
    websocket_endpoint._profiles[room_id][username] = profile_image

    # 4. 유저 온라인 상태 업데이트
    try:
        query = users.update().where(users.c.id == user.id).values(is_online=True)
        await database.execute(query)
    except Exception as e:
        print(f"  → 온라인 상태 업데이트 실패: {e}")

    # 5. 입장 알림 (다른 유저들에게)
    await broadcast_to_room(room_id, {
        "type": "system",
        "text": f"{username}님이 입장했습니다."
    }, exclude_user=username)

    # 6. 모든 유저에게 최신 접속자 목록 전송 (프로필 이미지 포함)
    profiles = websocket_endpoint._profiles.get(room_id, {})
    online_users = list(active_connections[room_id].keys())
    user_profiles = [{"username": u, "profile_image": profiles.get(u)} for u in online_users]
    print(f"  → 방 {room_id} 접속자: {online_users}")
    await broadcast_to_room(room_id, {
        "type": "user_list",
        "users": online_users,
        "user_profiles": user_profiles
    })

    try:
        # 7. 메시지 수신 루프
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            print(f"  📨 [{username}] {msg.get('type')}: {msg.get('text', '')[:50] if msg.get('text') else ''}")

            if msg.get("type") == "message":
                await broadcast_to_room(room_id, {
                    "type": "message",
                    "username": username,
                    "profile_image": profile_image,
                    "text": msg.get("text", "")
                }, exclude_user=username)

            elif msg.get("type") == "recording":
                await broadcast_to_room(room_id, {
                    "type": "recording",
                    "username": username,
                    "is_recording": msg.get("is_recording", False)
                }, exclude_user=username)

    except WebSocketDisconnect:
        print(f"  🔌 {username} 연결 해제 (정상)")
    except Exception as e:
        print(f"  ❌ {username} 오류: {e}")
        traceback.print_exc()
    finally:
        # 8. 연결 정리
        if room_id in active_connections and username in active_connections[room_id]:
            del active_connections[room_id][username]
            if not active_connections[room_id]:
                del active_connections[room_id]

        # 프로필 캐시 정리
        if hasattr(websocket_endpoint, '_profiles'):
            if room_id in websocket_endpoint._profiles and username in websocket_endpoint._profiles[room_id]:
                del websocket_endpoint._profiles[room_id][username]
                if not websocket_endpoint._profiles[room_id]:
                    del websocket_endpoint._profiles[room_id]

        # 오프라인 상태 업데이트
        try:
            query = users.update().where(users.c.id == user.id).values(is_online=False)
            await database.execute(query)
        except Exception:
            pass

        # 퇴장 알림
        await broadcast_to_room(room_id, {
            "type": "system",
            "text": f"{username}님이 퇴장했습니다."
        })

        # 접속자 목록 업데이트
        if room_id in active_connections:
            profiles = websocket_endpoint._profiles.get(room_id, {}) if hasattr(websocket_endpoint, '_profiles') else {}
            online_users = list(active_connections[room_id].keys())
            user_profiles = [{"username": u, "profile_image": profiles.get(u)} for u in online_users]
            await broadcast_to_room(room_id, {
                "type": "user_list",
                "users": online_users,
                "user_profiles": user_profiles
            })
        else:
            # ★ 방에 아무도 없으면 자동 삭제
            try:
                from .database import rooms, room_members as rm_table
                # room_members 삭제
                query = rm_table.delete().where(rm_table.c.room_id == room_id)
                await database.execute(query)
                # rooms 삭제
                query = rooms.delete().where(rooms.c.id == room_id)
                await database.execute(query)
                print(f"  🗑️ 방 {room_id} 자동 삭제 완료 (모든 유저 퇴장)")
            except Exception as e:
                print(f"  ⚠️ 방 삭제 실패: {e}")

        print(f"  🧹 {username} 정리 완료")

