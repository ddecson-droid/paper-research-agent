"""
Semantic Scholar API 论文搜索工具
支持 API Key（免费申请，提限 10x），返回引用量/venue/journal 等质量信号
"""
import os
import time
import requests
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

# 速率限制
_request_timestamps: list[float] = []

BASE_URL = "https://api.semanticscholar.org/graph/v1"
DEFAULT_FIELDS = (
    "title,abstract,year,citationCount,influentialCitationCount,"
    "authors,venue,journal,externalIds,publicationTypes,openAccessPdf"
)

# 有 key: 1000 req/5min → 安全上限 950;  无 key: 100 req/5min → 安全上限 95
_RATE_LIMIT_NO_KEY = 95
_RATE_LIMIT_WITH_KEY = 950


def _get_api_key() -> str:
    return os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()


def _rate_limit():
    """确保不超过 S2 速率限制"""
    global _request_timestamps
    has_key = bool(_get_api_key())
    limit = _RATE_LIMIT_WITH_KEY if has_key else _RATE_LIMIT_NO_KEY

    now = time.time()
    _request_timestamps = [t for t in _request_timestamps if now - t < 300]
    if len(_request_timestamps) >= limit:
        oldest = _request_timestamps[0]
        wait = oldest + 300 - now + 0.5
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

    Returns:
        论文列表。每篇包含 title, authors, year, summary, url, pdf_url,
        citation_count, influential_citation_count, venue, journal,
        doi, arxiv_id, source ("semantic_scholar")
    """
    params = {
        "query": query,
        "limit": min(limit, 100),
        "fields": fields or DEFAULT_FIELDS,
    }

    api_key = _get_api_key()
    headers = {"User-Agent": "PaperResearchAgent/2.0"}
    if api_key:
        headers["x-api-key"] = api_key

    try:
        _rate_limit()
        resp = requests.get(
            f"{BASE_URL}/paper/search",
            params=params,
            headers=headers,
            timeout=15,
        )

        if resp.status_code == 429:
            time.sleep(3)
            resp = requests.get(
                f"{BASE_URL}/paper/search",
                params=params,
                headers=headers,
                timeout=10,
            )
            if resp.status_code == 429:
                return []
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

        authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
        ext_ids = item.get("externalIds") or {}
        arxiv_id = ext_ids.get("ArXiv", "")
        doi = ext_ids.get("DOI", "")
        pdf_info = item.get("openAccessPdf") or {}
        pdf_url = pdf_info.get("url", "")
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
