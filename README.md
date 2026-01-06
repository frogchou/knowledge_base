# 知识库系统

基于 FastAPI + MySQL + Qdrant 的个人/团队知识库，支持文本、链接、文件入库，并通过可插拔的大模型提供摘要、关键词、标签和向量化语义检索。项目提供 REST API 与简易 Web 管理界面，支持 Docker Compose 一键启动，默认使用 Mock LLM/Embedding 提供离线可运行体验。

## 功能特点
- 用户注册/登录，JWT 鉴权；配置允许匿名只读访问。
- 知识条目 CRUD，按内容哈希去重，删除同步清理 Qdrant 向量。
- 统一入库流水线：内容抽取 → 摘要/关键词/标签生成 → Embedding → Qdrant 建索引。
- 检索能力：关键词/标签过滤、MySQL 全文/LIKE 搜索、Qdrant 语义检索（含相似度分数）。
- 支持文本、URL 抓取（保留原始 HTML）、文件上传（PDF/DOCX 提取文本并保存原文件）。
- 简易 Web 界面（Jinja2 渲染）：入库、列表、详情、编辑、删除。

## 目录结构
```
knowledge_base/
├── app/
│   ├── main.py                # FastAPI 入口
│   ├── core/                  # 配置、日志、安全与依赖注入
│   ├── db/                    # SQLAlchemy 会话与模型
│   ├── alembic/               # 数据库迁移
│   ├── api/v1/                # REST 路由（认证、条目、搜索）
│   ├── services/              # 入库流水线、抽取、存储与向量索引
│   ├── llm/providers/         # Mock 与 OpenAI Provider
│   ├── ui/                    # Web 界面路由与模板
│   ├── templates/             # Jinja2 模板
│   ├── static/                # 静态资源
│   └── tests/                 # 基础用例
├── docker/                    # Dockerfile 等
├── docker-compose.yml         # 一键启动编排
├── requirements.txt
├── .env.example               # 环境变量模板
└── README.md
```

## 快速开始（Docker Compose）
1. 复制环境变量模板并按需修改：
   ```bash
   cp .env.example .env
   ```
2. 启动服务（FastAPI + MySQL + Qdrant）：
   ```bash
   docker compose up -d --build
   ```
   - API 默认端口：`9981`
   - MySQL：`33066`
   - Qdrant：`6333`
3. API 文档与界面入口：
   - Swagger: http://localhost:9981/docs
   - Web 登录: http://localhost:9981/ui/login
   - 列表页: http://localhost:9981/ui/items

> 提示：API 容器启动时会自动执行 `alembic upgrade head` 迁移，挂载的 `/data/uploads` 用于保存上传文件与原始 HTML。当前 docker-compose 将上传文件、MySQL 数据与 Qdrant 数据映射到项目下的 `volume/` 目录。

## 配置说明
下表列出 `.env` 所有配置项及说明（示例值可参考 `.env.example`）：

| 变量名 | 说明 | 示例/默认值 |
| --- | --- | --- |
| `DATABASE_URL` | MySQL 连接串，支持同步/异步驱动（用于 Alembic 与运行时）。 | `mysql+aiomysql://kb:kbpass@mysql:33066/kb` |
| `QDRANT_URL` | Qdrant 服务地址。 | `http://qdrant:6333` |
| `QDRANT_API_KEY` | Qdrant API 密钥（未启用鉴权可留空）。 | 空 | 
| `EMBEDDING_DIM` | 向量维度，需与 Qdrant collection 配置一致。 | `1536` |
| `JWT_SECRET` | JWT 加密密钥，必须修改为强随机值。 | `supersecret` |
| `JWT_EXPIRE_MINUTES` | Access Token 过期时间（分钟）。 | `60` |
| `ALLOW_ANONYMOUS_READ` | 是否允许未登录用户进行查询/检索（`true`/`false`）。 | `true` |
| `UPLOAD_DIR` | 上传文件与网页原始 HTML 的持久化目录。 | `/data/uploads` |
| `OPENAI_API_KEY` | OpenAI Key，留空则自动使用 MockProvider。 | 空 |
| `OPENAI_MODEL` | 使用的 OpenAI 模型名称。 | `gpt-3.5-turbo` |
| `auth__admin_username` | 启动时创建的内置管理员用户名。 | `admin` |
| `auth__admin_password` | 启动时创建的内置管理员密码。 | `adminpass` |

> 提示：当 `OPENAI_API_KEY` 为空时，系统默认使用 MockProvider，在离线环境也能完整跑通全流程。

## 本地开发
1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
2. 本地运行（需先启动 MySQL/Qdrant 或使用 docker-compose）：
   ```bash
   uvicorn app.main:app --reload
   ```
3. 手动迁移（若未通过容器自动迁移）：
   ```bash
   alembic upgrade head
   ```

## 运行测试
执行基础测试（需要已配置依赖）：
```bash
pytest
```

## 交互说明
- REST API：以 `/api/v1` 为前缀；统一响应格式 `{ "success": true/false, ... }`。
- Web UI：登录后可进行条目创建、编辑、删除与查看；匿名访问的开关由配置控制。

## 未来计划
- 开放添加知识的 API：提供 API Key、限流/配额、审计与使用统计，面向第三方系统稳定接入。
- 增加多种检索模式，包括关键字全文检索、向量检索、标签检索。
- 批量入库与异步任务：支持大批量 URL/文件导入，提供进度与失败重试。
- 内容分块与增量更新：长文档分块检索、增量更新与重建向量索引策略。
- 更多数据源与格式：Markdown/HTML、图片 OCR、音频转写、浏览器插件采集等。
- 团队与权限体系：空间/项目、多角色权限、共享与协作。
- UI 完善：高级搜索/筛选、标签管理、数据导出与可视化面板。

## 常见问题
- **没有 OpenAI Key 也能跑吗？** 可以，默认使用 MockProvider 生成摘要/关键词/标签与伪造向量。
- **重复内容如何处理？** 同一用户内容哈希相同则拒绝入库，可通过 `force=true` 参数覆盖。
