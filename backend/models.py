
# 导入 SQLAlchemy 所需的模块和基类
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean  # 字段类型和外键
from sqlalchemy.orm import relationship  # 关系映射
from sqlalchemy.sql import func  # SQL 函数
from database import Base  # 数据库基类


class User(Base):
    """
    用户表模型，存储注册用户的基本信息。
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)  # 用户ID，主键
    username = Column(String(50), unique=True, index=True)  # 用户名，唯一
    email = Column(String(100), unique=True, index=True)  # 邮箱，唯一
    hashed_password = Column(String(255))  # 加密后的密码
    is_active = Column(Boolean, default=True)  # 是否激活
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间
    
    # 与 Conversation 的一对多关系
    conversations = relationship("Conversation", back_populates="user")


class Conversation(Base):
    """
    对话表模型，存储每个用户的对话。
    """
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)  # 对话ID，主键
    title = Column(String(200))  # 对话标题
    user_id = Column(Integer, ForeignKey("users.id"))  # 所属用户ID，外键
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # 更新时间
    
    # 与 User 的多对一关系
    user = relationship("User", back_populates="conversations")
    # 与 Message 的一对多关系
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    """
    消息表模型，存储每条对话消息。
    """
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)  # 消息ID，主键
    content = Column(Text)  # 消息内容
    role = Column(String(20))  # 消息角色，'user' 或 'assistant'
    conversation_id = Column(Integer, ForeignKey("conversations.id"))  # 所属对话ID，外键
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间
    
    # 与 Conversation 的多对一关系
    conversation = relationship("Conversation", back_populates="messages")