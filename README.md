# 📚 多 Agent 学术论文研究助手

基于 **4 个专业 AI Agent 协作**的学术文献综述自动生成系统。输入一个研究方向，系统自动完成论文检索 → 深度分析 → 横向对比 → 综述撰写全流程。

> 🏗️ **完全自包含** — 不依赖第三方 Agent 框架，核心 LLM/Agent 模块全部内联在 `backend/core.py` 中。

## ✨ 核心特性

- **4 Agent 流水线协作**：检索专家 → 分析专家 → 对比专家 → 撰写专家，各司其职
- **arXiv 实时搜索**：通过官方 API 检索最新论文，离线时自动回退到经典论文库
- **结构化深度分析**：每篇论文 6 维度分析（问题/方法/数据/指标/创新/局限）
- **横向对比**：方法间的差异对比表 + 适用场景建议 + 技术趋势判断
- **学术综述生成**：5 段式结构化文献综述，可直接下载 Markdown
- **质量评估框架**：内置单 Agent vs 多 Agent 对比评估，LLM 裁判 5 维度打分
- **双入口**：Streamlit 可视化前端 + FastAPI REST 后端
- **灵活 LLM 配置**：支持任意 OpenAI 兼容接口（DeepSeek / OpenAI / 通义千问 / 智谱 等）

## 🏗️ 架构概览

```
┌─────────────────────────────────────────────────────┐
│                    用户输入                           │
│              (研究方向，如 "Tool-Augmented LLMs")      │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  Agent 1: 📖 文献检索专家 (RetrieverAgent)           │
│  ┌─────────────────────────────────────────────┐    │
│  │ • arxiv API 搜索 → 整理结果 → 标注相关度     │    │
│  │ • 无网络时自动回退到离线经典论文数据库         │    │
│  └─────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────┘
                       │ 论文列表 (最多8篇)
                       ▼
┌─────────────────────────────────────────────────────┐
│  Agent 2: 🔍 论文分析专家 (AnalyzerAgent)            │
│  ┌─────────────────────────────────────────────┐    │
│  │ 对前5篇论文逐篇结构化分析:                    │    │
│  │ 研究问题 | 方法 | 数据集 | 指标 | 创新 | 局限 │    │
│  └─────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────┘
                       │ 分析结果
                       ▼
┌─────────────────────────────────────────────────────┐
│  Agent 3: ⚖️ 论文对比专家 (ComparatorAgent)          │
│  ┌─────────────────────────────────────────────┐    │
│  │ 横向对比: 共同点 | 差异表 | 适用场景 | 趋势   │    │
│  └─────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────┘
                       │ 对比结果
                       ▼
┌─────────────────────────────────────────────────────┐
│  Agent 4: 📝 综述撰写专家 (WriterAgent)              │
│  ┌─────────────────────────────────────────────┐    │
│  │ 5段式综述: 背景→方法分类→代表工作→对比→展望  │    │
│  └─────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
              结构化文献综述输出
     (papers + analysis + comparison + report)
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone https://github.com/ddecson-droid/paper-research-agent.git
cd paper-research-agent

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 LLM

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填入你的 API Key
# 默认使用 DeepSeek，也可换用 OpenAI / 通义千问 / 智谱 等
```

`.env` 配置示例：

```env
LLM_API_KEY=sk-your-api-key-here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_ID=deepseek-chat
```

### 3. 启动应用

**方式 A：Streamlit 前端（推荐）**

```bash
streamlit run frontend/app.py
# 浏览器打开 http://localhost:8501
```

**方式 B：FastAPI 后端**

```bash
uvicorn backend.main:app --reload
# API 文档 http://localhost:8000/docs
```

## 🔌 API 接口

### `POST /research` — 执行研究

```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "Multi-Agent Reinforcement Learning"}'
```

返回：

