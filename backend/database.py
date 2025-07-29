
# 导入 SQLAlchemy 相关模块和配置
from sqlalchemy import create_engine  # 创建数据库引擎
from sqlalchemy.ext.declarative import declarative_base  # 声明基类
from sqlalchemy.orm import sessionmaker  # 会话工厂
from config import settings  # 导入配置项

# 创建数据库引擎，连接到指定数据库
engine = create_engine(settings.DATABASE_URL)
# 创建数据库会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 所有 ORM 模型的基类
Base = declarative_base()

# 获取数据库会话的依赖，用于 FastAPI 路由
def get_db():
    db = SessionLocal()
    try:
        yield db  # 提供数据库会话
    finally:
        db.close()  # 用完后关闭