"""配置管理"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    llm_model_id: str = os.getenv("LLM_MODEL_ID", "deepseek-chat")
    semantic_scholar_api_key: str = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
    max_search_results: int = 10
    max_analysis_depth: int = 3


config = Config()
