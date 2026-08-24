> ⚠️ **历史快照（2026-07-21）**：本文档为当时的项目分析存档，多项问题已在后续版本修复，勿作为现状依据。最新情况以 README 与代码为准。
# NexusRAG 智能知识库 — 完善程度分析报告

> **项目路径**：`e:\code\新建文件夹`（根目录下的 NexusRAG 项目，不含 `ai-analytics-workbench` 子目录）
> **技术栈**：Express + node:sqlite + 纯 JS 向量库 + SSE + Vue3 + markdown-it + JWT
> **分析时间**：2026-07-21
> **综合评分**：**7.4 / 10**（完成度高、可演示、但工程化细节欠打磨的简历级项目）

---

## 一、总体概览

| 维度 | 量化指标 |
|------|----------|
| 后端代码规模 | 14 个 TypeScript 文件，约 1,650 行 |
| 前端代码规模 | 16 个文件，约 1,400 行 |
| 后端分层目录 | 6 个（routes / rag / llm / agents / middleware / types） |
| 前端子目录 | 6 个（api / pages / stores / router / composables / lib） |
| 入口点 | 3 个清晰分离（`index.ts` Vercel handler、`server.ts` 本地开发、`app.ts` Express 实例） |
| 后端 routes | 4 个（auth / chat / documents / kb） |
| RAG 引擎模块 | 5 个（bm25 / chunker / parser / pipeline / vectorStore） |
| Agent 工作流 | 1 个（Plan-Retrieve-Reflect-Synthesize，最多 3 轮反思） |
| 前端页面 | 5 个（Home / Login / Dashboard / KbDetail / Chat） |
| TODO/FIXME | **0 个**（源码极干净） |
| `any` 类型使用 | 10 处 |
| `console.*` 调用 | 22 处 |
| 空 catch 块 | 5 处 |
| 测试文件数 | **0** |
| CI/CD 配置 | **无** |
| ESLint 配置 | **装了依赖但无配置文件** |
| TypeScript strict | **关闭** |
| 数据库迁移机制 | **无** |
| 版本控制 | ✅ 是 git 仓库 |

---

## 二、项目架构完整性 — 评分 8.5 / 10

### 量化指标

| 指标 | 数值 |
|---|---|
| 后端源文件数 | 14 个 `.ts` 文件 |
| 前端源文件数 | 16 个 |
| 配置文件 | 9 个（package.json、tsconfig.json、vite.config.ts、vercel.json、nodemon.json、tailwind.config.js、postcss.config.js、.env.example、.gitignore） |
| 后端分层目录 | 6 个 |
| 入口点 | 3 个清晰分离 |

### 定性描述

**优点：**
- **入口点分离清晰**：`api/index.ts` 专用于 Vercel Serverless（导出 handler），`api/server.ts` 用于本地开发（含 SIGTERM/SIGINT 优雅关闭），`api/app.ts` 仅组装 Express 应用，三者职责分明
- **后端分层标准**：`routes → rag/llm/agents → db`，每层不越界。`routes` 不直接操作向量库，`rag` 不直接处理 HTTP，`agents` 编排 `rag` 与 `llm`
- **前端结构规范**：`api/` 封装 HTTP、`stores/` 管理全局状态、`composables/` 复用逻辑、`pages/` 路由级组件、`router/` 路由守卫、`lib/utils.ts` 工具函数，符合 Vue3 最佳实践
- **类型集中管理**：`api/types/index.ts` 统一定义后端共享类型（User / KB / Document / Chunk / Citation / StreamChunk 等），前端 `src/api/types.ts` 镜像
- **Vercel 部署就绪**：`vercel.json` 的 rewrites 把 `/api/(.*)` 路由到 `/api/index`，`/.*` 回退到 `index.html`，SPA + API 单仓部署可用

