
# 导入 Pydantic 基类和类型注解
from pydantic import BaseModel, EmailStr  # 用于数据验证和序列化
from typing import Optional, List  # 类型注解
from datetime import datetime  # 时间类型


# 用户基础信息 Schema
class UserBase(BaseModel):
    username: str  # 用户名
    email: EmailStr  # 邮箱


# 用户注册 Schema，包含密码
class UserCreate(UserBase):
    password: str  # 密码


# 用户返回 Schema，包含数据库中的所有字段
class User(UserBase):
    id: int  # 用户ID
    is_active: bool  # 是否激活
    created_at: datetime  # 创建时间
    
    class Config:
        from_attributes = True  # 支持 ORM 模式


# 登录返回的 Token Schema
class Token(BaseModel):
    access_token: str  # 访问令牌
    token_type: str  # 令牌类型


# Token 解析后的数据
class TokenData(BaseModel):
    username: Optional[str] = None  # 用户名


# 消息基础 Schema
class MessageBase(BaseModel):
    content: str  # 消息内容
    role: str  # 消息角色


# 创建消息 Schema
class MessageCreate(MessageBase):
    pass


# 消息返回 Schema，包含数据库中的所有字段
class Message(MessageBase):
    id: int  # 消息ID
    conversation_id: int  # 所属对话ID
    created_at: datetime  # 创建时间
    
    class Config:
        from_attributes = True  # 支持 ORM 模式


# 对话基础 Schema
class ConversationBase(BaseModel):
    title: str  # 对话标题


# 创建对话 Schema
class ConversationCreate(ConversationBase):
    pass


# 对话返回 Schema，包含数据库中的所有字段和消息列表
class Conversation(ConversationBase):
    id: int  # 对话ID
    user_id: int  # 所属用户ID
    created_at: datetime  # 创建时间
    updated_at: Optional[datetime] = None  # 更新时间
    messages: List[Message] = []  # 消息列表
    
    class Config:
        from_attributes = True  # 支持 ORM 模式


# 聊天请求 Schema
class ChatRequest(BaseModel):
    message: str  # 用户消息
    conversation_id: Optional[int] = None  # 对话ID（可选）


# 聊天响应 Schema
class ChatResponse(BaseModel):
    response: str  # AI 回复内容
    conversation_id: int  # 对话ID