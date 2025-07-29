
# 导入操作系统环境变量和 dotenv 加载工具
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 配置类，集中管理所有后端配置项
class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL")

# 实例化配置对象，供全局导入使用
settings = Settings()