**不足：**
- README 中提到 `src/components/` 目录，但实际不存在——文档与代码漂移
- 后端没有 `services/` 层，部分业务逻辑（如 `chat.ts` 里的会话/消息管理）直接写在路由层
- `api/llm/` 只有 `client.ts` 单文件，未抽出 `prompts/` 模块，prompt 散落在 `pipeline.ts` / `workflow.ts` 字符串里

---

## 三、代码质量与规范遵循 — 评分 6.5 / 10

### 量化指标

| 指标 | 数值 |
|---|---|
| TypeScript `strict` 模式 | ❌ 关闭 |
| `noUnusedLocals` / `noUnusedParameters` | ❌ 均关闭 |
| `any` 类型使用 | 10 处（`db.ts` 7 处、`chat.ts` 2 处、`pipeline.ts` 1 处） |
| `console.*` 调用 | 22 处 |
| 空 catch 块 | 5 处（`auth.ts` 中间件 2 处、`workflow.ts` 2 处、`documents.ts` 1 处） |
| ESLint 配置文件 | ❌ 缺失（有依赖与 lint 脚本，但无配置文件） |
| Prettier 配置 | ❌ 缺失 |
| 文件级 JSDoc 注释 | 14/14 后端文件均有，前端约 60% |
| TODO/FIXME/HACK 注释 | **0 个** |

### 定性描述

**优点：**
- 0 个 TODO/FIXME/HACK 注释，源码没有遗留待办标记，非常干净
- 每个后端文件顶部均有 JSDoc 说明文件用途，命名风格一致（camelCase 函数、PascalCase 类型）
- 路由层普遍使用 Zod schema 校验请求体（`auth.ts`、`kb.ts`），未校验的路由（`chat.ts`、`documents.ts`）有手动类型判断兜底
- SQL 全部使用参数化查询（`prepare().run(...)`），无字符串拼接，无 SQL 注入风险
- 异步路由全部包裹 try/catch，`app.ts` 有兜底的全局错误中间件与 404 处理

**不足：**
- **TypeScript 严格模式关闭**：`strict: false`、`noUnusedLocals: false`、`noUnusedParameters: false`，意味着编译期漏检大量类型问题，这与 README 宣称的「TypeScript 全栈」工程化卖点不符
- **ESLint 形同虚设**：装了 `@typescript-eslint/eslint-plugin` 等依赖但没配置文件，`npm run lint` 实际不会执行任何规则
- **无 Prettier**：代码风格靠人工维持，长期协作风险高
- **`any` 类型 10 处**：主要在 `db.ts` 的代理层，绕过了类型检查；`chat.ts` 中 `send(chunk: any)` 和 `citations: any[]` 应替换为 `StreamChunk` 与 `Citation[]`
- **空 catch 块 5 处**：`auth.ts` 中间件吞掉 JWT 错误（这里是合理的），但 `workflow.ts` 的 `planSubqueries` / `reflect` 解析 JSON 失败时静默回退，应该至少打日志
- **无统一 logger**：22 处 `console.log/error` 直接输出，无日志分级、无文件落盘、生产环境难以管控

---

## 四、功能模块实现进度 — 评分 9.0 / 10

### 量化指标

