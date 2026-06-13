"""数据模型"""
from pydantic import BaseModel
from typing import Optional


class ResearchRequest(BaseModel):
    topic: str
    run_evaluation: bool = False


class ResearchResponse(BaseModel):
    success: bool
    topic: str
    papers: list[dict] = []
    analysis: str = ""
    comparison: str = ""
    report: str = ""
    agent_times: dict = {}
    evaluation: Optional[dict] = None
