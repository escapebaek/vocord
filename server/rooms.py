# server/rooms.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_

from .database import database, rooms, room_members, users
from .models import RoomCreate, RoomResponse
from .auth import get_current_user

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


# ─────────────────────────────────────
# 1. 방 생성
# ─────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_room(room: RoomCreate, current_user=Depends(get_current_user)):
    # 방 이름 중복 체크
    query = rooms.select().where(rooms.c.name == room.name)
    existing = await database.fetch_one(query)
    if existing:
        raise HTTPException(status_code=400, detail="이미 존재하는 방 이름입니다.")

    # 방 생성
    query = rooms.insert().values(
        name=room.name,
        created_by=current_user.id
    )
    room_id = await database.execute(query)

    # 생성자를 자동으로 방에 입장
    query = room_members.insert().values(
        room_id=room_id,
        user_id=current_user.id
    )
    await database.execute(query)

    return {"message": "방이 생성되었습니다.", "room_id": room_id}


# ─────────────────────────────────────
# 2. 방 목록 조회
# ─────────────────────────────────────
@router.get("")
async def get_rooms(current_user=Depends(get_current_user)):
    query = rooms.select()
    results = await database.fetch_all(query)

    room_list = []
    for r in results:
        # 방 멤버 수 조회
        count_query = room_members.select().where(room_members.c.room_id == r.id)
        members = await database.fetch_all(count_query)
        room_list.append({
            "id": r.id,
            "name": r.name,
            "created_by": r.created_by,
            "created_at": str(r.created_at) if r.created_at else None,
            "member_count": len(members)
        })
    return room_list


# ─────────────────────────────────────
# 3. 방 입장
# ─────────────────────────────────────
@router.post("/{room_id}/join")
async def join_room(room_id: int, current_user=Depends(get_current_user)):
    # 방 존재 확인
    query = rooms.select().where(rooms.c.id == room_id)
    room = await database.fetch_one(query)
    if not room:
        raise HTTPException(status_code=404, detail="방을 찾을 수 없습니다.")

    # 이미 참가 중인지 확인
    query = room_members.select().where(
        and_(
            room_members.c.room_id == room_id,
            room_members.c.user_id == current_user.id
        )
    )
    existing = await database.fetch_one(query)
    if existing:
        raise HTTPException(status_code=400, detail="이미 참가 중인 방입니다.")

    # 입장
    query = room_members.insert().values(
        room_id=room_id,
        user_id=current_user.id
    )
    await database.execute(query)
    return {"message": "방에 입장했습니다."}


# ─────────────────────────────────────
# 4. 방 퇴장
# ─────────────────────────────────────
@router.post("/{room_id}/leave")
async def leave_room(room_id: int, current_user=Depends(get_current_user)):
    query = room_members.select().where(
        and_(
            room_members.c.room_id == room_id,
            room_members.c.user_id == current_user.id
        )
    )
    existing = await database.fetch_one(query)
    if not existing:
        raise HTTPException(status_code=400, detail="이 방에 참가하고 있지 않습니다.")

    query = room_members.delete().where(
        and_(
            room_members.c.room_id == room_id,
            room_members.c.user_id == current_user.id
        )
    )
    await database.execute(query)
    return {"message": "방에서 퇴장했습니다."}


# ─────────────────────────────────────
# 5. 방 멤버 조회
# ─────────────────────────────────────
@router.get("/{room_id}/members")
async def get_room_members(room_id: int, current_user=Depends(get_current_user)):
    query = room_members.select().where(room_members.c.room_id == room_id)
    members = await database.fetch_all(query)

    member_list = []
    for m in members:
        user_query = users.select().where(users.c.id == m.user_id)
        user = await database.fetch_one(user_query)
        if user:
            member_list.append({
                "id": user.id,
                "username": user.username,
                "is_online": bool(user.is_online)
            })
    return member_list


# ─────────────────────────────────────
# 6. 초대 시스템 (in-memory)
# ─────────────────────────────────────
import time

# { invite_id: { from_user, from_username, to_user, to_username, room_id, room_name, timestamp } }
pending_invitations: dict[int, dict] = {}
invite_counter = 0


