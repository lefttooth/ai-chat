
# 导入 FastAPI 及相关依赖
from fastapi import FastAPI, Depends, HTTPException, status  # FastAPI 主体和依赖注入
from fastapi.security import OAuth2PasswordRequestForm  # OAuth2 表单
from fastapi.middleware.cors import CORSMiddleware  # 跨域中间件
from sqlalchemy.orm import Session  # 数据库会话
from datetime import timedelta  # 时间处理
from typing import List  # 类型注解

# 导入本地模块
from database import engine, get_db  # 数据库引擎和依赖
from models import Base, User, Conversation, Message  # ORM 模型
from schemas import UserCreate, User as UserSchema, Token, Conversation as ConversationSchema, Message as MessageSchema, ChatRequest, ChatResponse  # 数据结构
from auth import authenticate_user, create_access_token, get_current_user, get_password_hash  # 认证相关
from config import settings  # 配置

# 导入本地和联网 AI 服务
from ai_service import ai_service


# 创建数据库表（如未存在）
Base.metadata.create_all(bind=engine)

# 创建 FastAPI 应用实例
app = FastAPI(title="AI Chat API", version="1.0.0")

# 配置 CORS，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vue 开发服务器地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 用户注册接口
@app.post("/register", response_model=UserSchema)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # 检查用户名是否已注册
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    # 检查邮箱是否已注册
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    # 加密密码并保存新用户
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# 用户登录接口，返回 JWT Token
@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# 获取当前登录用户信息
@app.get("/users/me", response_model=UserSchema)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


# 创建新对话
@app.post("/conversations", response_model=ConversationSchema)
def create_conversation(
    conversation: ConversationSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_conversation = Conversation(
        title=conversation.title,
        user_id=current_user.id
    )
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    return db_conversation


# 获取当前用户的所有对话
@app.get("/conversations", response_model=List[ConversationSchema])
def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversations = db.query(Conversation).filter(Conversation.user_id == current_user.id).all()
    return conversations


# 获取指定对话详情
@app.get("/conversations/{conversation_id}", response_model=ConversationSchema)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


# 删除指定对话及其消息
@app.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    # 级联删除消息
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    db.delete(conversation)
    db.commit()
    return None


# 聊天接口，支持多轮对话
from fastapi import Request



# 聊天接口，支持多轮对话和联网切换
from fastapi import Request

@app.post("/chat", response_model=ChatResponse)
def chat(
    chat_request: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 如果没有指定对话ID，创建新对话
    if not chat_request.conversation_id:
        conversation = Conversation(
            title=chat_request.message[:50] + "..." if len(chat_request.message) > 50 else chat_request.message,
            user_id=current_user.id
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        conversation_id = conversation.id
    else:
        conversation_id = chat_request.conversation_id
        # 验证对话是否属于当前用户
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    # 获取对话历史
    conversation_history = []
    if conversation_id:
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).all()
        for msg in messages:
            conversation_history.append({
                "role": msg.role,
                "content": msg.content
            })
    # 保存用户消息
    user_message = Message(
        content=chat_request.message,
        role="user",
        conversation_id=conversation_id
    )
    db.add(user_message)

    # 只用本地模型
    ai_response = ai_service.generate_response(
        chat_request.message,
        conversation_history
    )

    # 保存 AI 消息
    ai_message = Message(
        content=ai_response,
        role="assistant",
        conversation_id=conversation_id
    )
    db.add(ai_message)
    db.commit()
    return ChatResponse(response=ai_response, conversation_id=conversation_id)


# 获取 AI 服务状态
@app.get("/ai/status")
def get_ai_status():
    """获取AI服务状态"""
    is_connected = ai_service.test_connection()
    available_models = ai_service.get_available_models() if is_connected else []
    return {
        "connected": is_connected,
        "available_models": available_models,
        "current_model": ai_service.model
    }


# 根路由，健康检查
@app.get("/")
def read_root():
    return {"message": "AI Chat API is running"}