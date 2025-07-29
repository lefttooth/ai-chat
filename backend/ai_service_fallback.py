
# 导入所需的库
import requests  # 用于发送 HTTP 请求
import json      # 用于处理 JSON 数据
import time      # 用于延时操作
from typing import List, Dict, Any  # 类型注解
from config import settings  # 导入配置项


# 备用 Ollama 服务类，用于与备用 AI 模型进行交互
class FallbackOllamaService:
    def __init__(self, base_url: str = None, model: str = None):
        """
        初始化 FallbackOllamaService。
        :param base_url: Ollama 服务基础 URL。
        :param model: 使用的模型名称。
        """
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.OLLAMA_MODEL
        self.api_url = f"{self.base_url}/api/generate"  # 生成接口地址
    
    def wait_for_model_ready(self, max_retries: int = 3) -> bool:
        """
        检查备用模型是否准备就绪，最多重试 max_retries 次。
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
                        print(f"✅ 备用模型在第 {attempt + 1} 次尝试后准备就绪")
                        return True
                    else:
                        print(f"⏳ 备用模型正在加载中，等待... (尝试 {attempt + 1}/{max_retries})")
                        time.sleep(5)
                else:
                    print(f"❌ 备用模型测试失败: {response.status_code}")
                    time.sleep(2)
            except Exception as e:
                print(f"❌ 备用模型测试异常: {str(e)}")
                time.sleep(2)
        print("❌ 备用模型在多次尝试后仍未准备就绪")
        return False
    
    def generate_response(self, message: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """
        生成 AI 对话回复。
        :param message: 当前用户消息。
        :param conversation_history: 对话历史（可选）。
        :return: AI 回复文本。
        """
        try:
            if not self.wait_for_model_ready():
                return "抱歉，AI模型正在加载中，请稍后重试。"
            prompt = message
            # 拼接最近 5 条对话历史
            if conversation_history:
                context = ""
                for msg in conversation_history[-5:]:
                    if msg["role"] == "user":
                        context += f"用户: {msg['content']}\n"
                    else:
                        context += f"助手: {msg['content']}\n"
                prompt = context + f"用户: {message}\n助手:"
            print(f"发送prompt: {prompt}")
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
            print(f"响应状态: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                if "response" in result and result["response"]:
                    return result["response"].strip()
                else:
                    print("响应中没有有效内容")
                    if result.get("done_reason") == "load":
                        return "抱歉，AI模型正在加载中，请稍后重试。"
                    else:
                        return "抱歉，AI没有生成有效回复。"
            else:
                print(f"API错误: {response.text}")
                return f"API错误: {response.status_code}"
        except Exception as e:
            print(f"异常: {str(e)}")
            return f"处理错误: {str(e)}"
    
    def test_connection(self) -> bool:
        """
        测试与 Ollama 服务的连接是否正常。
        :return: 连接正常返回 True，否则 False。
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_available_models(self) -> List[str]:
        """
        获取 Ollama 服务可用的模型列表。
        :return: 模型名称列表。
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except:
            return []

# 创建备用服务实例，供外部直接调用
fallback_ai_service = FallbackOllamaService()