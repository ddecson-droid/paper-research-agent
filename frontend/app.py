"""Streamlit 前端 - 论文研究助手（增强检索版）"""
import sys, os, io, json, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from backend.agents.pipeline import ResearchPipeline

st.set_page_config(page_title="多Agent学术论文研究助手", page_icon="📚", layout="wide")

# ---- 侧边栏 ----
with st.sidebar:
    st.header("⚙️ 配置")
    topic = st.text_input("研究方向", placeholder="例如: Multi-Agent Reinforcement Learning", value="")
    eval_mode = st.checkbox("运行评估模式（对比单Agent vs 多Agent）", value=False)
    submit = st.button("🚀 开始研究", type="primary", use_container_width=True)

    st.divider()
    st.caption("4 Agent 协作：检索 → 分析 → 对比 → 撰写")
    st.caption("多源检索 + 质量评分：Semantic Scholar + arxiv")

# ---- 主页面 ----
st.title("📚 多Agent学术论文研究助手")
st.caption("输入研究方向，多源检索 + 4个专业Agent自动协作，生成结构化文献综述")

if not submit or not topic.strip():
    st.info('👈 在左侧输入研究方向，点击「开始研究」')
    # 示例
    st.divider()
    st.subheader("📋 示例研究方向")
    examples = [
        "Multi-Agent Reinforcement Learning",
        "Retrieval-Augmented Generation for LLMs",
        "Vision Transformer Architecture Improvements",
        "Tool-Augmented Language Models",
    ]
    cols = st.columns(2)
    for i, ex in enumerate(examples):
        with cols[i % 2]:
            if st.button(ex, use_container_width=True):
                topic = ex
                submit = True

if submit and topic.strip():
    pipeline = ResearchPipeline()

    # ---- Tab 1: 检索结果 ----
    tab1, tab2, tab3, tab4 = st.tabs(["📖 论文检索", "🔍 深度分析", "⚖️ 对比", "📝 综述报告"])

    with tab1:
        with st.spinner("Agent 1/4: 多源检索 + 质量评分中（Semantic Scholar + arxiv）..."):
            papers = pipeline.search_engine.search(topic, max_results=8)
            retrieval = pipeline.retriever.run(topic, papers)

        st.subheader(f"检索到 {len(papers)} 篇论文")
        st.markdown(retrieval)

        for i, p in enumerate(papers):
            with st.expander(f"[{i+1}] {p['title']}"):
                st.write(f"**作者**: {', '.join(p.get('authors',[])[:5])}")
                st.write(f"**年份**: {p.get('year','')}")

                # 引用量
                cites = p.get('citation_count', 0)
                if cites:
                    cite_str = f"{cites:,}"
                    inf = p.get('influential_citation_count')
                    if inf:
                        cite_str += f"（高影响力: {inf:,}）"
                    st.write(f"**引用量**: {cite_str}")

                # venue / journal
                venue = p.get('venue', '') or p.get('journal', '')
                if venue:
                    st.write(f"**发表venue**: {venue}")

                # 综合评分
                score = p.get('score')
                if score is not None:
                    st.write(f"**综合评分**: {score:.2f}")

                # 来源
                source_label = {
                    "semantic_scholar": "Semantic Scholar",
                    "arxiv": "arXiv",
                    "fallback": "离线数据库",
                }.get(p.get('source', ''), p.get('source', ''))
                if source_label:
                    st.write(f"**来源**: {source_label}")

                st.write(f"**摘要**: {p.get('summary','')[:500]}")
                if p.get("url"):
                    st.write(f"[链接]({p['url']})")
                if p.get("pdf_url"):
                    st.write(f"[PDF]({p['pdf_url']})")

    # ---- Tab 2: 分析 ----
    with tab2:
        analyses_parts = []
        with st.spinner("Agent 2/4: 深度分析每篇论文..."):
            for i, p in enumerate(papers[:5]):
                st.write(f"**分析论文 {i+1}/{min(5,len(papers))}**: {p['title'][:80]}...")
                paper_text = (
                    f"标题: {p['title']}\n作者: {', '.join(p.get('authors',[])[:3])}\n"
                    f"年份: {p.get('year','')}\n"
                    f"引用量: {p.get('citation_count', 'N/A')}\n"
                    f"发表venue: {p.get('venue', '') or p.get('journal', 'N/A')}\n"
                    f"摘要: {p.get('summary','')}"
                )
                analysis = pipeline.analyzer.run(paper_text)
                analyses_parts.append(f"--- 论文{i+1} ---\n{analysis}")
                with st.expander(f"分析: {p['title'][:60]}..."):
                    st.markdown(analysis)

        analysis_text = "\n\n".join(analyses_parts)

    # ---- Tab 3: 对比 ----
    with tab3:
        with st.spinner("Agent 3/4: 横向对比中..."):
            comparison = pipeline.comparator.run(analysis_text)
        st.markdown(comparison)

    # ---- Tab 4: 综述 ----
    with tab4:
        with st.spinner("Agent 4/4: 撰写综述中..."):
            report = pipeline.writer.run(topic, analysis_text, comparison)
        st.markdown(report)

        # 下载按钮
        st.download_button(
            "📥 下载综述 (Markdown)",
            report,
            file_name=f"文献综述_{topic.replace(' ','_')[:30]}.md",
            mime="text/markdown",
        )

    # ---- 评估模式（可选）----
    if eval_mode:
        st.divider()
        st.header("📊 评估：单Agent vs 多Agent")

        if st.button("运行评估对比", type="secondary"):
            from backend.evaluation.evaluator import run_evaluation

            with st.spinner("运行单Agent模式... 运行多Agent模式... LLM打分中..."):
                eval_data = run_evaluation(topic)

            st.subheader("评分对比")
            imp = eval_data["improvement"]

            # 表格
            rows = []
            for dim, scores in imp.items():
                rows.append({
                    "维度": dim,
                    "单Agent": scores["single"],
                    "多Agent": scores["multi"],
                    "提升": scores["gain"],
                    "提升比例": scores["gain_pct"],
                })
            st.dataframe(rows, use_container_width=True)

            # 时间对比
            t1, t2 = st.columns(2)
            with t1:
                st.metric("单Agent耗时", f"{eval_data['single_agent']['time_seconds']}秒")
            with t2:
                st.metric("多Agent耗时", f"{eval_data['multi_agent']['time_seconds']}秒")

            st.caption("多Agent耗时更长，但输出质量显著更高——这是质量与效率的权衡。")
