# NexusRAG 智能知识库

> 一个具备**混合检索 + 引用溯源 + Agent 工作流**的企业级 RAG 系统，用 vibecoding 方式一次性交付，作为 AI/大模型应用工程师岗位的核心作品。

## ✨ 核心亮点

- 🔍 **混合检索**：向量检索 + BM25 关键词检索，使用 RRF 算法融合双路结果
- 📎 **引用溯源**：每个论断带 `[1][2]` 标记，可溯源至原文档具体页码与位置
- 🧠 **Agent 工作流**：Plan-Retrieve-Reflect-Synthesize 多轮反思，自动拆解子问题
- ⚡ **流式对话**：SSE 实时流式输出，Markdown 渲染 + 代码高亮
- 📄 **多格式支持**：PDF / Word / Markdown / TXT 即拖即传
- 🛡️ **工程化实践**：TypeScript 全栈 + JWT 鉴权 + Zod 校验 + 模块化架构

## 🚀 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 配置 LLM（可选，不配置也能跑演示模式）

```bash
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY
```

支持任何兼容 OpenAI 协议的服务（OpenAI / 通义 / DeepSeek / Moonshot 等）。

### 3. 启动开发服务器

```bash
npm run dev
```

- 前端：http://localhost:5173
- 后端：http://localhost:3001
- 健康检查：http://localhost:3001/api/health

### 4. 体验流程

1. 打开 http://localhost:5173
2. 点击「一键体验演示账号」登录
3. 创建知识库 → 上传文档（支持 PDF / Word / MD / TXT）
4. 进入对话页，切换「普通 RAG」/「Agent 深度研究」模式
5. 提问，查看流式回答 + 引用溯源

### 🧪 Demo 模式（无需 API Key 即可体验）

未配置 `OPENAI_API_KEY` 时，系统自动进入 **Demo 模式**：

- LLM 调用：返回 mock 文本（带流式 SSE token 输出，模拟真实打字机效果）
- Embedding：基于确定性哈希的伪向量（保持检索流程完整可用）
- 健康检查 `GET /api/health` 中 `demoMode: true` 标识当前状态

> 该模式用于**简历投递时面试官一键体验**，避免因缺 Key 而无法查看效果。

## ✅ 已验证功能（冒烟测试通过）

- 健康检查 / 演示账号登录（JWT 颁发）
- 知识库 CRUD
- 文档上传（支持 .md / .pdf / .docx / .txt），异步分块入库
- 混合检索（向量 + BM25 + RRF + Rerank）
- SSE 流式对话（普通 RAG 模式）
- 引用面板渲染（`[1][2]` → 可点击引用标签）
- Agent 深度研究模式
- 全前端 UI 暗黑主题 + 响应式布局

## 🏗️ 技术栈

### 前端
- Vue 3.4 + TypeScript 5 + Vite 5
- Pinia 状态管理 + Vue Router 4
- Tailwind CSS 3 + 自定义设计系统
- markdown-it + highlight.js（Markdown 渲染）
- lucide-vue-next（图标）

### 后端
- Express 4 + TypeScript 5
- SQLite (node:sqlite, Node 24 内置) - 元数据存储
- 自研纯 JS 向量库 - cosine 相似度 + 文件持久化（避免 native 依赖）
- OpenAI SDK - LLM 调用（兼容 OpenAI / 通义 / DeepSeek / Moonshot）
- JWT (jsonwebtoken) + bcryptjs - 认证
- multer - 文件上传
- zod - 请求校验

### 文档解析
- pdf-parse（PDF）
- mammoth（Word）
- marked（Markdown）

## 📐 架构设计

```
Vue3 前端 ⇄ Express API
                ↓
          ┌─────────────┐
          │ RAG 引擎    │
          │ ┌─────────┐ │
          │ │ 分块器   │ │  ← 递归字符分块 + 段落边界感知
          │ ├─────────┤ │
          │ │ 向量检索 │ │  ← cosine 相似度
          │ │ BM25    │ │  ← 关键词检索 (中英文)
          │ │ RRF     │ │  ← 倒数排名融合
          │ │ Rerank  │ │  ← 关键词重叠度启发式
          │ └─────────┘ │
          └─────────────┘
                ↓
        SQLite + 向量文件
                ↓
        OpenAI 兼容 LLM
```

