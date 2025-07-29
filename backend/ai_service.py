from math_mcp import mcp_math_request

"""
AI 本地与联网辅助服务
"""
# 导入所需的库
def need_internet_query(message: str) -> bool:
    """
    判断用户输入是否需要联网（如包含日期、星期、天气、新闻等关键词）。
    """
    keywords = [
        '今天', '日期', '星期', '几号', '现在时间', '天气', '新闻', '查一下', '搜索', '百度', '谷歌', 'google', 'bing', 'stock', '股价', '汇率', '实时', '热搜', '头条'
    ]
    return any(k in message for k in keywords)
import requests  # 用于发送 HTTP 请求
import json      # 用于处理 JSON 数据
import time      # 用于延时操作
import re        # 用于正则表达式处理
from typing import List, Dict, Any  # 类型注解
from config import settings  # 导入配置项

class OllamaService:
    """
    OllamaService 用于与 Ollama AI 模型服务进行交互，生成对话回复。
    """
    def __init__(self, base_url: str = None, model: str = None):
        """
        初始化 OllamaService。
        :param base_url: Ollama 服务的基础 URL。
        :param model: 使用的模型名称。
        """
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.OLLAMA_MODEL
        self.api_url = f"{self.base_url}/api/generate"  # 生成接口地址

    def wait_for_model_ready(self, max_retries: int = 3) -> bool:
        """
        检查模型是否准备就绪，最多重试 max_retries 次。
        :param max_retries: 最大重试次数。
        :return: 模型可用返回 True，否则 False。
        """
        for attempt in range(max_retries):
            try:
                payload = {
                    "model": self.model,
                    "prompt": "你好",  # 用于测试模型是否可用
                    "stream": False
                }
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                if response.status_code == 200:
                    result = response.json()
                    # 如果 done_reason 不是 load，说明模型已加载完成
                    if result.get("done_reason") != "load":
                        return True
                    else:
                        time.sleep(5)
                else:
                    time.sleep(2)
            except Exception as e:
                # 只保留错误日志
                print(f"❌ 模型测试异常: {str(e)}")
                time.sleep(2)
        return False

    def strip_think_tags(self, text: str) -> str:
        """
        移除 <think> 标签及其内容。
        :param text: 原始文本。
        :return: 处理后的文本。
        """
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    def generate_response(self, message: str, conversation_history: List[Dict[str, str]] = None) -> str:
        # 1. 优先MCP数学计算
        mcp_result = mcp_math_request(message)
        if mcp_result["status"] == "success":
            return f"答案：{mcp_result['result']}"
        elif mcp_result["status"] == "error":
            return f"数学计算出错：{mcp_result['reason']}"
        # 2. 其他情况（not_applicable）继续走大模型
        """
        生成 AI 对话回复。
        :param message: 当前用户消息。
        :param conversation_history: 对话历史（可选）。
        :return: AI 回复文本。
        """
        try:
            if not self.wait_for_model_ready():
                return "抱歉，AI模型正在加载中，请稍后重试。"
            prompt = ""
            # 拼接最近 5 条对话历史
            if conversation_history:
                for msg in conversation_history[-5:]:
                    if msg["role"] == "user":
                        prompt += f"用户: {msg['content']}\n"
                    else:
                        prompt += f"助手: {msg['content']}\n"
            prompt += f"用户: {message}\n助手:"
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            response = requests.post(
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            if response.status_code == 200:
                result = response.json()
                if "response" in result and result["response"]:
                    reply = result["response"].strip()
                    reply = self.strip_think_tags(reply)
                    return reply if reply else "抱歉，AI没有生成有效回复。"
                elif result.get("done_reason") == "load":
                    return "抱歉，AI模型正在加载中，请稍后重试。"
                else:
                    return "抱歉，AI没有生成有效回复。"
            else:
                print(f"Ollama API错误: {response.status_code} - {response.text}")
                return f"抱歉，AI服务暂时不可用。错误代码: {response.status_code}"
        except requests.exceptions.ConnectionError:
            print("连接错误: 无法连接到Ollama服务")
            return "无法连接到Ollama服务，请确保Ollama正在运行。"
        except requests.exceptions.Timeout:
            print("请求超时")
            return "请求超时，请稍后重试。"
        except Exception as e:
            print(f"调用Ollama API时发生错误: {str(e)}")
            return "抱歉，处理您的请求时发生错误。"

    def test_connection(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

    def get_available_models(self) -> List[str]:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except:
            return []

ai_service = OllamaService() 