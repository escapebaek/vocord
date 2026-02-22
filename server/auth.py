# server/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import bcrypt
from datetime import datetime, timedelta, timezone

from .database import database, users
from .models import UserCreate, UserResponse
from .config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 비밀번호 해싱 도구
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# OAuth2 토큰 추출기 (헤더에서 Bearer 토큰 읽기)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# JWT 토큰 생성 함수
def create_access_token(data: dict) -> str:
    # 1. data 복사
    to_encode = data.copy()

    # 2. 만료시간 추가: {"exp": datetime.utcnow() + timedelta(minutes=...)}
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    # 3. jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM) 반환
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# 회원가입 엔드포인트
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate):
    # 1. DB에서 username 중복 체크
    #    query = users.select().where(users.c.username == user.username)
    #    existing = await database.fetch_one(query)
    query = users.select().where(users.c.username == user.username)
    existing_user = await database.fetch_one(query)

    # 2. 중복이면 HTTPException(400) 발생
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="이미 존재하는 사용자입니다."
        )

    # 3. 비밀번호 해싱
    hashed_password = hash_password(user.password)

    # 4. DB에 INSERT
    #    query = users.insert().values(username=..., password_hash=...)
    #    await database.execute(query)
    query = users.insert().values(
        username=user.username,
        password_hash=hashed_password
    )
    await database.execute(query)
    
    # 5. 성공 메시지 반환
    return {"message": "회원가입 성공"}


# 로그인 엔드포인트
@router.post("/login")
async def login(user: UserCreate):
    # 1. DB에서 유저 조회
    query = users.select().where(users.c.username == user.username)
    db_user = await database.fetch_one(query)
    
    # 2. 없으면 HTTPException(401)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 3. 비밀번호 검증
    if not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 4. 틀리면 HTTPException(401)
    
    # 5. JWT 토큰 생성: create_access_token({"sub": username})
    access_token = create_access_token({"sub": db_user.username})
    # 6. {"access_token": token, "token_type": "bearer"} 반환
    return {"access_token": access_token, "token_type": "bearer"}


# 현재 로그인된 유저 가져오기 (다른 API에서 Depends()로 사용)
async def get_current_user(token: str = Depends(oauth2_scheme)):
    # 4. 실패 시 HTTPException(401)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보를 확인할 수 없습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
    # 1. jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    # 2. payload에서 username 추출: payload.get("sub")
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # 3. DB에서 유저 조회 후 반환
    query = users.select().where(users.c.username == username)
    user = await database.fetch_one(query)
    if not user:
        raise credentials_exception
    return user


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "is_online": current_user.is_online
    }


from pydantic import BaseModel

class PasswordChange(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(data: PasswordChange, current_user=Depends(get_current_user)):
    # 현재 비밀번호 확인
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=400,
            detail="현재 비밀번호가 올바르지 않습니다."
        )

    # 새 비밀번호 길이 검증
    if len(data.new_password) < 4:
        raise HTTPException(
            status_code=400,
            detail="새 비밀번호는 4자 이상이어야 합니다."
        )

    # 새 비밀번호 해싱 후 업데이트
    new_hash = hash_password(data.new_password)
    query = users.update().where(users.c.id == current_user.id).values(password_hash=new_hash)
    await database.execute(query)

    return {"message": "비밀번호가 변경되었습니다."}