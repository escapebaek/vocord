import sqlalchemy
from sqlalchemy import Table, Column, Integer, String, Boolean, DateTime, ForeignKey, func
import databases

# 1. DATABASE_URL 정의: "sqlite:///./vocord.db"
DATABASE_URL = "sqlite:///./vocord.db"

# 2. databases.Database(DATABASE_URL) 객체 생성
database = databases.Database(DATABASE_URL)

# 3. sqlalchemy.MetaData() 생성
metadata = sqlalchemy.MetaData()

# 4. 테이블 4개 정의 (sqlalchemy.Table 사용):

# [users 테이블] - 회원 정보
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String(50), unique=True, index=True),
    Column("password_hash", String(255)),
    Column("is_online", Boolean, default=False),
    Column("profile_image", String(255), nullable=True),   # 프로필 이미지 파일명
    Column("user_status", String(20), default="online"),    # online / away
    Column("created_at", DateTime, default=func.now())
)

# [friends 테이블] - 친구 관계
friends = Table(
    "friends",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("friend_id", Integer, ForeignKey("users.id")),
    Column("status", String(20), default="pending")
)

# [rooms 테이블] - 채팅방/게임방 등 방 정보
rooms = Table(
    "rooms",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100)),
    Column("created_by", Integer, ForeignKey("users.id")),
    Column("created_at", DateTime, default=func.now())
)

# [room_members 테이블] - 방에 들어간 멤버 목록
room_members = Table(
    "room_members",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("room_id", Integer, ForeignKey("rooms.id")),
    Column("user_id", Integer, ForeignKey("users.id"))
)

# 5. engine 생성 + 테이블 실제 생성
engine = sqlalchemy.create_engine(DATABASE_URL)
metadata.create_all(engine)

# 6. 기존 DB에 새 컬럼이 없으면 추가 (마이그레이션)
import sqlite3

def migrate_db():
    conn = sqlite3.connect("vocord.db")
    cursor = conn.cursor()
    # 이미 있는 컬럼이면 무시
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN profile_image TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN user_status TEXT DEFAULT 'online'")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

migrate_db()