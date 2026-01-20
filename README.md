# MyAgent

> 🤖 基于 LangGraph 的智能对话助手，支持联网搜索、知识库 RAG、多模型切换

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0+-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docs.docker.com/compose/)

---

## ✨ 功能特性

| 模块 | 功能描述 |
|------|----------|
| **智能对话** | 基于 LangGraph 工作流，支持 DeepSeek / OpenAI / Gemini 等多模型 |
| **联网搜索** | 集成 Tavily Search，实时获取网络信息增强回答 |
| **知识库 RAG** | 支持 PDF/DOCX 文档解析，pgvector 向量检索 + BM25 混合召回 |
| **用户模型** | 用户可自定义配置第三方 LLM 模型（API Key 加密存储） |
| **对话记忆** | PostgreSQL Checkpoint 持久化，完整保存对话历史与状态 |
| **可观测性** | 集成 Langfuse，追踪 LLM 调用链路与质量评估 |
| **文件存储** | 阿里云 OSS 对象存储，支持头像上传与文档管理 |

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React 19)                     │
│         Vite + TailwindCSS + Zustand + React Query          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI + LangGraph)              │
├─────────────────────────────────────────────────────────────┤
│  API Layer     │  Services      │  Agent Nodes               │
│  ├─ /auth      │  ├─ Chat       │  ├─ Chatbot Node           │
│  ├─ /chat      │  ├─ Knowledge  │  ├─ Search Node            │
│  ├─ /user      │  ├─ Embedding  │  ├─ Rewrite Node           │
│  └─ /knowledge │  └─ Checkpoint │  ├─ Planning Node          │
│                │                │  └─ Summary Node           │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  PostgreSQL   │   │      Redis      │   │   Celery Worker │
│  + pgvector   │   │    (Cache)      │   │ (Async Tasks)   │
└───────────────┘   └─────────────────┘   └─────────────────┘
```

---

## 📁 项目结构

```
my-agent/
├── backend/                    # Python 后端
│   ├── app/
│   │   ├── api/               # FastAPI 路由
│   │   ├── agent/             # LangGraph Agent 定义
│   │   ├── nodes/             # Agent 节点实现
│   │   ├── services/          # 业务服务层
│   │   ├── models/            # SQLAlchemy 模型
│   │   ├── tasks/             # Celery 异步任务
│   │   ├── tools/             # Agent 工具
│   │   └── utils/             # 工具类
│   ├── alembic/               # 数据库迁移
│   └── pyproject.toml         # 依赖配置 (uv)
│
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── components/        # UI 组件
│   │   ├── pages/             # 页面
│   │   ├── stores/            # Zustand 状态管理
│   │   └── api/               # API 客户端
│   └── package.json
│
├── docker-compose.yml          # 本地开发环境
├── docker-compose.prod.yml     # 生产环境
├── Makefile                    # 常用命令
└── .env.example                # 环境变量示例
```

---

## 🚀 快速开始

### 前置要求

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [Node.js 20+](https://nodejs.org/) (本地开发前端)
- [uv](https://github.com/astral-sh/uv) (本地开发后端)

### 1️⃣ 环境配置

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env，填入必要配置
# 必填: DB_PASSWORD, REDIS_PASSWORD, JWT_SECRET, AI_DEEPSEEK_API_KEY
```

### 2️⃣ Docker 一键启动

```bash
# 启动所有服务 (后端 + 前端 + PostgreSQL + Redis)
docker compose up -d

# 查看服务状态
docker compose ps

# 查看后端日志
docker compose logs -f backend
```

服务访问地址：
- 前端: http://localhost:3001
- 后端 API: http://localhost:8081
- 健康检查: http://localhost:8081/api/chat/health

### 3️⃣ 本地开发模式

**后端开发：**
```bash
# 安装依赖
make backend-install

# 启动开发服务器 (热重载)
make run
```

**前端开发：**
```bash
# 安装依赖
make frontend-install

# 启动开发服务器
make frontend-run
```

---

## ⚙️ 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| **数据库** |||
| `DB_HOST` | PostgreSQL 主机 | `localhost` |
| `DB_PASSWORD` | 数据库密码 | - |
| **Redis** |||
| `REDIS_HOST` | Redis 主机 | `localhost` |
| `REDIS_PASSWORD` | Redis 密码 | - |
| **认证** |||
| `JWT_SECRET` | JWT 密钥 | - |
| `JWT_EXPIRE_MINUTES` | Token 过期时间(分钟) | `60` |
| **AI 模型** |||
| `AI_DEEPSEEK_API_KEY` | DeepSeek API Key | - |
| `AI_DEEPSEEK_MODEL_NAME` | 模型名称 | `deepseek-chat` |
| **向量化** |||
| `AI_EMBEDDING_PROVIDER` | 提供商 (local/openai) | `local` |
| `AI_EMBEDDING_MODEL` | Embedding 模型 | `BAAI/bge-small-zh-v1.5` |
| **可选服务** |||
| `TAVILY_API_KEY` | Tavily 搜索 API Key | - |
| `LANGFUSE_PUBLIC_KEY` | Langfuse 公钥 | - |
| `OSS_ACCESS_KEY_ID` | 阿里云 OSS Key | - |

完整配置参考 [.env.example](.env.example)

---

## 🧰 常用命令

```bash
# 查看所有命令
make help

# 代码检查
make lint

# 代码格式化
make format

# 运行测试
make test

# 数据库迁移
make db-migrate

# 清理缓存
make clean
```

---

## 📊 可观测性

项目集成 [Langfuse](https://langfuse.com/) 进行 LLM 调用追踪：

1. 注册 [Langfuse Cloud](https://cloud.langfuse.com/) 或自建
2. 配置环境变量:
   ```env
   LANGFUSE_ENABLED=true
   LANGFUSE_PUBLIC_KEY=pk-xxx
   LANGFUSE_SECRET_KEY=sk-xxx
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```
3. 访问 Langfuse Dashboard 查看追踪数据

---

## 🚢 生产部署

```bash
# 使用生产配置文件
docker compose -f docker-compose.prod.yml up -d

# 配合 Watchtower 自动更新 (可选)
docker run -d \
  --name watchtower \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --interval 300
```

> **生产环境建议**：使用反向代理(Nginx/OpenResty)处理 HTTPS、配置合理的连接池参数、启用 Redis 持久化。

---

## 📝 开发路线

- [x] 基础对话功能
- [x] LangGraph Agent 架构
- [x] 联网搜索 (Tavily)
- [x] 知识库 RAG
- [x] 用户自定义模型
- [x] Langfuse 可观测性
- [ ] 多轮对话分支
- [ ] 语音输入/输出
- [ ] 插件系统

---

## 📄 License

MIT License
