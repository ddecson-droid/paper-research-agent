"""
多源论文搜索引擎 —— 编排多查询、多数据源、去重、质量评分
"""
import math
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .semantic_scholar_tool import search_semantic_scholar
from .arxiv_tool import search_arxiv

# 中英文通用停用词
_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "in", "for", "on", "to",
    "with", "via", "by", "as", "at", "is", "it", "its", "be", "no",
    "not", "but", "from", "into", "over", "after", "before", "between",
    "has", "have", "been", "can", "could", "may", "might", "will",
    "would", "should", "that", "this", "these", "those", "each",
    "which", "what", "all", "any", "some", "many", "few", "more",
    "most", "other", "such", "only", "both", "new", "using", "based",
    "approach", "method", "model", "system", "towards", "toward",
    "learning", "language", "large", "through", "among", "across",
    "under", "well", "also",
}


def _normalize_title(title: str) -> str:
    """标准化标题用于比较"""
    t = title.lower()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    words = [w for w in t.split() if len(w) >= 2]
    return " ".join(words)


def _title_similarity(title1: str, title2: str) -> float:
    """基于词级 Jaccard 的标题相似度"""
    w1 = set(_normalize_title(title1).split())
    w2 = set(_normalize_title(title2).split())
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / len(w1 | w2)


