# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式；
版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)。

## [Unreleased] — 2026-08 全面优化

对 nexus-rag 主项目与 ai-analytics-workbench 子项目进行系统性代码审计后，
按六轮计划执行的质量 / 性能 / 架构 / 安全优化。

### 新增

- **文档摄取服务层**：`api/services/ingestion.ts`，上传解析全局串行化，防止并发摄取拖垮事件循环
- **认证限流**：登录/注册接入每 IP 滑动窗口限流（10 次/分钟），超限返回 429
- **Refresh Token**：`POST /auth/refresh` 端点；登录/注册签发 access+refresh 双 token（类型隔离，
  refresh 不能访问业务 API）；前端 401 单飞自动刷新并重放原请求
- **JWT 吊销预留**：payload 增加 `jti`
- **图表认证下发端点**：`GET /analyses/{id}/chart`（归属校验 + 路径白名单双重防遍历），
  替代原匿名静态挂载
- **列表分页**：datasets / analyses / reports 列表端点支持 `limit`(1–500)/`offset`
- **图表保留期清理**：启动时按 `CHART_RETENTION_DAYS`（默认 30，0 禁用）回收过期工件
- **生产环境配置守卫**：强制非默认 `SECRET_KEY` 与非弱口令 `DATABASE_URL`；`/auth/demo` 生产禁用
- 测试基建：WS 全链路测试（此前零覆盖）、图表 IDOR 回归、refresh 流、NULL 属主策略、
  限流行为、NaN 序列化、主项目前端单测（useMarkdown / cn / params）

### 变更

- JWT access 默认有效期 **7 天 → 12 小时**
- 数据库时间列统一为 `timestamptz`（迁移 0004，存量数据按 UTC 语义转换），模型默认值改用 aware UTC
- 上传路由同步化（线程池执行）并在读取前预检大小；`to_sql` 按列数自适应 `chunksize`
  （规避 PG 65535 绑定参数上限）
- LLM 客户端显式 60s 超时；仅对连接/超时/限流类瞬时错误重试
- 日志：保留字段自动推导、human 格式单行化防注入、JSON 输出禁 NaN
- 删除数据集顺序调整：先提交元数据删除、后尽力 drop 物理表
- 图表文件名带时间戳，重跑分析不再覆盖旧图
- 主项目构建：路由级代码分割 + highlight.js 按需注册（首屏 1236KB → 153KB，gzip 59KB）
- workbench 前端 echarts 改按需引入；tsconfig 开启 `noUnusedLocals/noUnusedParameters`

### 修复

- **WS 进度推送链路断裂（P1）**：路由误挂 `/api/v1` 前缀致前端 `/ws/...` 永远 404，改为应用根路径挂载；
  会话改依赖注入以打通测试
- BM25 缓存被每条聊天消息清除导致全量重建（性能）
- chunker 句读正则 `/g` 状态缺陷隐患与 `overlap≥chunkSize` 死循环边界
- rerank 中文失效（空白分词 → BM25 tokenize）
- 入库 vector_id 与向量库实际位置不一致
- SSE 客户端断连后写入已结束连接；消息同秒排序不稳定（rowid 决胜）
- 占位表名唯一约束连锁瘫痪上传（随机占位名 + 补偿事务）
- 日期列 Timestamp 不可序列化导致含日期列的数据集分析必败
- matplotlib figure 异常路径泄漏；WeasyPrint 外链抓取 SSRF（仅放行本地资源）
- 沙箱 `np.load(allow_pickle=True)` 反序列化逃逸路径封堵
- NaN/Infinity 写出非法 JSON；注册并发竞态 500（IntegrityError→409）；邮箱大小写归一化
- NULL 属主遗留行越权写/删/"认领"报告（过渡期改为只读，管理员除外）
- workbench 前端 WS 连接/轮询定时器/ECharts 实例三重生命周期泄漏；
  v-if 重建容器后图表绑定 detached DOM 导致第二次分析空白
- Redis 发布失败拖垮任务（降级告警）、订阅循环断线静默死亡（指数退避重连）、
  Celery worker 崩溃后任务永久卡 running（acks_late + 终态幂等跳过）
- 主项目 vitest 在 Windows 多进程下的共享目录 EPERM 竞态（按 PID 隔离）
- 上传越权时 multer 孤儿临时文件泄漏

### 移除

- 匿名静态目录挂载（`/reports`、`/uploads`）
- 双轨重复测试 3 个文件、未使用依赖 naive-ui / vue-echarts、误入库的构建产物
  （`vite.config.js|.d.ts`、`*.tsbuildinfo`）、死代码（`get_current_user_optional`、`pragma` 代理等）

### 安全

详见上方"新增/修复"中的认证、IDOR、SSRF、沙箱条目；完整清单见
`docs/OPTIMIZATION_REPORT.md`。