@router.post("/invite/{friend_id}")
async def invite_friend(friend_id: int, current_user=Depends(get_current_user)):
    global invite_counter

    # 자기 자신 초대 불가
    if friend_id == current_user.id:
        raise HTTPException(status_code=400, detail="자기 자신을 초대할 수 없습니다.")

    # 상대 유저 확인
    query = users.select().where(users.c.id == friend_id)
    friend = await database.fetch_one(query)
    if not friend:
        raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

    # 1:1 방 생성 (방 이름: "유저1 & 유저2")
    room_name = f"{current_user.username} & {friend.username}"

    # 이미 같은 이름의 방이 있으면 재사용
    query = rooms.select().where(rooms.c.name == room_name)
    existing_room = await database.fetch_one(query)

    if existing_room:
        room_id = existing_room.id
    else:
        # 역순 이름도 체크
        room_name_rev = f"{friend.username} & {current_user.username}"
        query = rooms.select().where(rooms.c.name == room_name_rev)
        existing_room_rev = await database.fetch_one(query)

        if existing_room_rev:
            room_id = existing_room_rev.id
            room_name = room_name_rev
        else:
            # 새 방 생성
            query = rooms.insert().values(name=room_name, created_by=current_user.id)
            room_id = await database.execute(query)

    # 생성자를 방에 추가 (이미 있으면 무시)
    query = room_members.select().where(
        and_(room_members.c.room_id == room_id, room_members.c.user_id == current_user.id)
    )
    if not await database.fetch_one(query):
        query = room_members.insert().values(room_id=room_id, user_id=current_user.id)
        await database.execute(query)

    # 이미 같은 유저에게 보낸 대기 중 초대가 있으면 중복 방지
    for inv_id, inv in pending_invitations.items():
        if inv["from_user"] == current_user.id and inv["to_user"] == friend_id:
            return {
                "message": "이미 초대를 보냈습니다.",
                "room_id": room_id,
                "room_name": room_name
            }

    # 초대 생성
    invite_counter += 1
    pending_invitations[invite_counter] = {
        "from_user": current_user.id,
        "from_username": current_user.username,
        "to_user": friend_id,
        "to_username": friend.username,
        "room_id": room_id,
        "room_name": room_name,
        "timestamp": time.time()
    }

    return {
        "message": f"{friend.username}님에게 초대를 보냈습니다.",
        "room_id": room_id,
        "room_name": room_name,
        "invite_id": invite_counter
    }


@router.get("/invitations")
async def get_invitations(current_user=Depends(get_current_user)):
    """내게 온 대기 중인 초대 목록"""
    my_invites = []
    now = time.time()
    expired = []

    for inv_id, inv in pending_invitations.items():
        # 5분 지난 초대는 만료
        if now - inv["timestamp"] > 300:
            expired.append(inv_id)
            continue
        if inv["to_user"] == current_user.id:
            my_invites.append({
                "id": inv_id,
                "from_username": inv["from_username"],
                "room_id": inv["room_id"],
                "room_name": inv["room_name"]
            })

    # 만료 초대 정리
    for inv_id in expired:
        del pending_invitations[inv_id]

    return my_invites


@router.post("/invitations/{invite_id}/accept")
async def accept_invitation(invite_id: int, current_user=Depends(get_current_user)):
    invite = pending_invitations.get(invite_id)
    if not invite:
        raise HTTPException(status_code=404, detail="초대를 찾을 수 없습니다.")
    if invite["to_user"] != current_user.id:
        raise HTTPException(status_code=403, detail="이 초대의 대상이 아닙니다.")

    room_id = invite["room_id"]

    # 방에 입장
    query = room_members.select().where(
        and_(room_members.c.room_id == room_id, room_members.c.user_id == current_user.id)
    )
    if not await database.fetch_one(query):
        query = room_members.insert().values(room_id=room_id, user_id=current_user.id)
        await database.execute(query)

    # 초대 삭제
    del pending_invitations[invite_id]

    return {
        "message": "초대를 수락했습니다.",
        "room_id": room_id,
        "room_name": invite["room_name"]
    }


@router.post("/invitations/{invite_id}/decline")
async def decline_invitation(invite_id: int, current_user=Depends(get_current_user)):
    invite = pending_invitations.get(invite_id)
    if not invite:
        raise HTTPException(status_code=404, detail="초대를 찾을 수 없습니다.")
    if invite["to_user"] != current_user.id:
        raise HTTPException(status_code=403, detail="이 초대의 대상이 아닙니다.")

    del pending_invitations[invite_id]
    return {"message": "초대를 거절했습니다."}

