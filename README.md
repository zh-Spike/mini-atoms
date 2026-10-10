# mini-atoms

一个 [Atoms](https://atoms.dev/) 风格的 AI 应用生成平台 Demo：用一句话描述想要的应用，一支由 AI 智能体组成的软件团队（产品经理、架构师、工程师、测试）协作完成需求梳理、架构设计、编码和检查，生成的 React 应用在浏览器里实时运行，并可以继续用对话迭代、手动改代码、回滚版本。还可以开启 Race 让两个工程师并行写出两版方案对比择优，满意后一键发布成公开链接分享给别人。

## 功能

| 能力 | 说明 |
| --- | --- |
| 邀请码注册 + 账号登录 | 凭邀请码注册账号（用户名 + 密码），之后用账号登录；项目和生成额度都归属账号，换设备也能访问。每个邀请码有注册次数上限，每个账号有生成次数上限，用于控制模型成本 |
| 多智能体流水线 | Emma 写 PRD，Bob 做架构和文件规划，Alex 写代码，Quinn 做静态检查；发现问题时 Alex 自动修复一轮 |
| 流式过程可视化 | 每个角色的思考过程、发言、正在写的文件和代码实时推送；顶部有流水线进度条 |
| 实时预览 | 生成的多文件 React 项目在 Sandpack 沙箱中编译运行，和主站隔离 |
| Race 模式 | 对标 Atoms 的 Race：打开 Race 后勾选 2-3 个参赛模型（默认可选 deepseek-flash、glm-5.3-flashx、glm-5.3、grok-4.7），Emma 和 Bob 只跑一次，每个模型基于同一份 PRD 和架构并行写代码、各自过 QA，工作台分栏实时展示各路进度；完成后切换对比预览，一键采用 |
| 发布分享 | 一键把最新版本发布到公开链接 `/s/{slug}`，无需登录即可全屏使用，带浏览量统计；可更新到新版本或取消发布 |
| 多轮迭代 | 有应用后再发消息，由 Mike（团队负责人）判断是"在现有应用上修改"还是"推倒重做"；修改只输出变更文件，再合并成新版本 |
| 版本历史 | 每次 AI 生成、手动编辑、回滚都生成新版本，可以随时查看任意历史版本并回滚 |
| 在线改代码 | 在"代码"页签直接编辑，预览实时刷新，可保存为新版本 |
| 一键修复 | 预览运行报错时，点击"让 Alex 修复"会把报错信息交给工程师 |
| 导出项目 | 任意版本可导出为 Create React App 结构的 zip，本地 `npm install && npm start` 即可运行 |
| 体验细节 | 预览可切换桌面 / 手机尺寸；窄屏下工作台改为"对话 / 应用"页签切换；每轮结束显示耗时和 token 用量 |
| 数据持久化 | 账号、项目、对话、版本、发布记录全部存入 Postgres（生产用 Neon，本地用 SQLite）；生成的应用自身数据存在 localStorage |

## 架构

```
浏览器 (React SPA)                         FastAPI
┌──────────────────────────┐   JSON       ┌───────────────────────────────┐
│ 登录注册 / 项目列表 / 工作台 │ ──────────▶ │ /api/auth  /api/projects       │
│ 公开分享页 /s/{slug}        │              │ /api/share/{slug}（免登录）     │
│                          │   NDJSON 流   │ /api/projects/{id}/messages   │
│ 对话 + Agent 时间线        │ ◀────────── │   └─ Agent Pipeline           │
│ Race 双栏 / 方案对比        │              │      Mike → Emma → Bob        │
│ Sandpack 预览 / 代码编辑    │              │      → Alex → QA (→ Alex 修复) │
└────────────┬─────────────┘              │      Race：N 路 Alex+QA 并行    │
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
8. **邀请码控制注册，账号承载身份。** 邀请码只在注册时校验并扣减次数，注册后所有鉴权、项目归属和额度都基于账号。密码用标准库 scrypt 加盐哈希，不引入额外依赖。
9. **不引入 Alembic。** 启动时 `create_all` 创建缺失的表；对已有表新增的可空列，用 `app/db.py` 里一个十几行的 `_add_missing_columns()` 检查后补 `ALTER TABLE ADD COLUMN`。发布记录用独立的 `shares` 表，不改旧表。Demo 阶段表结构简单，属于有意的复杂度控制。
10. **Race 只分叉"写代码"这一段。** PRD 和架构对两个方案是共享的，分叉在 Alex 之后，这样对比的是"同一需求的两种实现"，而不是两份不同的需求；也少跑一次 Emma 和 Bob。实现上把"Alex 编码 → QA → 修复一轮"抽成 `_code_and_check`，普通生成和 Race 共用；Race 用 `asyncio.Queue` 合并多路事件流，每个事件带 `lane` 字段，前端按 lane 分别渲染。每路产出一个 `source=race` 的候选版本，"采用"复用已有的回滚接口生成最新版本，不需要新接口。
11. **Race 的模型选择。** 所有模型走同一个 OpenAI 兼容网关，`LLM_RACE_MODELS` 只是一份白名单（`LLM_MODEL` 总会被加进去），用户在界面上勾选 2-3 个参赛，后端校验必须在白名单内。不同模型对可选参数的支持不一样（例如有的不认 DeepSeek 风格的 `thinking`，有的不认 `stream_options`），所以某个模型返回 400 时，会按顺序去掉这些可选参数重试，并对这个模型记住，之后不再发送。某一路模型报错只会让那一路失败，其他方案照常产出。不传模型时，用默认模型的两种风格（低温度稳健版 + 高温度、视觉更大胆的创意版）比较。Race 只在新建或推倒重做时生效（小修改没必要比较），每个参赛模型消耗 1 次额度——第 1 次由接口扣，其余由流水线在确定要 Race 时才扣，Mike 判断为"修改"时不会多扣；额度不够时自动退回单方案并提示。
12. **发布的是快照，不是实时同步。** 分享链接指向某个具体版本，继续修改不会影响已发布的应用，需要手动"更新到最新版本"，和 Atoms / Vercel 的发布语义一致。

## 完成度

已完成：

- 邀请码注册与账号登录、项目管理、多智能体流水线、流式过程展示
- Sandpack 预览、代码编辑、版本历史、回滚、运行报错一键修复
- Race 多方案并行与对比采用、发布分享（公开链接 + 浏览量）、导出 zip、桌面 / 手机预览、移动端工作台、耗时与 token 展示
- 后端 35 个测试，覆盖解析器、QA、鉴权、额度、流水线、Race（含多模型选择和参数降级）、发布分享、表结构补列（使用假 LLM）
- CI（后端、前端、Docker 构建）与合并到 main 后自动部署

未完成 / 已知限制：

- 生成的应用只能是纯前端应用，数据存在 localStorage，没有后端和数据库
- 预览依赖 codesandbox.io 的打包服务和 Tailwind CDN，网络受限时可能加载慢
- 单个生成请求在 HTTP 连接内完成；中途刷新页面会中断当前生成（已生成的阶段性结果会保留）。Race 期间刷新会丢失对比面板，但两个候选版本已入库，可以在版本列表里查看和采用
- 分享页同样依赖 codesandbox.io 打包服务，分享出去的是"源码 + 浏览器内编译"，不是预构建的静态产物
- token 用量依赖模型服务在流式响应里返回 usage；不支持的服务只显示耗时
- 不支持图片 / 截图输入（当前使用的 deepseek 模型没有视觉能力）

## 与 Atoms 的对照

| Atoms 能力 | mini-atoms |
| --- | --- |
| 多角色团队（Mike / Emma / Bob / Alex …） | 已实现 Mike、Emma、Bob、Alex、Quinn 五个角色 |
| Race 模式（多模型并行，择优） | 已实现，用户勾选 2-3 个模型并行 |
| App Viewer 实时预览、版本历史 | 已实现（Sandpack + 不可变版本快照） |
| 一键发布到公开域名 | 已实现 `/s/{slug}`，暂不支持自定义域名 |
| Supabase 后端 / 数据库 | 未实现，生成的应用只用 localStorage |
| Remix / 作品广场 | 未实现 |
| 图片输入、更多角色（数据分析、深度研究） | 未实现 |

## 后续路线（按优先级）

1. **生成应用的后端能力**：给生成的应用注入一个平台 KV / 数据表 SDK，让数据跨设备持久化（对标 Atoms 的 Supabase 集成）。这是和 Atoms 差距最大、也最能提升"可用性"的一项
2. **后台任务化**：生成任务放进队列，前端断线可以续看；同时为多实例部署做准备
3. **模板广场与 Remix**：在发布分享的基础上公开优秀作品，一键复制到自己的项目再改
4. **视觉自检**：用无头浏览器截图预览，让 QA 基于截图和运行时日志判断问题；也可以作为 Race 的自动评委
5. **成本看板**：把每轮的耗时和 token 落库，按用户 / 模型统计

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

打开 http://localhost:5173，用 `.env` 里 `INVITE_CODES` 配置的邀请码注册账号（默认 `DEMO`），之后用账号登录。

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
  - 可选：`LLM_RACE_MODELS`（Race 可选模型白名单）不在部署流程里，使用代码中的默认值 `glm-5.3-flashx,glm-5.3,grok-4.7`；要修改时把它加到 deploy 工作流
  - 修改方式：在 *Settings → Environments → production* 中更新，然后重新运行 *Deploy*。新增配置项时，还需要加到 deploy 工作流的 *Upload runtime config* 步骤。
- 服务器防火墙需要放行 TCP 80、443（Caddy 申请证书和提供 HTTPS 都需要）。
- 部署权限：仓库 variable `DEPLOY_HOST`；仓库 secrets `DEPLOY_USER`、`DEPLOY_SSH_KEY`、`DEPLOY_KNOWN_HOSTS`。
- 回滚：*Actions → Deploy → Run workflow*，填入旧的 commit SHA。只能部署已经在 `main` 上的提交。
- `production` 环境及其 secrets 只对 `main` 分支开放，第三方 Action 都固定到 commit SHA。
