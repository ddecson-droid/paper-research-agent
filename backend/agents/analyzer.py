"""Agent 2: 论文分析专家——逐篇深度分析"""
from ..core import SimpleAgent, HelloAgentsLLM

ANALYZER_PROMPT = """你是学术论文分析专家。你的任务是对每篇论文进行结构化深度分析。

对每篇论文提取以下信息：
1. **研究问题**: 论文要解决什么核心问题？
2. **方法**: 使用了什么方法/模型/架构？
3. **数据集**: 在什么数据集上评估？数据集规模？
4. **关键指标**: 核心性能指标及数值（准确率、F1、BLEU等）
5. **创新点**: 相比前人工作的主要创新在哪？
6. **局限性**: 论文自己承认的局限或你判断的不足

输出格式（每篇论文）：
### 论文分析： [标题]
| 维度 | 内容 |
|------|------|
| 研究问题 | ... |
| 方法 | ... |
| 数据集 | ... |
| 指标 | ... |
| 创新点 | ... |
| 局限性 | ... |

请保持分析客观、准确，尽量提取具体数字。"""


class AnalyzerAgent:
    def __init__(self):
        self.llm = HelloAgentsLLM()
        self.agent = SimpleAgent(
            name="论文分析专家",
            llm=self.llm,
            system_prompt=ANALYZER_PROMPT
        )

    def run(self, paper_text: str) -> str:
        return self.agent.run(
            f"请对以下论文进行结构化分析：\n\n{paper_text}"
        )
