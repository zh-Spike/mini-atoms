# mini-atoms

一个 [Atoms](https://atoms.dev/) 风格的 AI 应用生成平台 Demo：用一句话描述想要的应用，一支由 AI 智能体组成的软件团队（产品经理、架构师、工程师、测试）协作完成需求梳理、架构设计、编码和检查，生成的 React 应用在浏览器里实时运行，并可以继续用对话迭代、手动改代码、回滚版本。

## 功能

| 能力 | 说明 |
| --- | --- |
| 邀请码访问 | 输入邀请码后签发会话 Cookie；每个邀请码有使用次数上限，每个访客有生成次数上限，用于控制模型成本 |
| 多智能体流水线 | Emma 写 PRD，Bob 做架构和文件规划，Alex 写代码，Quinn 做静态检查；发现问题时 Alex 自动修复一轮 |
| 流式过程可视化 | 每个角色的思考过程、发言、正在写的文件和代码实时推送；顶部有流水线进度条 |
| 实时预览 | 生成的多文件 React 项目在 Sandpack 沙箱中编译运行，和主站隔离 |
| 多轮迭代 | 有应用后再发消息，由 Mike（团队负责人）判断是"在现有应用上修改"还是"推倒重做"；修改只输出变更文件，再合并成新版本 |
| 版本历史 | 每次 AI 生成、手动编辑、回滚都生成新版本，可以随时查看任意历史版本并回滚 |
| 在线改代码 | 在"代码"页签直接编辑，预览实时刷新，可保存为新版本 |
| 一键修复 | 预览运行报错时，点击"让 Alex 修复"会把报错信息交给工程师 |
| 数据持久化 | 访客、项目、对话、版本全部存入 Postgres（生产用 Neon，本地用 SQLite）；生成的应用自身数据存在 localStorage |

## 架构

```
浏览器 (React SPA)                         FastAPI
┌──────────────────────────┐   JSON       ┌───────────────────────────────┐
│ 邀请码页 / 项目列表 / 工作台 │ ──────────▶ │ /api/auth  /api/projects       │
│                          │   NDJSON 流   │ /api/projects/{id}/messages   │
│ 对话 + Agent 时间线        │ ◀────────── │   └─ Agent Pipeline           │
│ Sandpack 预览 / 代码编辑    │              │      Mike → Emma → Bob        │
└────────────┬─────────────┘              │      → Alex → QA (→ Alex 修复) │
             │ 跨域 iframe                  └──────┬───────────────┬────────┘
             ▼                                     │               │
     Sandpack bundler                       OpenAI 兼容 LLM    Postgres / SQLite
```

- 后端 `app/`：FastAPI + SQLAlchemy。`app/agents/` 是智能体核心，包括流式文件解析器 `parser.py`、静态检查 `qa.py`、各角色提示词 `prompts.py` 和编排器 `pipeline.py`。
- 前端 `web/`：Vite + React + TypeScript + Tailwind。构建产物由 FastAPI 同源托管，所以不需要处理跨域，Cookie 鉴权也最简单。

## 实现思路与关键取舍

1. **产物形态：多文件 React 项目 + Sandpack 预览。** 参考了几个开源实现：
   - bolt.diy 用 WebContainer 在浏览器里跑完整 Node 环境，但用于商业生产需要授权，体积也重。
   - E2B / Open Lovable 用云端沙箱，需要额外的付费服务和接入。
   - LlamaCoder 只生成单个组件。

   Sandpack 能在浏览器里编译多文件 React 项目，不需要服务端算力，预览运行在跨域 iframe 中，天然和主站隔离。代价是只支持纯前端应用、依赖需要白名单。
2. **输出协议：流式 `<file path>` 标签。** 借鉴 bolt.diy，模型按 `<file path="/App.js">...</file>` 输出，后端边收边解析，按文件推送事件，前端可以展示"工程师正在写哪个文件"。模型偶尔不遵守格式，因此做了三层兜底：
   - 用户消息末尾附格式示例；
   - 解析 Markdown 代码块并从上下文推断文件名；
   - 仍然没有文件时，带纠正提示自动重试一次。
3. **流式传输用 NDJSON 而不是 SSE。** 发消息的 POST 请求直接返回事件流，前端用 `fetch` + `ReadableStream` 读取。比"先 POST 再开 EventSource"少一次往返，服务端也不需要暂存运行状态。前端每帧最多渲染一次，扛得住每秒上千个代码增量事件。
4. **QA 用确定性静态检查，不调用 LLM。** 入口文件、相对引用、依赖白名单、保留文件都用规则检查，又快又稳；发现问题再交给 Alex 修一轮，避免"让 LLM 审 LLM"的成本和不确定性。
5. **迭代时增量修改。** 小改动只让 Alex 输出变更文件，再和上一版本合并，速度快、token 少，也不容易改坏无关代码。
6. **版本是不可变快照。** 回滚 = 复制旧版本生成新版本，历史永远不会丢。
7. **默认关闭模型的思考模式。** 实测 deepseek 系列开启思考时，模型会在思考阶段先把代码草拟一遍，首字延迟达到几十秒；关闭后整体快很多。可以用 `LLM_DISABLE_THINKING=false` 打开。
8. **邀请码而不是注册。** 降低体验门槛，同时用邀请码额度和访客额度控制成本。
9. **不引入 Alembic。** 启动时 `create_all`，Demo 阶段表结构简单，属于有意的复杂度控制。

## 完成度

已完成：

- 邀请码访问、项目管理、多智能体流水线、流式过程展示
- Sandpack 预览、代码编辑、版本历史、回滚、运行报错一键修复
- 后端 22 个测试，覆盖解析器、QA、鉴权、额度、流水线（使用假 LLM）
- CI（后端、前端、Docker 构建）与合并到 main 后自动部署

未完成 / 已知限制：

- 生成的应用只能是纯前端应用，数据存在 localStorage，没有后端和数据库
- 预览依赖 codesandbox.io 的打包服务和 Tailwind CDN，网络受限时可能加载慢
- 单个生成请求在 HTTP 连接内完成；中途刷新页面会中断当前生成（已生成的阶段性结果会保留）
- 没有移动端适配的工作台布局

## 后续路线（按优先级）

1. **后台任务化**：生成任务放进队列，前端断线可以续看；同时为多实例部署做准备
2. **发布分享**：一键生成公开链接 `/s/{slug}`，可以独立访问生成的应用，带浏览量统计
3. **生成应用的后端能力**：给生成的应用注入一个平台 KV / 数据表 SDK，让数据跨设备持久化（对标 Atoms 的 Supabase 集成）
4. **视觉自检**：用无头浏览器截图预览，让 QA 基于截图和运行时日志判断问题
5. **模板广场与 Remix**：公开优秀作品，一键复制再改
6. **按 token 计量**：记录每次运行的 token 用量和耗时，做成本看板

## 本地开发

```bash
# 后端
uv sync
cp .env.example .env   # 填写 LLM_API_KEY
uv run uvicorn app.main:app --reload

# 前端（另开终端，/api 会代理到 8000 端口）
cd web
npm install
npm run dev
```

打开 http://localhost:5173，用 `.env` 里 `INVITE_CODES` 配置的邀请码进入（默认 `DEMO`）。

## 检查

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
cd web && npm run lint && npm run typecheck && npm run build
```

## 部署

```
feature 分支 -> PR -> CI（后端检查、前端检查、Docker 构建）-> squash merge 到 main
  -> main 上 CI 通过 -> Deploy：构建并推送 ghcr.io 镜像 -> SSH 到服务器
  -> docker compose pull && up -d -> 通过 HTTPS 做健康检查（/healthz、SPA 首页、未登录 /api/auth/me 返回 401）
```

- 线上地址：https://43-161-240-115.sslip.io 。[sslip.io](https://sslip.io) 把 IP 形式的子域名解析回这个 IP，从而不用买域名也能申请证书。直接用 IP 的 HTTP 访问仍然可用，作为兜底。
- `docker-compose.yml` 包含两个服务：`web`（应用，只在内部网络暴露 8000 端口）和 `caddy`（监听 80/443 的反向代理）。Caddy 会为 `SITE_ADDRESS` 自动申请并续期 Let's Encrypt 证书，证书保存在 `caddy_data` 卷里。
- 必须用 HTTPS 的原因：浏览器只在安全上下文（HTTPS 或 localhost）里提供 `crypto.subtle` 等 API，Sandpack 依赖这些 API；前端对 HTTP 环境也做了兼容补丁。
- `Dockerfile` 是多阶段构建：先用 Node 构建前端，再把 `web/dist` 拷贝进 Python 镜像，由 FastAPI 托管。
- 运行时配置在 GitHub `production` 环境中管理，每次部署写入服务器的 `/opt/mini-atoms/.env`（权限 600）。任何一项缺失，部署都会在重启服务之前失败。
  - secrets：`DATABASE_URL`、`LLM_API_KEY`、`SECRET_KEY`、`INVITE_CODES`
  - variables：`LLM_BASE_URL`、`LLM_MODEL`、`SITE_ADDRESS`（HTTPS 域名，如 `43-161-240-115.sslip.io`）
  - 修改方式：在 *Settings → Environments → production* 中更新，然后重新运行 *Deploy*。新增配置项时，还需要加到 deploy 工作流的 *Upload runtime config* 步骤。
- 服务器防火墙需要放行 TCP 80、443（Caddy 申请证书和提供 HTTPS 都需要）。
- 部署权限：仓库 variable `DEPLOY_HOST`；仓库 secrets `DEPLOY_USER`、`DEPLOY_SSH_KEY`、`DEPLOY_KNOWN_HOSTS`。
- 回滚：*Actions → Deploy → Run workflow*，填入旧的 commit SHA。只能部署已经在 `main` 上的提交。
- `production` 环境及其 secrets 只对 `main` 分支开放，第三方 Action 都固定到 commit SHA。