class PaperSearchEngine:
    """
    多源、多查询论文检索 + 去重 + 质量评分。

    Usage:
        engine = PaperSearchEngine()
        papers = engine.search("Multi-Agent Reinforcement Learning", max_results=8)
    """

    def __init__(self):
        pass

    # ================================================================
    #  公开入口
    # ================================================================

    def search(self, topic: str, max_results: int = 10) -> list[dict]:
        """
        主入口：输入研究方向 → 返回排名后的优质论文列表。

        三级回退：
          1. S2 + arxiv 多源多查询
          2. 仅 arxiv（S2 完全失败时）
          3. 离线 fallback 数据
        """
        queries = self._generate_queries(topic)
        raw_papers = self._search_all_sources(queries)

        if not raw_papers:
            # Tier 2: 只走 arxiv
            raw_papers = search_arxiv(topic, max_results=20)

        if not raw_papers:
            # Tier 3: 离线 fallback
            return search_arxiv(topic, max_results=8)  # 内部会走 _fallback_papers

        unique = self._deduplicate(raw_papers)
        ranked = self._score_and_rank(unique, topic)
        return ranked[:max_results]

    # ================================================================
    #  查询生成
    # ================================================================

    def _generate_queries(self, topic: str) -> list[str]:
        """
        从研究方向中生成 3-4 个不同角度的搜索查询。

        规则策略：
          1. 原始 topic
          2. 提取关键名词短语的组合
          3. 去掉最后一个限定词（更宽泛的查询）
          4. 核心短语（仅保留名词短语）
        """
        queries = [topic.strip()]

        # 提取有意义的关键词（长度 ≥ 3 的非停用词）
        words = topic.lower().split()
        keywords = [w for w in words if w not in _STOPWORDS and len(w) >= 3]

        if len(keywords) >= 4:
            # 查询 2: 前两个 + 后两个关键词（另一种组合）
            alt = f"{keywords[0]} {keywords[1]} {keywords[-2]} {keywords[-1]}"
            if alt != queries[0].lower():
                queries.append(alt)

            # 查询 3: 去掉最后一个词（更宽泛）
            broader = " ".join(keywords[:-1])
            if broader != queries[0].lower():
                queries.append(broader)

            # 查询 4: 只用核心词
            core = " ".join(keywords[:3])
            if core not in [q.lower() for q in queries]:
                queries.append(core)

        elif len(keywords) >= 2:
            # 查询 2: 调换顺序
            alt = f"{keywords[-1]} {keywords[0]}"
            if alt != queries[0].lower():
                queries.append(alt)
            # 查询 3: 更宽泛
            broader = " ".join(keywords[:-1]) if len(keywords) > 2 else keywords[0]
            if broader not in [q.lower() for q in queries]:
                queries.append(broader)

        return queries[:4]

    # ================================================================
    #  多源搜索
    # ================================================================

    def _search_all_sources(self, queries: list[str]) -> list[dict]:
        """每个查询并行调用 S2 + arxiv"""
        all_papers: list[dict] = []

        for query in queries:
            with ThreadPoolExecutor(max_workers=2) as executor:
                s2_future = executor.submit(search_semantic_scholar, query, 15)
                arxiv_future = executor.submit(search_arxiv, query, 8)

                for future in as_completed([s2_future, arxiv_future]):
                    try:
                        papers = future.result()
                        if papers:
                            all_papers.extend(papers)
                    except Exception:
                        pass

        return all_papers

    # ================================================================
    #  去重
    # ================================================================

    def _deduplicate(self, papers: list[dict]) -> list[dict]:
        """
        三遍去重：
          1. DOI 精确匹配（保留 S2 → 数据更丰富）
          2. arXiv ID 精确匹配
          3. 标题 Jaccard 相似度 ≥ 0.75（保留引用量更高者）
        """
        if len(papers) <= 1:
            return papers

        kept: dict[int, dict] = {}  # index → paper
        seen_doi: dict[str, int] = {}
        seen_arxivid: dict[str, int] = {}

        # Pass 1: DOI
        for i, p in enumerate(papers):
            doi = (p.get("doi") or "").strip().lower()
            if doi:
                if doi in seen_doi:
                    prev_idx = seen_doi[doi]
                    if not kept.get(prev_idx):
                        continue
                    # 保留有引用量数据或来源更好的
                    prev = kept[prev_idx]
                    if self._is_better_source(p, prev):
                        kept[prev_idx] = p
                else:
                    seen_doi[doi] = i
                    kept[i] = p
            else:
                kept[i] = p

        # Pass 2: arXiv ID
        remaining = {i: p for i, p in kept.items()
                     if not (p.get("doi") or "").strip().lower()}
        kept2 = {i: p for i, p in kept.items()
                 if (p.get("doi") or "").strip().lower()}

        for i, p in remaining.items():
            aid = (p.get("arxiv_id") or "").strip()
            if aid:
                if aid in seen_arxivid:
                    prev_idx = seen_arxivid[aid]
                    prev = kept2.get(prev_idx)
                    if prev and self._is_better_source(p, prev):
                        kept2[prev_idx] = p
                else:
                    seen_arxivid[aid] = i
                    kept2[i] = p
            else:
                kept2[i] = p

        # Pass 3: 标题相似度
        final_papers = list(kept2.values())
        result: list[dict] = []

        for i, p in enumerate(final_papers):
            is_dup = False
            for j, existing in enumerate(result):
                if _title_similarity(p.get("title", ""), existing.get("title", "")) >= 0.75:
                    is_dup = True
                    if self._is_better_paper(p, existing):
                        result[j] = p
                    break
            if not is_dup:
                result.append(p)

        return result

    @staticmethod
    def _is_better_source(a: dict, b: dict) -> bool:
        """a 是否比 b 更好的数据源？"""
        score_a = 2 if a.get("source") == "semantic_scholar" else 1
        score_b = 2 if b.get("source") == "semantic_scholar" else 1
        return score_a > score_b

    @staticmethod
    def _is_better_paper(a: dict, b: dict) -> bool:
        """a 是否比 b 更好（引用量高或数据更丰富）？"""
        cites_a = a.get("citation_count", 0) or 0
        cites_b = b.get("citation_count", 0) or 0
        if cites_a != cites_b:
            return cites_a > cites_b
        return PaperSearchEngine._is_better_source(a, b)

    # ================================================================
    #  评分排序
    # ================================================================

    def _score_and_rank(self, papers: list[dict], topic: str) -> list[dict]:
        """对论文评分并排序"""
        max_cites = max((p.get("citation_count") or 0 for p in papers), default=1)
        if max_cites < 1:
            max_cites = 1

        topic_words = self._extract_topic_words(topic)
        current_year = datetime.now().year

        for p in papers:
            citation_score = self._citation_score(p.get("citation_count") or 0, max_cites)
            recency_score = self._recency_score(p, current_year)
            source_score = self._source_score(p)
            relevance_score = self._keyword_relevance(p, topic_words)
            p["score"] = (
                0.35 * citation_score
                + 0.15 * recency_score
                + 0.10 * source_score
                + 0.40 * relevance_score
            )

        papers.sort(key=lambda x: x.get("score", 0), reverse=True)
        return papers

    def _citation_score(self, count: int, max_count: int) -> float:
        return math.log(1 + count) / math.log(1 + max_count)

    def _recency_score(self, paper: dict, current_year: int) -> float:
        year_str = paper.get("year", "")
        if not year_str:
            return 0.0
        try:
            age = current_year - int(year_str)
        except (ValueError, TypeError):
            return 0.0
        if age < 0:
            return 1.0
        return max(0.0, 1.0 - 0.12 * age)

    def _source_score(self, paper: dict) -> float:
        source = paper.get("source", "arxiv")
        if source == "semantic_scholar":
            if paper.get("venue") or paper.get("journal"):
                return 1.0
            return 0.8
        return 0.5  # arxiv only

    def _extract_topic_words(self, topic: str) -> list[str]:
        """从 topic 提取关键词"""
        words = re.findall(r"[a-zA-Z一-鿿]+", topic.lower())
        return [w for w in words
                if w not in _STOPWORDS and len(w) >= 2]

    def _keyword_relevance(self, paper: dict, topic_words: list[str]) -> float:
        """计算 title + abstract 中 topic 关键词的命中率"""
        if not topic_words:
            return 0.5
        text = (paper.get("title") or "") + " " + (paper.get("summary") or "")
        text_lower = text.lower()
        hits = sum(1 for w in topic_words if w in text_lower)
        return hits / len(topic_words)
