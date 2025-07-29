
# 导入依赖库和类型注解
from datetime import datetime, timedelta  # 时间相关
from typing import Optional  # 可选类型
from jose import JWTError, jwt  # JWT 编解码
from passlib.context import CryptContext  # 密码加密
from fastapi import Depends, HTTPException, status  # FastAPI 依赖和异常
from fastapi.security import OAuth2PasswordBearer  # OAuth2 认证
from sqlalchemy.orm import Session  # 数据库会话
from database import get_db  # 获取数据库会话
from models import User  # 用户模型
from schemas import TokenData  # Token 数据结构
from config import settings  # 配置项


# 密码加密上下文，使用 bcrypt 算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# OAuth2 认证方案，token 获取接口为 /token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# 校验明文密码和加密密码是否一致
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# 获取密码的加密哈希值
def get_password_hash(password):
    return pwd_context.hash(password)


# 创建 JWT 访问令牌
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()  # 复制数据
    if expires_delta:
        expire = datetime.utcnow() + expires_delta  # 自定义过期时间
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)  # 默认15分钟
    to_encode.update({"exp": expire})  # 添加过期时间
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)  # 加密生成 token
    return encoded_jwt


# 根据用户名获取用户对象
def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


# 校验用户名和密码，认证用户
def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


# 获取当前登录用户，依赖于 token 验证
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 解码 JWT，获取用户名
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user