| 模块 | 文件 | 行数 | 实现度 |
|---|---|---|---|
| **后端 routes** | | | |
| auth.ts | register/login/me/demo | 128 | 100% |
| kb.ts | list/get/create/delete/patch | 107 | 100% |
| documents.ts | list/upload/status/delete | 162 | 100% |
| chat.ts | sessions CRUD + SSE 流式问答 | 190 | 100% |
| **RAG 引擎** | | | |
| parser.ts | PDF/Word/MD/TXT 解析 | 83 | 100% |
| chunker.ts | 递归分块 + 句子边界感知 | 119 | 100% |
| bm25.ts | 中英文分词 + BM25 + 内存索引 | 161 | 100% |
| vectorStore.ts | 纯 JS cosine 检索 + JSON 持久化 | 171 | 100% |
| pipeline.ts | ingestDocument / retrieve / rerank / ragAnswer | 249 | 100% |
| **LLM client** | embed/embedBatch/chatStream/chat + Demo 模式 | 153 | 100% |
| **agents/workflow** | Plan-Retrieve-Reflect-Synthesize | 252 | 100% |
| **middleware/auth** | JWT 签发/校验/可选认证 | 53 | 100% |
| **前端 pages** | | | |
| HomePage.vue | Hero + 特性卡 + 技术栈 + CTA | 240 | 100% |
| LoginPage.vue | 登录/注册切换 + 演示登录 | 146 | 100% |
| DashboardPage.vue | 知识库列表 + 创建 Modal | 164 | 100% |
| KbDetailPage.vue | 文档上传 + 列表 + 状态轮询 | 265 | 100% |
| ChatPage.vue | 会话列表 + 流式消息 + 引用侧滑 | 446 | 100% |
| **SSE 流式通信** | 后端 SSE 头 + 事件流；前端 XHR 渐进式读取 | — | 100% |
| **Markdown 渲染** | markdown-it + highlight.js + `[1][2]` 引用标记转换 | 47 | 100% |

### 定性描述

**优点：**
- **全部核心模块已实现且可用**：4 个路由、5 个 RAG 模块、LLM 客户端、Agent 工作流、5 个前端页面，无任何「占位」代码
- **SSE 流式实现到位**：后端正确设置 `Content-Type: text/event-stream` + `X-Accel-Buffering: no` + `flushHeaders`；前端用 `XMLHttpRequest.onprogress` 渐进式读取 `responseText`（注释说明这是为了兼容 trae-preview/Electron webview，比 `fetch + ReadableStream` 更稳）
- **Agent 工作流真实落地**：`workflow.ts` 实现了完整循环——`planSubqueries` 让 LLM 输出 JSON 子问题，多轮检索 + `reflect` 评估充分性，最多 3 轮反思，最后流式合成报告，不是玩具
- **Demo 模式设计巧妙**：无 `OPENAI_API_KEY` 时自动降级，用确定性哈希生成伪向量保证检索流程跑通，LLM 返回带流式打字机的 mock 文本——面试官一键可体验
- **引用溯源闭环**：`pipeline.toCitations` 生成结构化引用 → 前端 `useMarkdown.renderCitations` 把 `[1]` 替换为可点击 `<span class="citation-ref">` → ChatPage 侧滑面板展示原文 + 页码 + 相关度

**不足：**
- **Rerank 是启发式而非模型**：`pipeline.rerank` 仅用关键词重叠度，注释自承「真实场景应使用 Cohere Rerank 或 BGE Reranker」
- **向量检索是线性扫描**：`vectorStore.search` O(n) 遍历，注释说「演示规模（<10k 向量）够用」，但生产规模需要 HNSW
- **PDF 按页解析不精确**：`parser.parsePdf` 用 `\f` form feed 切页，pdf-parse 对部分 PDF 不输出 `\f`，会丢页码信息
- **没有 WebSocket**：README 与 PRD 暗示 WebSocket，但实际只用了 SSE（这是合理取舍，但与原始设计文档不一致）

---

## 五、测试覆盖率 — 评分 1.0 / 10

### 量化指标

| 指标 | 数值 |
|---|---|
| 测试文件数（`*.test.ts` / `*.spec.ts`） | **0** |
| 测试框架配置（jest.config / vitest.config） | **无** |
| CI/CD 配置（`.github/workflows/`） | **无** |
| 测试依赖（devDependencies） | **无** |
| 测试数据文件 | `test_msg2.json`（1 行，内容为 `{"content":"NexusRAG 用了哪些技术？","mode":"normal"}`，明显是手动调试残留） |
| README 中「已验证功能（冒烟测试通过）」 | 8 条功能手动验证清单（无自动化） |

### 定性描述

