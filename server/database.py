"""
server/database.py

로컬: SQLite (기본값)
배포 환경(Railway 등): DATABASE_URL 환경변수 → Supabase PostgreSQL
"""
import os
import sqlalchemy
from sqlalchemy import Table, Column, Integer, String, Boolean, DateTime, ForeignKey, func
import databases

# ─── DB URL 결정 ─────────────────────────────────────────────────────────────
_raw_url = os.getenv("DATABASE_URL", "sqlite:///./vocord.db")

# Heroku/Railway가 "postgres://" 형태로 줄 수 있어서 변환
if _raw_url.startswith("postgres://"):
    _raw_url = _raw_url.replace("postgres://", "postgresql://", 1)

IS_POSTGRES = _raw_url.startswith("postgresql")

# databases 라이브러리는 async 드라이버를 써야 함
if IS_POSTGRES:
    # postgresql://... → postgresql+asyncpg://...
    if "postgresql+asyncpg" not in _raw_url:
        _async_url = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        _async_url = _raw_url
else:
    _async_url = _raw_url   # sqlite:///...

DATABASE_URL = _async_url

# ─── databases (비동기 쿼리) ──────────────────────────────────────────────────
database = databases.Database(DATABASE_URL)

# ─── SQLAlchemy metadata (테이블 스키마 정의) ────────────────────────────────
metadata = sqlalchemy.MetaData()

users = Table(
    "users", metadata,
    Column("id",            Integer,     primary_key=True),
    Column("username",      String(50),  unique=True, index=True),
    Column("password_hash", String(255)),
    Column("is_online",     Boolean,     default=False),
    Column("profile_image", String(500), nullable=True),
    Column("user_status",   String(20),  default="online"),
    Column("created_at",    DateTime,    default=func.now()),
)

friends = Table(
    "friends", metadata,
    Column("id",        Integer, primary_key=True),
    Column("user_id",   Integer, ForeignKey("users.id")),
    Column("friend_id", Integer, ForeignKey("users.id")),
    Column("status",    String(20), default="pending"),
)

rooms = Table(
    "rooms", metadata,
    Column("id",         Integer, primary_key=True),
    Column("name",       String(100)),
    Column("created_by", Integer, ForeignKey("users.id")),
    Column("created_at", DateTime, default=func.now()),
)

room_members = Table(
    "room_members", metadata,
    Column("id",      Integer, primary_key=True),
    Column("room_id", Integer, ForeignKey("rooms.id")),
    Column("user_id", Integer, ForeignKey("users.id")),
)

# ─── DDL 실행 (테이블 생성) ───────────────────────────────────────────────────
if IS_POSTGRES:
    # sync psycopg2로 DDL 실행 (Supabase는 이미 테이블이 있으므로 IF NOT EXISTS 무시됨)
    _sync_url = _raw_url  # postgresql://... (asyncpg 아닌 원본)
    engine = sqlalchemy.create_engine(_sync_url)
else:
    engine = sqlalchemy.create_engine(_raw_url)

metadata.create_all(engine)

# ─── SQLite 전용 마이그레이션 ──────────────────────────────────────────────────
if not IS_POSTGRES:
    import sqlite3

    def _migrate():
        conn = sqlite3.connect("vocord.db")
        cur = conn.cursor()
        for ddl in [
            "ALTER TABLE users ADD COLUMN profile_image TEXT",
            "ALTER TABLE users ADD COLUMN user_status TEXT DEFAULT 'online'",
        ]:
            try:
                cur.execute(ddl)
            except sqlite3.OperationalError:
                pass
        conn.commit()
        conn.close()

    _migrate()