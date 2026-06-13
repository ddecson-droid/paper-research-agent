"""
多源论文搜索引擎 —— 编排多查询、多数据源、去重、质量评分
含 S2 健康检查 + 智能跳过 + arxiv 多查询增强
"""
import math
import re
import time
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

# S2 健康管理
_S2_COOLDOWN_SECONDS = 900  # 15 分钟冷却
_S2_MAX_CONSECUTIVE_FAILS = 3  # 连续失败 3 次触发冷却


def _normalize_title(title: str) -> str:
    t = title.lower()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    words = [w for w in t.split() if len(w) >= 2]
    return " ".join(words)


def _title_similarity(title1: str, title2: str) -> float:
    w1 = set(_normalize_title(title1).split())
    w2 = set(_normalize_title(title2).split())
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / len(w1 | w2)


class PaperSearchEngine:
    """
    多源、多查询论文检索 + 去重 + 质量评分。

    智能源管理：
      - S2 连续失败 3 次 → 15 分钟冷却（跳过 S2，走 arxiv 多查询）
      - 冷却期满后自动重试，成功则恢复
      - arxiv 始终可用，S2 unhealthy 时 arxiv 对每个 query 都搜索
    """

    def __init__(self):
        self._s2_healthy = True
        self._s2_fail_count = 0
        self._s2_cooldown_until: float = 0.0

    # ================================================================
    #  公开入口
    # ================================================================

    def search(self, topic: str, max_results: int = 10) -> list[dict]:
        """
        主入口：输入研究方向 → 返回排名后的优质论文列表。

        三级回退：
          1. S2 + arxiv 多源多查询
          2. arxiv 多查询（S2 unhealthy 或失败时）
          3. 离线 fallback 数据
        """
        queries = self._generate_queries(topic)
        raw_papers = self._search_all_sources(queries)

        if not raw_papers:
            # Tier 2: arxiv 多查询
            raw_papers = self._search_arxiv_multi(queries, limit=15)

        if not raw_papers:
            # Tier 3: 离线 fallback
            return search_arxiv(topic, max_results=8)

        unique = self._deduplicate(raw_papers)
        ranked = self._score_and_rank(unique, topic)
        return ranked[:max_results]

    # ================================================================
    #  S2 健康管理
    # ================================================================

    def _check_s2_health(self) -> bool:
        """检查 S2 是否可用，处理冷却期"""
        if self._s2_healthy:
            return True
        # 冷却期到了，允许重试
        if time.time() > self._s2_cooldown_until:
            self._s2_healthy = True
            self._s2_fail_count = 0
            return True
        return False

    def _record_s2_failure(self):
        """记录 S2 一次失败"""
        self._s2_fail_count += 1
        if self._s2_fail_count >= _S2_MAX_CONSECUTIVE_FAILS:
            self._s2_healthy = False
            self._s2_cooldown_until = time.time() + _S2_COOLDOWN_SECONDS
            self._s2_fail_count = 0

    def _record_s2_success(self):
        """重置 S2 失败计数"""
        if self._s2_fail_count > 0:
            self._s2_fail_count = 0

    # ================================================================
    #  查询生成
    # ================================================================

    def _generate_queries(self, topic: str) -> list[str]:
        """从研究方向中生成 3-4 个不同角度的搜索查询"""
        queries = [topic.strip()]
        words = topic.lower().split()
        keywords = [w for w in words if w not in _STOPWORDS and len(w) >= 3]

        if len(keywords) >= 4:
            alt = f"{keywords[0]} {keywords[1]} {keywords[-2]} {keywords[-1]}"
            if alt != queries[0].lower():
                queries.append(alt)
            broader = " ".join(keywords[:-1])
            if broader != queries[0].lower():
                queries.append(broader)
            core = " ".join(keywords[:3])
            if core not in [q.lower() for q in queries]:
                queries.append(core)
        elif len(keywords) >= 2:
            alt = f"{keywords[-1]} {keywords[0]}"
            if alt != queries[0].lower():
                queries.append(alt)
            broader = " ".join(keywords[:-1]) if len(keywords) > 2 else keywords[0]
            if broader not in [q.lower() for q in queries]:
                queries.append(broader)

        return queries[:4]

    # ================================================================
    #  多源搜索
    # ================================================================

    def _search_all_sources(self, queries: list[str]) -> list[dict]:
        """多源搜索：S2 + arxiv。S2 unhealthy 时只走 arxiv"""
        all_papers: list[dict] = []
        use_s2 = self._check_s2_health()

        for query in queries:
            if use_s2:
                # S2 + arxiv 并行
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

                # 检查 S2 是否返回数据
                try:
                    s2_result = s2_future.result()
                    if s2_result:
                        self._record_s2_success()
                    else:
                        self._record_s2_failure()
                except Exception:
                    self._record_s2_failure()
            else:
                # S2 unhealthy → arxiv 多查询
                all_papers.extend(self._search_arxiv_multi(queries, limit=8))
                break  # arxiv 多查询一次搞定所有 query

        return all_papers

    def _search_arxiv_multi(self, queries: list[str], limit: int = 15) -> list[dict]:
        """仅 arxiv 多查询搜索（S2 不可用时的增强备选）"""
        all_papers: list[dict] = []

        with ThreadPoolExecutor(max_workers=min(len(queries), 4)) as executor:
            futures = {
                executor.submit(search_arxiv, q, limit): q for q in queries
            }
            for future in as_completed(futures):
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
        """三遍去重：DOI → arXiv ID → 标题 Jaccard ≥ 0.75"""
        if len(papers) <= 1:
            return papers

        kept: dict[int, dict] = {}
        seen_doi: dict[str, int] = {}
        seen_arxivid: dict[str, int] = {}

        # Pass 1: DOI
        for i, p in enumerate(papers):
            doi = (p.get("doi") or "").strip().lower()
            if doi:
                if doi in seen_doi:
                    prev_idx = seen_doi[doi]
                    if kept.get(prev_idx) and self._is_better_source(p, kept[prev_idx]):
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

        for p in final_papers:
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
        score_a = 2 if a.get("source") == "semantic_scholar" else 1
        score_b = 2 if b.get("source") == "semantic_scholar" else 1
        return score_a > score_b

    @staticmethod
    def _is_better_paper(a: dict, b: dict) -> bool:
        cites_a = a.get("citation_count", 0) or 0
        cites_b = b.get("citation_count", 0) or 0
        if cites_a != cites_b:
            return cites_a > cites_b
        return PaperSearchEngine._is_better_source(a, b)

    # ================================================================
    #  评分排序
    # ================================================================

    def _score_and_rank(self, papers: list[dict], topic: str) -> list[dict]:
        """对论文评分并排序（自适应权重：有 S2 数据时用引用量，纯 arxiv 时靠相关性）"""
        has_citation_data = any(
            (p.get("citation_count") or 0) > 0 for p in papers
        )

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

            if has_citation_data:
                # 有引用数据：引用量 35% + 时效 15% + 来源 10% + 关键词 40%
                p["score"] = (
                    0.35 * citation_score
                    + 0.15 * recency_score
                    + 0.10 * source_score
                    + 0.40 * relevance_score
                )
            else:
                # 无引用数据（仅 arxiv）：引用量 15%（多为 0）+ 时效 15% + 来源 5% + 关键词 65%
                p["score"] = (
                    0.15 * citation_score
                    + 0.15 * recency_score
                    + 0.05 * source_score
                    + 0.65 * relevance_score
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
        return 0.5

    def _extract_topic_words(self, topic: str) -> list[str]:
        words = re.findall(r"[a-zA-Z一-鿿]+", topic.lower())
        return [w for w in words
                if w not in _STOPWORDS and len(w) >= 2]

    def _keyword_relevance(self, paper: dict, topic_words: list[str]) -> float:
        if not topic_words:
            return 0.5
        text = (paper.get("title") or "") + " " + (paper.get("summary") or "")
        text_lower = text.lower()
        hits = sum(1 for w in topic_words if w in text_lower)
        return hits / len(topic_words)
