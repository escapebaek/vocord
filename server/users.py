# server/users.py

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import or_, and_
import uuid
import os

from .database import database, users, friends
from .models import UserResponse, FriendResponse
from .auth import get_current_user

router = APIRouter(prefix="/api", tags=["users"])

UPLOAD_DIR = "uploads"


# ─────────────────────────────────────
# 프로필 이미지 업로드
# ─────────────────────────────────────
@router.post("/users/profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    # 파일 확장자 검증
    allowed_ext = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail="jpg, png, gif, webp 파일만 업로드 가능합니다.")

    # 파일 크기 제한 (2MB)
    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="파일 크기는 2MB 이하여야 합니다.")

    # 고유 파일명 생성
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # 기존 프로필 이미지 삭제
    if current_user.profile_image:
        old_path = os.path.join(UPLOAD_DIR, current_user.profile_image)
        if os.path.exists(old_path):
            os.remove(old_path)

    # 파일 저장
    with open(filepath, "wb") as f:
        f.write(contents)

    # DB 업데이트
    query = users.update().where(users.c.id == current_user.id).values(profile_image=filename)
    await database.execute(query)

    return {"message": "프로필 이미지가 변경되었습니다.", "profile_image": f"/uploads/{filename}"}


# ─────────────────────────────────────
# 상태 변경 (online / away)
# ─────────────────────────────────────
@router.post("/users/status")
async def update_status(current_user=Depends(get_current_user)):
    # 현재 상태 토글
    current_status = current_user.user_status or "online"
    new_status = "away" if current_status == "online" else "online"

    query = users.update().where(users.c.id == current_user.id).values(user_status=new_status)
    await database.execute(query)

    return {"message": f"상태가 '{new_status}'로 변경되었습니다.", "status": new_status}


# ─────────────────────────────────────
# 내 프로필 정보 (프로필 이미지, 상태 포함)
# ─────────────────────────────────────
@router.get("/users/profile")
async def get_profile(current_user=Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "profile_image": f"/uploads/{current_user.profile_image}" if current_user.profile_image else None,
        "user_status": current_user.user_status or "online",
        "is_online": bool(current_user.is_online)
    }



# ─────────────────────────────────────
# 1. 유저 검색
# ─────────────────────────────────────
@router.get("/users/search")
async def search_users(q: str, current_user=Depends(get_current_user)):
    if not q:
        return []

    # databases 라이브러리의 SQLite 백엔드에서 contains()가
    # % 포맷 문자 충돌을 일으키므로 raw query 사용
    query = "SELECT id, username, is_online FROM users WHERE username LIKE :pattern AND id != :uid"
    results = await database.fetch_all(
        query=query,
        values={"pattern": f"%{q}%", "uid": current_user.id}
    )
    return [
        UserResponse(id=r["id"], username=r["username"], is_online=bool(r["is_online"]))
        for r in results
    ]


# ─────────────────────────────────────
# 2. 접속 중인 유저 목록
# ─────────────────────────────────────
@router.get("/users/online")
async def get_online_users(current_user=Depends(get_current_user)):
    query = (
        users.select()
        .where(users.c.is_online == True)
        .where(users.c.id != current_user.id)
    )
    results = await database.fetch_all(query)
    return [
        UserResponse(id=r.id, username=r.username, is_online=r.is_online)
        for r in results
    ]


# ─────────────────────────────────────
# 3. 친구 요청 보내기
# ─────────────────────────────────────
@router.post("/friends/request/{friend_id}")
async def send_friend_request(friend_id: int, current_user=Depends(get_current_user)):
    # 자기 자신에게 요청 불가
    if friend_id == current_user.id:
        raise HTTPException(status_code=400, detail="자기 자신에게 친구 요청을 보낼 수 없습니다.")

    # 대상 유저 존재 여부 확인
    query = users.select().where(users.c.id == friend_id)
    target_user = await database.fetch_one(query)
    if not target_user:
        raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

    # 중복 요청 체크 (양방향)
    query = friends.select().where(
        or_(
            and_(friends.c.user_id == current_user.id, friends.c.friend_id == friend_id),
            and_(friends.c.user_id == friend_id, friends.c.friend_id == current_user.id),
        )
    )
    existing = await database.fetch_one(query)
    if existing:
        raise HTTPException(status_code=400, detail="이미 친구 요청을 보냈거나 친구입니다.")

    # 친구 요청 INSERT
    query = friends.insert().values(
        user_id=current_user.id,
        friend_id=friend_id,
        status="pending"
    )
    await database.execute(query)
    return {"message": "친구 요청을 보냈습니다."}


