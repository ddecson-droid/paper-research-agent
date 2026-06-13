"""
Semantic Scholar API 论文搜索工具
免费 API，无需 key，返回引用量/venue/journal 等质量信号
"""
import time
import requests
from typing import Optional

# 速率限制：每 5 分钟最多 95 次请求（上限 100，留 5 次余量）
_request_timestamps: list[float] = []

BASE_URL = "https://api.semanticscholar.org/graph/v1"
DEFAULT_FIELDS = (
    "title,abstract,year,citationCount,influentialCitationCount,"
    "authors,venue,journal,externalIds,publicationTypes,openAccessPdf"
)


def _rate_limit():
    """确保不超过 S2 的速率限制（无 API key 时 100 req/5min）"""
    global _request_timestamps
    now = time.time()
    # 清除 300 秒前的记录
    _request_timestamps = [t for t in _request_timestamps if now - t < 300]
    if len(_request_timestamps) >= 95:
        oldest = _request_timestamps[0]
        wait = oldest + 300 - now + 0.5  # 等最老的过期再加 0.5 秒余量
        if wait > 0:
            time.sleep(wait)
    _request_timestamps.append(time.time())


def search_semantic_scholar(
    query: str,
    limit: int = 20,
    fields: Optional[str] = None,
) -> list[dict]:
    """
    搜索 Semantic Scholar 论文。

    Args:
        query: 搜索关键词
        limit: 最大返回数 (1-100)
        fields: 请求字段，默认包含 title/abstract/citation/venue 等

    Returns:
        论文列表，每篇包含:
        title, authors, year, summary (abstract), url, pdf_url,
        citation_count, influential_citation_count, venue, journal,
        doi, arxiv_id, source ("semantic_scholar")
    """
    params = {
        "query": query,
        "limit": min(limit, 100),
        "fields": fields or DEFAULT_FIELDS,
    }

    try:
        _rate_limit()
        resp = requests.get(
            f"{BASE_URL}/paper/search",
            params=params,
            headers={"User-Agent": "PaperResearchAgent/2.0"},
            timeout=15,
        )

        if resp.status_code == 429:
            # 被限流，等 5 秒重试一次，再失败就快速回退
            time.sleep(5)
            resp = requests.get(
                f"{BASE_URL}/paper/search",
                params=params,
                headers={"User-Agent": "PaperResearchAgent/2.0"},
                timeout=10,
            )
            if resp.status_code == 429:
                return []  # 不再死等，让 arxiv 顶上
        elif resp.status_code >= 500:
            return []

        resp.raise_for_status()
        data = resp.json()

    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        return []
    except Exception:
        return []

    papers = []
    for item in data.get("data", []):
        if not item.get("title"):
            continue

        # 提取作者名
        authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]

        # 提取 arXiv ID 和 DOI
        ext_ids = item.get("externalIds") or {}
        arxiv_id = ext_ids.get("ArXiv", "")
        doi = ext_ids.get("DOI", "")

        # 提取开放获取 PDF
        pdf_info = item.get("openAccessPdf") or {}
        pdf_url = pdf_info.get("url", "")

        # venue 和 journal
        venue = item.get("venue") or ""
        journal_info = item.get("journal") or {}
        journal = journal_info.get("name", "") if journal_info else ""

        papers.append({
            "title": item.get("title", "").strip(),
            "authors": authors,
            "year": str(item.get("year")) if item.get("year") else "",
            "summary": (item.get("abstract") or "")[:500],
            "url": f"https://www.semanticscholar.org/paper/{item.get('paperId','')}",
            "pdf_url": pdf_url,
            "citation_count": item.get("citationCount") or 0,
            "influential_citation_count": item.get("influentialCitationCount") or 0,
            "venue": venue,
            "journal": journal,
            "doi": doi,
            "arxiv_id": arxiv_id,
            "source": "semantic_scholar",
        })

    return papers
