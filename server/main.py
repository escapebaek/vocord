# server/main.py

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from .database import database
from .auth import router as auth_router
from .users import router as users_router
from .rooms import router as rooms_router
from .ws_handler import router as ws_router

# ── 경로: 이 파일(server/main.py)의 상위 폴더 = 프로젝트 루트 ──────────────
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 DB 연결 관리"""
    try:
        await database.connect()
        print("✅ DB 연결 완료")
    except Exception as e:
        print(f"⚠️  DB 연결 실패: {e}")
        print("   → DATABASE_URL 환경변수를 확인하세요")
        # 연결 실패해도 앱은 실행 (API 호출 시 에러 발생)
    yield
    try:
        await database.disconnect()
        print("🔌 DB 연결 해제")
    except Exception:
        pass



app = FastAPI(title="VOCORD", version="1.0.0", lifespan=lifespan)

# 라우터 등록
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(rooms_router)
app.include_router(ws_router)

# 정적 파일 서빙 (CSS, JS)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# 업로드 파일 서빙 (로컬 fallback)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# 메인 페이지
@app.get("/")
async def root():
    return FileResponse(str(STATIC_DIR / "index.html"))


# ─── 헬스체크 (UptimeRobot 등 외부 모니터용) ────────────────────────────────
@app.get("/ping")
@app.head("/ping")
async def ping():
    return {"status": "ok", "service": "VOCORD"}
