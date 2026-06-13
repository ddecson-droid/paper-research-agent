"""Agent 4: 综述撰写专家——生成结构化文献综述"""
from ..core import SimpleAgent, HelloAgentsLLM

WRITER_PROMPT = """你是学术综述撰写专家。你的任务是根据论文分析和对比结果，撰写一份结构化的文献综述。

综述结构：
1. **研究背景与问题** (200-300字): 该领域的研究意义和核心挑战
2. **方法分类与梳理** (500-800字): 将现有方法按技术路线分类，介绍每类的核心思想
3. **代表性工作详述** (每篇100-200字): 介绍每篇论文的核心贡献
4. **方法对比与讨论** (300-500字): 各方法的优劣和适用场景
5. **未来方向与结论** (200-300字): 该领域的发展趋势和开放问题

输出格式：
# 文献综述：[研究方向]
## 1. 研究背景与问题
...
## 2. 方法分类与梳理
...
## 3. 代表性工作详述
...
## 4. 方法对比与讨论
...
## 5. 未来方向与结论
...
## 参考文献
[1] ...
[2] ...

请保持学术规范，使用客观、专业的语言。"""


class WriterAgent:
    def __init__(self):
        self.llm = HelloAgentsLLM()
        self.agent = SimpleAgent(
            name="综述撰写专家",
            llm=self.llm,
            system_prompt=WRITER_PROMPT
        )

    def run(self, topic: str, analyses: str, comparison: str) -> str:
        prompt = (
            f"研究方向: {topic}\n\n"
            f"## 各论文分析结果\n{analyses}\n\n"
            f"## 横向对比结果\n{comparison}\n\n"
            f"请基于以上信息撰写一份完整的文献综述。"
        )
        return self.agent.run(prompt)