```json
{
  "success": true,
  "topic": "Multi-Agent Reinforcement Learning",
  "papers": [{ "title": "...", "authors": [...], "year": "2023", ... }],
  "analysis": "### 论文分析...",
  "comparison": "### 横向对比分析...",
  "report": "# 文献综述...",
  "agent_times": {
    "retriever": 7.0,
    "analyzer": 34.5,
    "comparator": 18.5,
    "writer": 22.7
  }
}
```

### `POST /evaluate` — 质量评估

对比单 Agent vs 多 Agent 模式，从 5 个维度打分：

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{"topic": "Vision Transformer"}'
```

| 评估维度 | 说明 |
|---------|------|
| 文献覆盖率 | 是否覆盖该领域主要工作 |
| 分析深度 | 对每篇论文的分析是否深入具体 |
| 结构化程度 | 报告结构是否清晰、逻辑连贯 |
| 对比质量 | 方法间对比是否有价值 |
| 实用性 | 对研究者是否有参考价值 |

## 📁 项目结构

```
paper-research-agent/
├── backend/
│   ├── core.py                 # 🔑 自包含 LLM + Agent 核心（替代 hello-agents）
│   ├── config.py               # 配置管理
│   ├── models.py               # Pydantic 数据模型
│   ├── main.py                 # FastAPI 入口
│   ├── agents/
│   │   ├── pipeline.py         # 4 Agent 研究流水线
│   │   ├── retriever.py        # Agent 1: 文献检索专家
│   │   ├── analyzer.py         # Agent 2: 论文分析专家
│   │   ├── comparator.py       # Agent 3: 论文对比专家
│   │   └── writer.py           # Agent 4: 综述撰写专家
│   ├── tools/
│   │   └── arxiv_tool.py       # arXiv API 搜索 + 离线回退
│   └── evaluation/
│       └── evaluator.py        # 单Agent vs 多Agent 质量评估
├── frontend/
│   └── app.py                  # Streamlit 前端界面
├── requirements.txt
├── .env.example
└── README.md
```

## 🧠 设计理念

### 为什么用多 Agent 而不是单 Agent？

单个全能 Agent 一次性完成"搜索→分析→对比→撰写"时，容易出现：

- **注意力分散**：提示词过长导致忽略关键细节
- **分析浅层**：没有专门化的分析视角
- **对比缺失**：容易只介绍而不对比
- **结构松散**：综述缺乏学术规范的结构

4 Agent 分工协作解决了这些问题：每个 Agent 有**精确定义的角色和输出格式**，专注于单一子任务，整体质量显著更高。

### 自包含设计

整个项目 **零外部 Agent 框架依赖**。`backend/core.py` 从零实现了：

- `HelloAgentsLLM` — 基于 OpenAI SDK 的统一 LLM 客户端，支持流式/非流式调用
- `SimpleAgent` — 简洁的 Agent 抽象（系统提示词 + 对话历史 + LLM 调用）
- `Agent` / `Message` — 轻量基类和消息系统

你只需要 `pip install -r requirements.txt`，无需安装 hello-agents 或其他 Agent 框架。

## 🔄 离线模式

当 arXiv API 无法访问时，系统自动切换到内置经典论文数据库，覆盖以下方向：

- **Agent / 工具增强**：ReAct, Toolformer, AutoGen
- **Transformer**：Attention Is All You Need, BERT

离线模式确保即使在没有网络的环境下，Demo 也能正常运行。

## 📊 评估结果示例

运行 `/evaluate` 接口后，LLM 裁判会从 5 个维度分别对单 Agent 和多 Agent 输出打分：

| 维度 | 单Agent | 多Agent | 提升 |
|------|---------|---------|------|
| 文献覆盖率 | 3 | 4 | +1 (33%) |
| 分析深度 | 3 | 4 | +1 (33%) |
| 结构化程度 | 3 | 5 | +2 (67%) |
| 对比质量 | 2 | 4 | +2 (100%) |
| 实用性 | 3 | 4 | +1 (33%) |

> 多 Agent 模式在结构化程度和对比质量上优势尤为明显。

## 📄 License

MIT License
