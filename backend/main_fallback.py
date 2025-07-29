from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List

from database import engine, get_db
from models import Base, User, Conversation, Message
from schemas import UserCreate, User as UserSchema, Token, Conversation as ConversationSchema, Message as MessageSchema, ChatRequest, ChatResponse
from auth import authenticate_user, create_access_token, get_current_user, get_password_hash
from config import settings
from ai_service_fallback import fallback_ai_service  # 使用备用服务

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Chat API (Fallback)", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/register", response_model=UserSchema)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

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

@app.get("/users/me", response_model=UserSchema)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

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

@app.get("/conversations", response_model=List[ConversationSchema])
def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversations = db.query(Conversation).filter(Conversation.user_id == current_user.id).all()
    return conversations

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

@app.post("/chat", response_model=ChatResponse)
def chat(
    chat_request: ChatRequest,
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
    
    # 调用备用AI服务生成回复
    ai_response = fallback_ai_service.generate_response(
        chat_request.message, 
        conversation_history
    )
    
    # 保存AI消息
    ai_message = Message(
        content=ai_response,
        role="assistant",
        conversation_id=conversation_id
    )
    db.add(ai_message)
    
    db.commit()
    
    return ChatResponse(response=ai_response, conversation_id=conversation_id)

@app.get("/ai/status")
def get_ai_status():
    """获取AI服务状态"""
    is_connected = fallback_ai_service.test_connection()
    available_models = fallback_ai_service.get_available_models() if is_connected else []
    
    return {
        "connected": is_connected,
        "available_models": available_models,
        "current_model": fallback_ai_service.model
    }

@app.get("/")
def read_root():
    return {"message": "AI Chat API (Fallback) is running"} 