**优点：**
- README 列出 8 条「冒烟测试通过」清单，至少说明开发者手动验证过核心流程
- Demo 模式本身就是一种可重复的端到端验证路径

**严重不足：**
- **零自动化测试**：没有单元测试、集成测试、E2E 测试，对于一个宣称「企业级」「工程化实践」的项目是硬伤
- **测试框架未配置**：`TechnicalArchitecture.md` 第 70 行白纸黑字写「测试：Vitest」，但实际根本没装 vitest
- **无 CI/CD**：没有 `.github/workflows/`，没有自动 lint/build/test 流水线，每次提交全靠人工
- **临时测试文件污染仓库**：`test_msg2.json` 应当清理或移入 `scripts/` 目录

---

## 六、文档完整性 — 评分 7.5 / 10

### 量化指标

| 文档 | 行数 | 完整度 |
|---|---|---|
| `README.md` | 172 | 安装/运行/Demo/技术栈/架构图/项目结构/简历素材 全齐 |
| `.trae/documents/PRD.md` | 113 | 含用户角色、功能模块、流程图（mermaid）、UI 设计 |
| `.trae/documents/TechnicalArchitecture.md` | 291 | 含架构图、技术选型、API 定义、ER 图、DDL |
| `.env.example` | 51 | 每个变量均有中文注释，含通义/DeepSeek/Moonshot 配置示例 |
| 代码内 JSDoc | 14/14 后端文件有顶部注释 | 较完整 |
| Swagger/OpenAPI | ❌ 无 | — |
| CHANGELOG | ❌ 无 | — |
| CONTRIBUTING | ❌ 无 | — |

### 定性描述

**优点：**
- README 写得非常专业，不仅有标准的安装/运行，还有「简历 Bullet Points 示例」「技术博客素材」这种面向求职场景的元信息
- PRD 与 TechnicalArchitecture 文档使用 mermaid 流程图、ER 图，DDL 直接对应 `db.ts` 实现
- `.env.example` 比较完善，覆盖了 `config.ts` 读取的全部变量，并给出三家国产 LLM 兼容服务的配置示范

**不足：**
- **文档与实现漂移**（4 处）：
  - `TechnicalArchitecture.md` 写的是 `hnswlib-node`（高性能本地向量索引）和 `better-sqlite3`，但实际代码用的是 **纯 JS 向量库 + JSON 持久化** 和 **node:sqlite**（Node 24 内置）
  - `TechnicalArchitecture.md` 写「测试：Vitest」，实际无测试
  - README 项目结构里列了 `src/components/`，实际无此目录
  - README 提「WebSocket/SSE 实时通信」，实际只有 SSE
- **无 API 文档**：没有 Swagger/OpenAPI，外部协作成本高
- **无 CHANGELOG / CONTRIBUTING**，对开源协作不友好

---

## 七、依赖管理状况 — 评分 7.0 / 10

### 量化指标

| 指标 | 数值 |
|---|---|
| `dependencies` 数量 | 23 个 |
| `devDependencies` 数量 | 24 个 |
| `package-lock.json` | ✅ 存在 |
| `scripts` 数量 | 9 个（`client:dev` / `server:dev` / `dev` / `build` / `preview` / `check` / `lint` / `lint:fix` / `server`） |
| TypeScript 版本 | `~5.3.3`（略保守，最新 5.5+） |
| Vue 版本 | `^3.4.15` |
| Express 版本 | `^4.21.2`（未升级到 5.x） |
| Vite 版本 | `^5.0.12` |
| 未使用依赖 | `naive-ui`、`katex`、`@types/katex`、`@types/marked`（代码中未实际 import） |
| Node 版本要求 | 隐式要求 Node 24+（`node:sqlite`），但 `package.json` 无 `engines` 字段声明 |

### 定性描述

