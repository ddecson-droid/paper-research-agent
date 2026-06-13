"""多Agent研究流水线——串联4个Agent"""
import time
from typing import Iterator
from .retriever import RetrieverAgent
from .analyzer import AnalyzerAgent
from .comparator import ComparatorAgent
from .writer import WriterAgent
from ..tools.arxiv_tool import search_arxiv


class ResearchPipeline:
    """4 Agent 研究流水线"""

    def __init__(self):
        self.retriever = RetrieverAgent()
        self.analyzer = AnalyzerAgent()
        self.comparator = ComparatorAgent()
        self.writer = WriterAgent()

    def run(self, topic: str, stream: bool = False) -> dict:
        """执行完整研究流水线，返回结构化结果"""
        result = {
            "topic": topic,
            "papers": [],
            "analysis": "",
            "comparison": "",
            "report": "",
            "agent_times": {},
        }
        t0 = time.time()

        # Step 1: 检索论文
        t1 = time.time()
        papers = search_arxiv(topic, max_results=8)
        result["papers"] = papers
        retrieval_text = self.retriever.run(topic, papers)
        result["agent_times"]["retriever"] = time.time() - t1

        # Step 2: 逐篇分析
        t2 = time.time()
        analyses = []
        for i, paper in enumerate(papers[:5]):  # 最多分析5篇
            paper_text = (
                f"标题: {paper.get('title','')}\n"
                f"作者: {', '.join(paper.get('authors',[])[:3])}\n"
                f"年份: {paper.get('year','')}\n"
                f"摘要: {paper.get('summary','')}"
            )
            analysis = self.analyzer.run(paper_text)
            analyses.append(f"--- 论文 {i+1} ---\n{analysis}")
        result["analysis"] = "\n\n".join(analyses)
        result["agent_times"]["analyzer"] = time.time() - t2

        # Step 3: 对比
        t3 = time.time()
        result["comparison"] = self.comparator.run(result["analysis"])
        result["agent_times"]["comparator"] = time.time() - t3

        # Step 4: 撰写
        t4 = time.time()
        result["report"] = self.writer.run(
            topic, result["analysis"], result["comparison"]
        )
        result["agent_times"]["writer"] = time.time() - t4

        result["total_time"] = time.time() - t0
        return result

    def run_single_agent(self, topic: str) -> dict:
        """单Agent模式（用于对比评估）"""
        from ..core import SimpleAgent, HelloAgentsLLM
        t0 = time.time()

        llm = HelloAgentsLLM()
        agent = SimpleAgent(
            name="全能研究助手",
            llm=llm,
            system_prompt="你是一个学术研究助手，负责搜索论文、分析内容并生成综述。"
        )
        report = agent.run(
            f"请就'{topic}'这个研究方向，搜索相关论文，"
            f"分析各方法，生成一份文献综述。"
            f"请包含：背景、方法分类、代表性工作、对比讨论和未来方向。"
        )

        return {"report": report, "total_time": time.time() - t0}
