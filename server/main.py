# server/main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from .database import database
from .auth import router as auth_router
from .users import router as users_router
from .rooms import router as rooms_router
from .ws_handler import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 DB 연결 관리"""
    await database.connect()
    print("✅ DB 연결 완료")
    yield
    await database.disconnect()
    print("🔌 DB 연결 해제")


app = FastAPI(title="VOCORD", version="1.0.0", lifespan=lifespan)

# 라우터 등록
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(rooms_router)
app.include_router(ws_router)

# 정적 파일 서빙 (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 업로드 파일 서빙 (프로필 이미지 등)
import os
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# 메인 페이지
@app.get("/")
async def root():
    return FileResponse("static/index.html")