**优点：**
- 依赖版本较新，均使用 `^` 范围，能吃到 patch/minor 更新
- `scripts` 完整覆盖开发、构建、预览、类型检查、lint
- `concurrently` 并发跑前后端 dev server，开发体验好
- 使用 `tsx` 替代 `ts-node` 跑后端，ESM 原生支持，启动快
- `vue-tsc -b` 做类型检查 + Vite build，前端构建链标准

**不足：**
- **未声明 Node 引擎要求**：用了 `node:sqlite`（Node 22+ 实验、Node 24 稳定），但 `package.json` 没有 `engines: { node: ">=22" }`，部署到 Vercel 默认 Node 18/20 会直接报错
- **未使用依赖 4 个**：`naive-ui`、`katex` 等装了但代码里没 import，属于历史选型遗留
- **TypeScript 严格模式关闭**（见维度 2），与「TypeScript 全栈」卖点矛盾
- **ESLint 装了但没配置**（见维度 2）
- **Vercel 部署有坑**：`vercel.json` 只配了 rewrites，没有配 `functions` 内存/超时，SSE 长连接在 Serverless 默认 10 秒超时会被截断，生产不可用

---

## 八、潜在技术债务与安全 — 评分 5.5 / 10

### 量化指标

| 风险类型 | 数量/状况 |
|---|---|
| 源码 TODO/FIXME | 0（干净） |
| 硬编码密钥 | 1 处（`auth.ts:115` 演示账号密码 `'demo123456'`，刻意） |
| JWT secret 硬编码兜底 | 1 处（`config.ts:9` `'nexus-rag-dev-secret-change-in-prod'`） |
| `.env` 是否提交 | ❌ 未提交（✅ 安全） |
| `.gitignore` 是否忽略 `.env` | ❌ **未显式忽略**（仅靠 `*.local` 兜底，风险） |
| `data/` 目录是否提交 | ❌ **已提交**：`nexus.db`、`nexus.db-shm`、`nexus.db-wal`、`uploads/36ba56df-*.md`、`vectors/f71aa941-*.json` 全部进了 git |
| 临时调试文件 | `test_msg2.json`（1 行，应清理） |
| 数据库迁移机制 | ❌ 无（仅 `CREATE TABLE IF NOT EXISTS`，无版本管理） |
| CORS 配置 | `app.use(cors())` 全开，无 origin 白名单 |
| 安全中间件 | 无 `helmet`、无 `express-rate-limit`、无 CSRF 防护 |
| bcrypt salt rounds | 10（合格） |
| 文件上传校验 | ✅ 50MB 限制 + 扩展名白名单（`.pdf/.docx/.doc/.md/.markdown/.txt`） |
| SQL 注入 | ✅ 全部参数化 |
| JWT 过期 | 7d（偏长但可接受） |

### 定性描述

**严重问题：**
1. **`data/` 目录被提交进 git**：包含 SQLite 数据库（含演示用户密码哈希）、上传的文档、向量索引文件。`.gitignore` 完全没有覆盖 `data/`，这是明显的工程化疏漏——既增大仓库体积，又泄露演示账号的 bcrypt 哈希
2. **`.gitignore` 未显式忽略 `.env`**：当前 `.env` 没被提交是运气好，未来任何人填了真实 key 都可能被误提交。应在 `.gitignore` 加 `.env` 与 `.env.local`
3. **JWT secret 硬编码兜底**：`config.ts` 写死 `'nexus-rag-dev-secret-change-in-prod'`，生产环境若忘记设 `JWT_SECRET` 环境变量，会用这个公开的 secret，任何人都能伪造 token。应在缺失 secret 时直接 throw 而不是兜底
4. **CORS 全开**：`app.use(cors())` 允许任意 origin 携带凭证，生产环境应限制为前端域名
5. **无数据库迁移机制**：所有表用 `CREATE TABLE IF NOT EXISTS` 创建，未来加字段只能手动 ALTER 或删库重来。建议引入 `node:sqlite` 配合简单的迁移脚本，或换用 Drizzle/Prisma
6. **无速率限制**：登录接口可被暴力破解，SSE 接口可被滥用消耗 LLM 配额

