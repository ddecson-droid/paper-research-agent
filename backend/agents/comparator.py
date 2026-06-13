"""Agent 3: 论文对比专家——横向比较"""
from ..core import SimpleAgent, HelloAgentsLLM

COMPARATOR_PROMPT = """你是学术评审专家。你的任务是对多篇论文进行横向对比分析。

对比维度：
1. **共同点**: 这些方法的共同假设或技术路线是什么？
2. **差异点**: 核心区别在哪里？（架构、训练方式、数据等）
3. **性能对比**: 哪个方法在哪类任务上更强？
4. **适用场景**: 各自最适合什么场景？
5. **发展趋势**: 从这些论文看，这个方向的技术趋势是什么？

输出格式：
### 横向对比分析
#### 共同点
...

#### 差异对比表
| 维度 | 论文A | 论文B | 论文C |
|------|-------|-------|-------|
| 方法 | ... | ... | ... |
| 数据集 | ... | ... | ... |
| 核心指标 | ... | ... | ... |
| 优势 | ... | ... | ... |
| 不足 | ... | ... | ... |

#### 适用场景建议
...

#### 技术趋势判断
...

请给出具体、有依据的对比分析。"""


class ComparatorAgent:
    def __init__(self):
        self.llm = HelloAgentsLLM()
        self.agent = SimpleAgent(
            name="论文对比专家",
            llm=self.llm,
            system_prompt=COMPARATOR_PROMPT
        )

    def run(self, analyses: str) -> str:
        return self.agent.run(
            f"请对以下论文分析结果进行横向对比：\n\n{analyses}"
        )
