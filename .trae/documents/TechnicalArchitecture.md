# NexusRAG 智能知识库 - 技术架构文档

## 1. 架构设计

```mermaid
flowchart TB
    subgraph Frontend["前端层"]
        VUE["Vue3 + TS + Tailwind"]
    end
    subgraph Backend["后端层 (Express + TS)"]
        API["API 路由层"]
        SVC["服务层"]
        RAG["RAG 核心引擎"]
        AGENT["Agent 工作流"]
    end
    subgraph Data["数据层"]
        SQLITE["SQLite (元数据)"]
        VEC["纯 JS 向量检索（cosine 相似度，线性扫描）"]
        REDIS["内存缓存"]
    end
    subgraph External["外部服务"]
        LLM["OpenAI / 兼容 LLM"]
        EMB["OpenAI Embeddings"]
    end

    VUE <-->|HTTP/WebSocket| API
    API --> SVC
    SVC --> RAG
    SVC --> AGENT
    RAG --> VEC
    RAG --> EMB
    AGENT --> LLM
    RAG --> LLM
    SVC --> SQLITE
    SVC --> REDIS
```

## 2. 技术说明

### 前端
- **框架**：Vue 3.4 + TypeScript 5 + Vite 5
- **路由**：vue-router 4
- **样式**：Tailwind CSS 3 + 自定义 CSS 变量
- **状态**：Pinia
- **HTTP**：axios + 拦截器
- **UI 组件**：Naive UI（轻量、TypeScript 友好）
- **Markdown**：markdown-it + highlight.js + KaTeX
- **图标**：lucide-vue-next
- **流式**：XHR onprogress 渐进解析 SSE（兼容 webview；fetch + ReadableStream 在部分 webview 中会 ERR_ABORTED）

### 后端
- **框架**：Express 4 + TypeScript 5
- **路由**：express.Router 模块化
- **数据库**：SQLite (node:sqlite，Node 22+ 内置，无需原生编译)
- **向量库**：纯 JS 向量检索（cosine 相似度，线性扫描，文件持久化）
- **文档解析**：
  - PDF：pdf-parse
  - Word：mammoth
  - Markdown：marked
  - 纯文本：原生
- **LLM 调用**：openai SDK（兼容 OpenAI 协议的任意服务）
- **流式响应**：Server-Sent Events (SSE)
- **认证**：JWT (jsonwebtoken) + bcrypt
- **文件上传**：multer
- **校验**：zod

### 工程化
- **包管理**：pnpm（如可用）/ npm
- **代码规范**：ESLint + Prettier
- **测试**：Vitest（已配置）
- **构建**：Vite（前端）+ tsx（后端运行）

## 3. 路由定义

### 前端路由

| 路由 | 用途 |
|------|------|
| `/` | 首页（项目介绍） |
| `/login` | 登录注册 |
| `/dashboard` | 工作台（知识库列表） |
| `/kb/:id` | 知识库详情（文档管理） |
| `/chat/:kbId` | 对话页（指定知识库） |
| `/chat/:kbId/:sessionId` | 对话页（指定会话） |

## 4. API 定义

### 4.1 认证相关
```typescript
POST   /api/auth/register    // 注册
POST   /api/auth/login       // 登录
GET    /api/auth/me          // 获取当前用户
```

### 4.2 知识库
```typescript
GET    /api/kb               // 列表
POST   /api/kb               // 创建
DELETE /api/kb/:id           // 删除
GET    /api/kb/:id           // 详情
```

### 4.3 文档
```typescript
POST   /api/kb/:id/documents        // 上传文档（multipart）
GET    /api/kb/:id/documents         // 文档列表
DELETE /api/kb/:id/documents/:docId  // 删除文档
GET    /api/kb/:id/documents/:docId/status  // 处理状态
```

### 4.4 对话
```typescript
POST   /api/chat/:kbId/sessions        // 创建会话
GET    /api/chat/:kbId/sessions         // 会话列表
POST   /api/chat/:kbId/sessions/:sid/messages  // 发送消息（SSE 流式）
GET    /api/chat/:kbId/sessions/:sid/messages  // 消息历史
```

### 4.5 请求/响应 Schema 示例

```typescript
// 发送消息请求
interface ChatRequest {
  content: string;
  mode: 'normal' | 'agent';  // 普通 RAG / Agent 深度研究
  topK?: number;
}

// 流式响应（SSE 事件）
interface StreamChunk {
  type: 'token' | 'citation' | 'done' | 'error';
  data: {
    content?: string;          // 文本片段
    citations?: Citation[];   // 引用列表
    error?: string;
  };
}

interface Citation {
  id: number;
  docId: string;
  docName: string;
  content: string;     // 原文片段
  page?: number;       // 页码（PDF）
  score: number;       // 相关度
}
```

## 5. 服务器架构图

```mermaid
flowchart LR
    Router["路由层 Router"] --> Controller["控制器 Controller"]
    Controller --> Service["服务层 Service"]
    Service --> Repo["数据访问层 Repository"]
    Repo --> DB[("SQLite (node:sqlite)")]
    Service --> RAG["RAG 引擎"]
    RAG --> Vec[("纯 JS 向量库")]
    RAG --> Embed["Embedding API"]
    RAG --> LLM["LLM API"]
    Service --> Agent["Agent 工作流"]
    Agent --> RAG
```

## 6. 数据模型

### 6.1 ER 图

```mermaid
erDiagram
    User ||--o{ KnowledgeBase : owns
    KnowledgeBase ||--o{ Document : contains
    KnowledgeBase ||--o{ ChatSession : has
    ChatSession ||--o{ ChatMessage : contains
    Document ||--o{ Chunk : "split into"

    User {
        string id PK
        string email UK
        string password_hash
        string name
        datetime created_at
    }
    KnowledgeBase {
        string id PK
        string user_id FK
        string name
        string description
        int document_count
        datetime created_at
    }
    Document {
        string id PK
        string kb_id FK
        string name
        string file_type
        int file_size
        string status
        int chunk_count
        datetime created_at
    }
    Chunk {
        string id PK
        string doc_id FK
        int chunk_index
        text content
        string vector_id
        int token_count
    }
    ChatSession {
        string id PK
        string kb_id FK
        string user_id FK
        string title
        string mode
        datetime created_at
    }
    ChatMessage {
        string id PK
        string session_id FK
        string role
        text content
        json citations
        datetime created_at
    }
```

### 6.2 DDL（SQLite）

```sql
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  name TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS knowledge_bases (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  description TEXT,
  document_count INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  kb_id TEXT NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  file_type TEXT NOT NULL,
  file_size INTEGER,
  status TEXT DEFAULT 'pending',
  chunk_count INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chunks (
  id TEXT PRIMARY KEY,
  doc_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  content TEXT NOT NULL,
  vector_id TEXT NOT NULL,
  token_count INTEGER,
  metadata TEXT
);

CREATE TABLE IF NOT EXISTS chat_sessions (
  id TEXT PRIMARY KEY,
  kb_id TEXT NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id),
  title TEXT,
  mode TEXT DEFAULT 'normal',
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  citations TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_documents_kb ON documents(kb_id);
CREATE INDEX IF NOT EXISTS idx_sessions_kb ON chat_sessions(kb_id);
CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id);
```