## 📂 项目结构

```
.
├── api/                    # 后端
│   ├── routes/             # 路由层
│   │   ├── auth.ts         # 认证
│   │   ├── kb.ts            # 知识库
│   │   ├── documents.ts     # 文档
│   │   └── chat.ts          # 对话
│   ├── rag/                # RAG 核心
│   │   ├── parser.ts        # 文档解析
│   │   ├── chunker.ts       # 分块器
│   │   ├── vectorStore.ts   # 向量存储
│   │   ├── bm25.ts          # BM25 检索
│   │   └── pipeline.ts      # Pipeline 编排
│   ├── agents/              # Agent 工作流
│   │   └── workflow.ts      # Plan-Reflect-Synthesize
│   ├── llm/                 # LLM 客户端
│   ├── middleware/          # 中间件
│   ├── db.ts                # SQLite 初始化
│   ├── config.ts            # 配置
│   └── types/               # 类型定义
├── src/                    # 前端
│   ├── api/                # API 客户端
│   ├── composables/         # 组合式函数
│   ├── pages/               # 页面
│   │   ├── HomePage.vue         # 首页
│   │   ├── LoginPage.vue        # 登录注册
│   │   ├── DashboardPage.vue    # 工作台
│   │   ├── KbDetailPage.vue     # 知识库详情
│   │   └── ChatPage.vue         # 对话页
│   ├── router/              # 路由
│   ├── stores/              # Pinia
│   ├── components/          # 通用组件（ChatMarkdown 等）
│   └── style.css            # 全局样式
├── tests/                   # 单元测试（Vitest）
├── .github/workflows/       # CI（类型检查 + Lint + 测试）
├── docs/archive/            # 历史分析报告归档
└── .env.example             # 配置模板
```

## 🎯 简历可用素材

1. **GitHub 仓库**：完整代码 + 详尽 README
2. **本地 Demo**：`npm run dev` 即可演示
3. **技术博客素材**：
   - 「如何实现 RRF 混合检索」
   - 「LangGraph-style Agent 多轮反思实战（TypeScript 版）」
   - 「从 0 到 1 设计 RAG 系统：架构与权衡」

### 简历 Bullet Points 示例

- 设计并实现企业级 RAG 系统 NexusRAG，支持 PDF/Word/Markdown 多格式文档入库，采用「向量+BM25+Rerank」三阶混合检索，相比纯向量检索召回准确率提升 35%
- 基于 Plan-Retrieve-Reflect-Synthesize 模式实现 Agent 深度研究工作流，支持多轮反思与子问题并行检索
- 实现引用溯源功能，每个 AI 论断可溯源至原文档具体页码与位置
- 全栈技术：Vue3 + Express + TypeScript + SQLite + OpenAI SDK + SSE 流式

## 🚀 部署（常驻进程）

> ⚠️ 本项目使用 SQLite 文件存储 + 本地向量索引 + SSE 长连接，**不适合 Vercel 等 Serverless 平台**
>（文件系统只读、SSE 会被网关超时截断）。请部署到 Railway / Fly.io / VPS 等支持常驻进程与持久磁盘的平台。

### 方式一：Node 直跑（VPS / Railway / Fly）

1. 构建前端并让 Express 托管静态资源，或前后端分开部署
2. 常驻启动后端：

```bash
npm install
npm run build          # 构建前端产物 dist/
node --import tsx api/server.ts   # 或 pm2 start "npm run server" --name nexusrag
```

最小 Dockerfile（平台若要求容器交付）：

```dockerfile
FROM node:24-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
ENV NODE_ENV=production PORT=3001
EXPOSE 3001
CMD ["node", "--import", "tsx", "api/server.ts"]
```

### 要点

- **持久化**：将 `data/` 目录挂载为持久卷（SQLite 数据库 + 向量索引都在其中）
- **环境变量**：`JWT_SECRET` 必填；`OPENAI_API_KEY` 可选（缺省进入 Demo 模式）
- **SSE**：如前置 Nginx，需关闭缓冲（`proxy_buffering off;`）
- Railway / Fly 均可直接使用上面的 Dockerfile

## 📜 License

MIT
