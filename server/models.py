from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# [요청용 모델]
# UserCreate: username(str), password(str)
# RoomCreate: name(str)

class UserCreate(BaseModel):
    username: str
    password: str

class RoomCreate(BaseModel):
    name: str

# [응답용 모델]  
# UserResponse: id(int), username(str), is_online(bool)
# RoomResponse: id(int), name(str), created_by(int), created_at(datetime)
# FriendResponse: id(int), user_id(int), friend_id(int), status(str), friend_username(Optional[str])

class UserResponse(BaseModel):
    id: int
    username: str
    is_online: bool = False

class RoomResponse(BaseModel):
    id: int
    name: str
    created_by: int
    created_at: datetime

class FriendResponse(BaseModel):
    id: int
    user_id: int
    friend_id: int
    other_user_id: int = 0  # 실제 상대방 유저 ID
    status: str
    friend_username: Optional[str] = None