**一般问题：**
- `test_msg2.json` 是调试残留，应清理
- `index.html` 的 `<title>` 是默认的 `My Trae Project`，应改为 `NexusRAG 智能知识库`
- 5 处空 catch 块吞掉错误（见维度 2）
- `documents.ts:100` 的 `try { fs.unlinkSync(file.path) } catch {}` 完全静默，文件清理失败无人知晓

**优点：**
- SQL 全部参数化，无注入风险
- 密码用 bcrypt（10 轮）哈希，未明文存储
- 文件上传有大小 + 类型双限制
- JWT 中间件实现规范（Bearer 提取 + verify + 错误码 401）
- 演示账号密码虽硬编码但刻意为之，且 README 公开声明

---

## 九、完善度评分汇总

| 维度 | 评分 | 关键词 |
|---|---|---|
| 1. 项目架构完整性 | 8.5 / 10 | 分层清晰、入口分离、Vercel 就绪 |
| 2. 代码质量与规范遵循 | 6.5 / 10 | 0 TODO 但 strict 关闭、ESLint 形同虚设 |
| 3. 功能模块实现进度 | 9.0 / 10 | 全部模块可用、Agent/SSE/引用闭环 |
| 4. 测试覆盖率 | 1.0 / 10 | 零自动化测试、无 CI |
| 5. 文档完整性 | 7.5 / 10 | README 优秀但与技术文档存在漂移 |
| 6. 依赖管理状况 | 7.0 / 10 | 版本较新但 4 个未用依赖、无 engines |
| 7. 技术债务与安全 | 5.5 / 10 | data/ 进 git、CORS 全开、无迁移机制 |
| **总体加权** | **7.4 / 10** | 简历级 demo 完成度高，生产级工程化不足 |

---

## 十、改进建议（按优先级）

### 🔴 P0 必须改进

1. **立刻把 `data/`、`.env`、`*.db*` 加入 `.gitignore` 并从 git 历史清除**（安全 + 卫生）
2. **开启 `tsconfig.json` 的 `strict: true`**，修复暴露的类型问题（已识别 10 处 `any`）
3. **补 ESLint 配置文件**（`.eslintrc.cjs` 或 `eslint.config.js`），让 `npm run lint` 真正生效
4. **引入 Vitest + 至少给 RAG 引擎写单元测试**（`bm25.tokenize`、`chunker.chunkRecursive`、`vectorStore.cosineSimilarity` 都是纯函数，测试成本低收益高）
5. **同步 `TechnicalArchitecture.md` 与实现**：把 `hnswlib-node`/`better-sqlite3` 改为 `node:sqlite` + 纯 JS 向量库，把「Vitest」改为「计划中」或真正引入

### 🟡 P1 应该改进

6. **JWT secret 缺失时 throw 而非兜底**：`config.ts` 移除硬编码默认值，生产环境强制要求 `JWT_SECRET` 环境变量
7. **CORS 限制白名单**：`app.use(cors({ origin: process.env.CORS_ORIGIN?.split(',') }))`
8. **引入统一 logger**：用 pino 或 winston 替换 22 处 `console.*`
9. **加 `helmet` + `express-rate-limit`**：基础安全中间件
10. **补 `package.json` 的 `engines` 字段**：`"engines": { "node": ">=22" }`
11. **清理未使用依赖**：`npm uninstall naive-ui katex @types/katex @types/marked`
12. **清理临时文件**：删除 `test_msg2.json`，修正 `index.html` 的 title

### 🟢 P2 可以改进

13. **配置 Vercel `functions.maxDuration`**：解决 SSE 长连接超时
14. **引入数据库迁移机制**：Drizzle ORM 或简单迁移脚本
15. **Rerank 升级为模型**：接入 Cohere Rerank 或 BGE Reranker
16. **向量检索升级 HNSW**：用 `hnswlib-node` 替换线性扫描
17. **补 Swagger/OpenAPI**：用 `swagger-jsdoc` 自动生成 API 文档
18. **补 LICENSE / CHANGELOG / CONTRIBUTING**

