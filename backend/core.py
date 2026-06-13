"""
自包含的 LLM + Agent 核心模块
替代 hello-agents 外部依赖，提供 HelloAgentsLLM + SimpleAgent
"""
import os
import re
from typing import Optional, Iterator
from datetime import datetime
from abc import ABC, abstractmethod

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from pydantic import BaseModel


# ============================================================
#  异常类
# ============================================================

class HelloAgentsException(Exception):
    """基础异常"""


# ============================================================
#  消息类
# ============================================================

class Message(BaseModel):
    """对话消息"""
    content: str
    role: str  # "user" | "assistant" | "system"
    timestamp: datetime = None

    def __init__(self, content: str, role: str, **kwargs):
        super().__init__(
            content=content,
            role=role,
            timestamp=kwargs.get("timestamp", datetime.now()),
        )

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


# ============================================================
#  LLM 客户端
# ============================================================

class HelloAgentsLLM:
    """
    兼容 OpenAI 接口的 LLM 客户端。
    优先使用传入参数，环境变量兜底。

    用法:
        llm = HelloAgentsLLM()                          # 从环境变量读取
        llm = HelloAgentsLLM(model="deepseek-chat",
                             api_key="sk-xxx",
                             base_url="https://api.deepseek.com")
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: int = 120,
        **kwargs,
    ):
        self.model = model or os.getenv("LLM_MODEL_ID", "deepseek-chat")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        if not self.api_key:
            raise HelloAgentsException(
                "API Key 未配置。请在 .env 中设置 LLM_API_KEY"
            )

        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def invoke(self, messages: list[dict], **kwargs) -> str:
        """非流式调用 LLM，返回完整响应文本"""
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                stream=False,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            raise HelloAgentsException(f"LLM 调用失败: {e}")

    def think(self, messages: list[dict], temperature: Optional[float] = None) -> Iterator[str]:
        """流式调用 LLM，逐 token 返回"""
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )
            for chunk in resp:
                content = chunk.choices[0].delta.content or ""
                if content:
                    yield content
        except Exception as e:
            raise HelloAgentsException(f"LLM 流式调用失败: {e}")

    def stream_invoke(self, messages: list[dict], **kwargs) -> Iterator[str]:
        """流式调用的别名"""
        yield from self.think(messages, kwargs.get("temperature"))


# ============================================================
#  Agent 基类
# ============================================================

class Agent(ABC):
    """Agent 抽象基类"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
    ):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self._history: list[Message] = []

    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str:
        """运行 Agent"""
        ...

    def add_message(self, message: Message):
        self._history.append(message)

    def clear_history(self):
        self._history.clear()

    def get_history(self) -> list[Message]:
        return self._history.copy()


# ============================================================
#  简单 Agent（项目中实际使用的类型）
# ============================================================

class SimpleAgent(Agent):
    """
    简单对话 Agent —— 系统提示词 + 用户输入 → LLM → 响应。

    用法:
        llm = HelloAgentsLLM()
        agent = SimpleAgent(
            name="分析专家",
            llm=llm,
            system_prompt="你是一个学术分析专家..."
        )
        result = agent.run("请分析这篇论文...")
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
    ):
        super().__init__(name, llm, system_prompt)

    def run(self, input_text: str, **kwargs) -> str:
        """运行 Agent —— 构建消息 → 调用 LLM → 返回响应"""
        messages: list[dict] = []

        # 系统提示词
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        # 历史消息
        for msg in self._history:
            messages.append(msg.to_dict())

        # 当前用户输入
        messages.append({"role": "user", "content": input_text})

        # 调用 LLM
        response = self.llm.invoke(messages, **kwargs)

        # 记录历史
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(response, "assistant"))

        return response

    def stream_run(self, input_text: str, **kwargs) -> Iterator[str]:
        """流式运行"""
        messages: list[dict] = []

        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        for msg in self._history:
            messages.append(msg.to_dict())

        messages.append({"role": "user", "content": input_text})

        full = ""
        for chunk in self.llm.stream_invoke(messages, **kwargs):
            full += chunk
            yield chunk

        self.add_message(Message(input_text, "user"))
        self.add_message(Message(full, "assistant"))
