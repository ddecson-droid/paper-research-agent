"""评估模块——对比单Agent vs 多Agent的研究质量"""
import time
from typing import Optional
from ..agents.pipeline import ResearchPipeline


def evaluate_with_llm(text: str, criteria: str) -> int:
    """用LLM对输出打分（1-5）"""
    from ..core import SimpleAgent, HelloAgentsLLM

    llm = HelloAgentsLLM()
    judge = SimpleAgent(
        name="评估裁判",
        llm=llm,
        system_prompt=f"""你是学术质量评审专家。请对文本按以下标准评分(1-5分):\n{criteria}\n\n只输出数字分数，不要其他内容。"""
    )
    try:
        score_text = judge.run(f"请评分:\n{text[:2000]}")
        # 提取数字
        import re
        nums = re.findall(r'[1-5]', score_text)
        return int(nums[0]) if nums else 3
    except:
        return 3


def run_evaluation(topic: str) -> dict:
    """
    对比评估：单Agent vs 多Agent

    Returns:
        {
            "topic": str,
            "single_agent": {"report": str, "time": float, "scores": dict},
            "multi_agent": {"report": str, "time": float, "scores": dict, "agent_times": dict},
            "improvement": dict
        }
    """
    print(f"\n{'='*60}")
    print(f"  Agent 评估对比实验")
    print(f"  研究方向: {topic}")
    print(f"{'='*60}")

    pipeline = ResearchPipeline()

    # 单Agent模式
    print("\n[1/2] 运行单Agent模式...")
    t0 = time.time()
    single_result = pipeline.run_single_agent(topic)
    single_time = time.time() - t0

    # 多Agent模式
    print("\n[2/2] 运行多Agent模式...")
    multi_result = pipeline.run(topic)
    multi_time = multi_result["total_time"]

    # LLM打分
    criteria = """
1. 文献覆盖率: 是否覆盖了该领域的主要工作？
2. 分析深度: 对每篇论文的分析是否深入具体？
3. 结构化程度: 报告结构是否清晰、逻辑是否连贯？
4. 对比质量: 方法间的对比是否有价值？
5. 实用性: 对研究者是否有参考价值？"""

    print("\n[评估] LLM 打分中...")
    single_scores = {
        "文献覆盖率": evaluate_with_llm(single_result.get("report", ""), criteria),
        "分析深度": evaluate_with_llm(single_result.get("report", ""), criteria),
        "结构化程度": evaluate_with_llm(single_result.get("report", ""), criteria),
        "对比质量": evaluate_with_llm(single_result.get("report", ""), criteria),
        "实用性": evaluate_with_llm(single_result.get("report", ""), criteria),
    }

    multi_scores = {
        "文献覆盖率": evaluate_with_llm(multi_result.get("report", ""), criteria),
        "分析深度": evaluate_with_llm(multi_result.get("report", ""), criteria),
        "结构化程度": evaluate_with_llm(multi_result.get("report", ""), criteria),
        "对比质量": evaluate_with_llm(multi_result.get("report", ""), criteria),
        "实用性": evaluate_with_llm(multi_result.get("report", ""), criteria),
    }

    # 计算提升
    improvement = {
        k: {
            "single": single_scores[k],
            "multi": multi_scores[k],
            "gain": f"+{multi_scores[k] - single_scores[k]}",
            "gain_pct": f"{(multi_scores[k] - single_scores[k]) / max(single_scores[k], 1) * 100:.0f}%"
        }
        for k in single_scores
    }

    return {
        "topic": topic,
        "single_agent": {
            "report": single_result.get("report", ""),
            "time_seconds": round(single_time, 1),
            "scores": single_scores,
        },
        "multi_agent": {
            "report": multi_result.get("report", ""),
            "time_seconds": round(multi_time, 1),
            "scores": multi_scores,
            "agent_times": multi_result.get("agent_times", {}),
        },
        "improvement": improvement,
    }