---

## 十一、总评

### 一句话定性

**这是一个「产品功能 100% 可演示、工程化细节 60% 及格」的简历项目**：核心 RAG 链路（混合检索 + Rerank + Agent 反思 + SSE 流式 + 引用溯源）全部真实落地，Demo 模式让面试官零成本体验；但 TypeScript 严格模式关闭、零自动化测试、`data/` 目录进 git、CORS 全开、文档与实现漂移等问题，说明它离「企业级生产系统」还差一截——这恰好是面试时可以坦诚讨论的优化空间。

### 优势

1. **功能 100% 完整**：5 个前端页面、4 个后端路由、5 个 RAG 模块、Agent 工作流、引用溯源、Demo 模式全部落地
2. **架构清晰**：三入口分离、分层不越界、Vercel 部署就绪
3. **源码干净**：0 TODO/FIXME、JSDoc 完整、SQL 参数化
4. **有完整认证**：JWT + bcrypt + 中间件
5. **文档双轨**：README + PRD + TechnicalArchitecture 三件套
6. **求职友好**：README 含简历素材、技术博客素材

### 不足

1. **零自动化测试 + 零 CI**：最大硬伤
2. **TS strict 关闭 + ESLint 形同虚设**：与「TypeScript 全栈」卖点矛盾
3. **`data/` 进 git + .gitignore 漏 .env**：工程化疏漏
4. **JWT secret 硬编码兜底 + CORS 全开**：生产级安全风险
5. **文档与实现漂移 4 处**：技术文档失真
6. **无数据库迁移**：schema 演进困难

### 改进路径

- 补齐 P0 项（gitignore + strict + ESLint + Vitest + 文档同步）→ 评分可达 **8.4 / 10**
- 再补齐 P1 项（JWT secret + CORS + logger + helmet + engines + 依赖清理）→ 评分可达 **9.0 / 10**
- 补齐 P2 项（Vercel 超时 + 迁移 + Rerank 模型 + HNSW + Swagger）→ 评分可达 **9.5 / 10** 的企业级水准

---

## 十二、关键文件路径索引

| 用途 | 路径 |
|---|---|
| 项目根 | `e:\code\新建文件夹` |
| 后端入口（Vercel） | `api/index.ts` |
| 后端入口（本地） | `api/server.ts` |
| Express 应用 | `api/app.ts` |
| 配置 | `api/config.ts` |
| 数据库 | `api/db.ts` |
| 类型定义 | `api/types/index.ts` |
| 认证中间件 | `api/middleware/auth.ts` |
| 路由 | `api/routes/{auth,chat,documents,kb}.ts` |
| RAG 引擎 | `api/rag/{bm25,chunker,parser,pipeline,vectorStore}.ts` |
| LLM 客户端 | `api/llm/client.ts` |
| Agent 工作流 | `api/agents/workflow.ts` |
| 前端入口 | `src/main.ts` |
| 前端路由 | `src/router/index.ts` |
| 前端页面 | `src/pages/{Home,Login,Dashboard,KbDetail,Chat}Page.vue` |
| 前端状态 | `src/stores/{auth,kb}.ts` |
| 前端复用 | `src/composables/{useMarkdown,useTheme}.ts` |
| PRD 文档 | `.trae/documents/PRD.md` |
| 技术架构文档 | `.trae/documents/TechnicalArchitecture.md`（与实现漂移，需同步） |
| 部署配置 | `vercel.json`（需补 functions 超时） |
| 待清理 | `test_msg2.json`、`data/`（应 untrack）、`index.html`（title） |
| 待修正配置 | `tsconfig.json`（开 strict）、`.gitignore`（加 data/ .env *.db*）、`package.json`（加 engines） |
