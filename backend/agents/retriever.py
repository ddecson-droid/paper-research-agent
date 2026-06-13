"""Agent 1: 文献检索专家——整理多源检索结果并评估质量"""
from ..core import SimpleAgent, HelloAgentsLLM
from ..config import config

RETRIEVER_PROMPT = """你是学术文献检索专家。你的任务是根据用户的研究方向，评估并整理多源检索结果。

工作流程：
1. 分析用户输入的研究方向，提取核心关键词
2. 根据论文元数据（引用量、发表venue、年份），评估每篇论文的权威性和质量
3. 标注质量等级：
   - ⭐⭐⭐ 顶会/顶刊论文，高引用量（>100），有影响力
   - ⭐⭐ 质量较好的论文，有一定引用
   - ⭐ 预印本或引用很少的新论文
4. 列出检索到的论文标题、作者、年份、引用量、venue和摘要
5. 标注每篇与研究方向的相关度：高/中/低

输出格式：
### 检索策略
- 关键词: ...
- 搜索角度: ...

### 质量评估总结
- 高影响力论文（⭐⭐⭐）: N篇
- 中等质量论文（⭐⭐）: N篇
- 待验证论文（⭐）: N篇

### 检索结果
**论文1: [标题]**
- 作者: ...
- 年份: ...
- 引用量: ... (高影响力引用: ...)
- 发表venue: ...
- 摘要: ... (前200字)
- 相关度: 高/中/低
- 质量等级: ⭐⭐⭐ / ⭐⭐ / ⭐

请确保质量评估客观，基于实际的引用量和venue信息。"""


class RetrieverAgent:
    def __init__(self):
        self.llm = HelloAgentsLLM()
        self.agent = SimpleAgent(
            name="文献检索专家",
            llm=self.llm,
            system_prompt=RETRIEVER_PROMPT
        )

    def run(self, topic: str, search_results: list[dict] = None) -> str:
        """检索并整理论文（含质量评估）"""
        if search_results:
            papers_text = "\n\n".join([
                f"[{i+1}] {p.get('title','')}\n"
                f"作者: {', '.join(p.get('authors',[])[:5])}\n"
                f"年份: {p.get('year','')}\n"
                f"引用量: {p.get('citation_count', 'N/A')}"
                + (f"（高影响力引用: {p.get('influential_citation_count')}）" if p.get('influential_citation_count') else "")
                + f"\n发表venue: {p.get('venue', '') or p.get('journal', 'N/A')}\n"
                f"来源: {p.get('source', 'unknown')}\n"
                f"综合评分: {p.get('score', 0):.2f}\n"
                f"摘要: {p.get('summary','')[:300]}"
                for i, p in enumerate(search_results)
            ])
            prompt = (
                f"研究方向: {topic}\n\n"
                f"以下是多源检索到的论文（含质量信号：引用量、venue、综合评分），"
                f"请整理、评估质量等级并标注相关性：\n\n{papers_text}"
            )
        else:
            prompt = (
                f"研究方向: {topic}\n\n"
                f"请根据你的知识推荐该领域的经典和最新论文。"
            )
        return self.agent.run(prompt)
