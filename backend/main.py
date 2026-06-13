"""FastAPI 后端入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .models import ResearchRequest, ResearchResponse
from .agents.pipeline import ResearchPipeline
from .evaluation.evaluator import run_evaluation

app = FastAPI(title="Paper Research Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "Paper Research Agent"}


@app.post("/research", response_model=ResearchResponse)
def research(request: ResearchRequest):
    """执行多Agent研究流水线"""
    pipeline = ResearchPipeline()
    result = pipeline.run(request.topic)

    eval_data = None
    if request.run_evaluation:
        eval_data = run_evaluation(request.topic)

    return ResearchResponse(
        success=True,
        topic=request.topic,
        papers=result["papers"],
        analysis=result["analysis"],
        comparison=result["comparison"],
        report=result["report"],
        agent_times=result["agent_times"],
        evaluation=eval_data,
    )


@app.post("/evaluate")
def evaluate(request: ResearchRequest):
    """独立评估接口——对比单Agent vs 多Agent"""
    return run_evaluation(request.topic)