# ─────────────────────────────────────
# 4. 친구 요청 수락
# ─────────────────────────────────────
@router.post("/friends/accept/{request_id}")
async def accept_friend_request(request_id: int, current_user=Depends(get_current_user)):
    # 요청 조회
    query = friends.select().where(friends.c.id == request_id)
    request = await database.fetch_one(query)
    if not request:
        raise HTTPException(status_code=404, detail="친구 요청을 찾을 수 없습니다.")

    # 나한테 온 요청인지 확인
    if request.friend_id != current_user.id:
        raise HTTPException(status_code=403, detail="이 요청을 수락할 권한이 없습니다.")

    # status를 accepted로 변경
    query = friends.update().where(friends.c.id == request_id).values(status="accepted")
    await database.execute(query)
    return {"message": "친구 요청을 수락했습니다."}


# ─────────────────────────────────────
# 5. 내 친구 목록 조회
# ─────────────────────────────────────
@router.get("/friends")
async def get_friends(current_user=Depends(get_current_user)):
    query = friends.select().where(
        and_(
            friends.c.status == "accepted",
            or_(
                friends.c.user_id == current_user.id,
                friends.c.friend_id == current_user.id
            )
        )
    )
    results = await database.fetch_all(query)

    friend_list = []
    for r in results:
        # 상대방 ID 찾기
        other_id = r.friend_id if r.user_id == current_user.id else r.user_id
        # 상대방 username 조회
        user_query = users.select().where(users.c.id == other_id)
        other_user = await database.fetch_one(user_query)
        friend_list.append(
            FriendResponse(
                id=r.id,
                user_id=r.user_id,
                friend_id=r.friend_id,
                other_user_id=other_id,
                status=r.status,
                friend_username=other_user.username if other_user else None
            )
        )
    return friend_list


# ─────────────────────────────────────
# 6. 받은 친구 요청 목록
# ─────────────────────────────────────
@router.get("/friends/pending")
async def get_pending_requests(current_user=Depends(get_current_user)):
    query = friends.select().where(
        and_(
            friends.c.friend_id == current_user.id,
            friends.c.status == "pending"
        )
    )
    results = await database.fetch_all(query)

    pending_list = []
    for r in results:
        user_query = users.select().where(users.c.id == r.user_id)
        sender = await database.fetch_one(user_query)
        pending_list.append(
            FriendResponse(
                id=r.id,
                user_id=r.user_id,
                friend_id=r.friend_id,
                status=r.status,
                friend_username=sender.username if sender else None
            )
        )
    return pending_list


# ─────────────────────────────────────
# 7. 친구 삭제
# ─────────────────────────────────────
@router.delete("/friends/{friend_id}")
async def delete_friend(friend_id: int, current_user=Depends(get_current_user)):
    query = friends.select().where(
        and_(
            or_(
                and_(friends.c.user_id == current_user.id, friends.c.friend_id == friend_id),
                and_(friends.c.user_id == friend_id, friends.c.friend_id == current_user.id),
            ),
            friends.c.status == "accepted"
        )
    )
    existing = await database.fetch_one(query)
    if not existing:
        raise HTTPException(status_code=404, detail="친구 관계를 찾을 수 없습니다.")

    query = friends.delete().where(friends.c.id == existing.id)
    await database.execute(query)
    return {"message": "친구를 삭제했습니다."}