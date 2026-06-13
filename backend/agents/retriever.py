"""Agent 1: 文献检索专家——搜索 arxiv 论文"""
from ..core import SimpleAgent, HelloAgentsLLM
from ..config import config

RETRIEVER_PROMPT = """你是学术文献检索专家。你的任务是根据用户的研究方向，构造精准的搜索查询，
并整理搜索结果。

工作流程：
1. 分析用户输入的研究方向，提取核心关键词
2. 构造 2-3 个不同角度的搜索查询（中英文结合）
3. 对搜索结果进行初步筛选，删除明显不相关的
4. 列出检索到的论文标题、作者、年份和摘要

输出格式：
### 检索策略
- 关键词: ...
- 搜索角度: ...

### 检索结果
**论文1: [标题]**
- 作者: ...
- 年份: ...
- 摘要: ...
- 相关度: 高/中/低

请确保每篇论文的信息完整、准确。"""


class RetrieverAgent:
    def __init__(self):
        self.llm = HelloAgentsLLM()
        self.agent = SimpleAgent(
            name="文献检索专家",
            llm=self.llm,
            system_prompt=RETRIEVER_PROMPT
        )

    def run(self, topic: str, search_results: list[dict] = None) -> str:
        """检索并整理论文"""
        if search_results:
            papers_text = "\n\n".join([
                f"[{i+1}] {p.get('title','')}\n"
                f"作者: {', '.join(p.get('authors',[])[:3])}\n"
                f"年份: {p.get('year','')}\n"
                f"摘要: {p.get('summary','')[:300]}"
                for i, p in enumerate(search_results)
            ])
            prompt = (
                f"研究方向: {topic}\n\n"
                f"以下是检索到的论文，请整理并标注相关度：\n\n{papers_text}"
            )
        else:
            prompt = (
                f"研究方向: {topic}\n\n"
                f"请根据你的知识推荐该领域的经典和最新论文。"
            )
        return self.agent.run(prompt)
