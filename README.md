# mini-atoms

一个 [Atoms](https://atoms.dev/) 风格的 AI 应用生成平台 Demo：用一句话描述想要的应用，一支由 AI 智能体组成的软件团队（产品经理、架构师、工程师、测试）协作完成需求梳理、架构设计、编码和检查，生成的 React 应用在浏览器里实时运行，并可以继续用对话迭代、手动改代码、回滚版本。还可以开启 Race 让两个工程师并行写出两版方案对比择优，满意后一键发布成公开链接分享给别人。

**线上体验**：<https://43-161-240-115.sslip.io> · **服务状态**：<https://43-161-240-115.sslip.io/status> · **使用指南（含截图）**：[docs/USAGE.md](docs/USAGE.md) · **提交说明**：[docs/SUBMISSION.md](docs/SUBMISSION.md) · **图文走查**：[docs/WALKTHROUGH.md](docs/WALKTHROUGH.md) · **演示视频（2 分 17 秒）**：[mini-atoms-demo.mp4](https://github.com/zh-Spike/mini-atoms/releases/download/demo-2026-10-11/mini-atoms-demo.mp4)

**示例作品（免登录直接用）**：[番茄钟](https://43-161-240-115.sslip.io/s/di8saYac)（Race 采用 + 对话迭代）· [习惯打卡](https://43-161-240-115.sslip.io/s/9_oQDh5p)（演示视频中生成）· [看板](https://43-161-240-115.sslip.io/s/7YEOxY_5) · [记账本](https://43-161-240-115.sslip.io/s/RGa9mbuC)

## 评审快速体验（约 3 分钟）

1. 打开线上地址，切换到「注册」，用提交文档里提供的评审邀请码注册（用户名 + 密码）。
2. 在项目页打开 **Race**，保持默认勾选的 2-3 个模型，点示例「番茄钟」或「看板」：可以看到 Emma 写 PRD、Bob 做架构，然后几路工程师并行写代码、各自过检查。
3. 完成后在预览上方切换「方案 A / B / C」对比，点「采用方案」；再发一句「把主色调换成蓝色」体验对话迭代，预览右上角的版本列表可以查看和回滚任意版本。
4. 点右上角「发布」得到公开链接，用无痕窗口打开即可免登录使用；生成的应用数据存在浏览器里，刷新后仍在。

模型网关不可用或额度用尽时，本轮会自动切到演示模式（回放预置应用），流程照常走完，界面会给出提示。

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
| 导出项目 | 任意版本可导出为 Create React App 结构的 zip，本地 `npm install && npm start` 即可运行；也可以导出为单个 HTML 文件，双击就能在浏览器里打开使用（导出时在浏览器里用 sucrase 编译 JSX，每个源文件变成一个 data URL 模块，用 import map 连接；Tailwind 运行时内联，npm 包从 esm.sh 加载） |
| 体验细节 | 预览可切换桌面 / 手机尺寸；窄屏下工作台改为"对话 / 应用"页签切换；每轮结束显示耗时和 token 用量 |
| 可观测性与运营 | 每次模型调用（角色、模型、prompt、思考过程、输出、输入 / 输出 token、首字延迟、耗时、成败）都落库；工作台可查看每轮明细，`/usage` 看自己的额度与用量，管理员在 `/admin` 看全局运营数据和完整 trace，公开的 `/status` 展示服务可用性；已发布应用有访问来源和设备统计 |
| 数据持久化 | 账号、项目、对话、版本、发布记录全部存入 Postgres（生产用 Neon 新加坡区域，本地用 SQLite）；生成的应用自身数据存在 localStorage |
| 演示模式兜底 | 不配置 `LLM_API_KEY`（或设 `LLM_MOCK=true`）时，各智能体回放预置的看板、番茄钟、记账本应用，整条流程（流式过程、QA、版本、Race、迭代改主题色、发布）照常可用；线上模型网关连不上、鉴权失败或额度不足时，本轮自动切到演示模式并提示 |

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

- 后端 `app/`：FastAPI + SQLAlchemy。`app/agents/` 是智能体核心，包括流式文件解析器 `parser.py`、静态检查 `qa.py`、各角色提示词 `prompts.py`、编排器 `pipeline.py` 和调用追踪 `tracing.py`；`app/metrics.py` 负责用量、运营和状态页的聚合。
- 前端 `web/`：Vite + React + TypeScript + Tailwind。构建产物由 FastAPI 同源托管，所以不需要处理跨域，Cookie 鉴权也最简单。

## 实现思路与关键取舍

1. **产物形态：多文件 React 项目 + Sandpack 预览。** 参考了几个开源实现：
   - bolt.diy 用 WebContainer 在浏览器里跑完整 Node 环境，但用于商业生产需要授权，体积也重。
   - E2B / Open Lovable 用云端沙箱，需要额外的付费服务和接入。
   - LlamaCoder 只生成单个组件。

   Sandpack 能在浏览器里编译多文件 React 项目，不需要服务端算力，预览运行在跨域 iframe 中，天然和主站隔离。代价是只支持纯前端应用、依赖需要白名单。

   样式方面踩过一个坑：现网探针（让预览里的代码把 `<head>`、脚本和计算样式 postMessage 回主页面）发现 Sandpack 的 react 模板会忽略自定义 `index.html` 的 `<head>`，最初放在里面的 Tailwind CDN 脚本从未生效；而且 `cdn.tailwindcss.com` 在国内网络下本身也访问不了。现在改为把官方 `@tailwindcss/browser`（v4）打包成本站静态资源，通过 Sandpack 的 `externalResources` 注入，深色模式用隐藏入口文件注册 class 变体。
2. **输出协议：流式 `<file path>` 标签。** 借鉴 bolt.diy，模型按 `<file path="/App.js">...</file>` 输出，后端边收边解析，按文件推送事件，前端可以展示"工程师正在写哪个文件"。模型偶尔不遵守格式，因此做了三层兜底：
   - 用户消息末尾附格式示例；
   - 解析 Markdown 代码块并从上下文推断文件名；
   - 仍然没有文件时，带纠正提示自动重试一次。
3. **流式传输用 NDJSON 而不是 SSE。** 发消息的 POST 请求直接返回事件流，前端用 `fetch` + `ReadableStream` 读取。比"先 POST 再开 EventSource"少一次往返，服务端也不需要暂存运行状态。前端每帧最多渲染一次，扛得住每秒上千个代码增量事件。
4. **QA 用确定性静态检查，不调用 LLM。** 入口文件、相对引用、依赖白名单、保留文件都用规则检查，又快又稳；发现问题再交给 Alex 修一轮，避免"让 LLM 审 LLM"的成本和不确定性。用真实模型实测后又加了"引入的名字是否真的存在"：lucide-react 图标名对照随仓库附带的 `lucide-react@0.460.0` 图标表（和 Sandpack 用的版本一致；实测 glm 和 grok 都编造过不存在的 `Tomato` 图标，导致预览白屏），以及相对文件的默认导入 / 具名导入是否和导出一致。
5. **迭代时增量修改。** 小改动只让 Alex 输出变更文件，再和上一版本合并，速度快、token 少，也不容易改坏无关代码。
6. **版本是不可变快照。** 回滚 = 复制旧版本生成新版本，历史永远不会丢。
7. **默认关闭 / 压低模型的思考。** 实测 deepseek 系列开启思考时，模型会在思考阶段先把代码草拟一遍，首字延迟达到几十秒；关闭后整体快很多。GLM / Grok 不认 DeepSeek 风格的 `thinking` 参数，改为发送低思考强度（Chat 协议的 `reasoning_effort`、Responses 协议的 `reasoning.effort`）。同一个三模型 Race 实测从 479 秒、12 万 token 降到 56 秒、2 万 token。可以用 `LLM_DISABLE_THINKING=false` 打开完整思考。
8. **按模型适配协议。** 同一网关下，grok 系列只支持 Responses 协议（Chat Completions 直接返回 `protocol_not_supported`），glm-5.3 在 Chat 协议下会把思考过程混进正文，所以这两类走 Responses 协议（`LLM_RESPONSES_MODELS`），其他模型遇到 `protocol_not_supported` 时自动切换。可选参数被某个模型拒绝（400）时，逐个去掉试探，只丢掉真正被拒绝的那个，并按模型记住。追踪数据还暴露过一次静默失败：glm-5.3-flashx 不接受关闭思考，即使低思考强度也会在思考里先把整份代码写一遍，用完网关默认的 4096 输出 token 后正文为空，Race 里这一路就悄悄消失了。现在每次调用显式设置 `LLM_MAX_TOKENS`（默认 16384，被拒绝时同样自动去掉），某一路没有产出代码时明确报错，新建时没有代码则整轮报错。
9. **邀请码控制注册，账号承载身份。** 邀请码只在注册时校验并扣减次数，注册后所有鉴权、项目归属和额度都基于账号。密码用标准库 scrypt 加盐哈希，不引入额外依赖。
10. **不引入 Alembic。** 启动时 `create_all` 创建缺失的表；对已有表新增的可空列，用 `app/db.py` 里一个十几行的 `_add_missing_columns()` 检查后补 `ALTER TABLE ADD COLUMN`。发布记录用独立的 `shares` 表，不改旧表。Demo 阶段表结构简单，属于有意的复杂度控制。
11. **Race 只分叉"写代码"这一段。** PRD 和架构对两个方案是共享的，分叉在 Alex 之后，这样对比的是"同一需求的两种实现"，而不是两份不同的需求；也少跑一次 Emma 和 Bob。实现上把"Alex 编码 → QA → 修复一轮"抽成 `_code_and_check`，普通生成和 Race 共用；Race 用 `asyncio.Queue` 合并多路事件流，每个事件带 `lane` 字段，前端按 lane 分别渲染。每路产出一个 `source=race` 的候选版本，"采用"复用已有的回滚接口生成最新版本，不需要新接口。
12. **Race 的模型选择。** 所有模型走同一个 OpenAI 兼容网关，`LLM_RACE_MODELS` 只是一份白名单（`LLM_MODEL` 总会被加进去），用户在界面上勾选 2-3 个参赛，后端校验必须在白名单内。不同模型对可选参数的支持不一样（例如有的不认 DeepSeek 风格的 `thinking`，有的不认 `stream_options`），所以某个模型返回 400 时，会按顺序去掉这些可选参数重试，并对这个模型记住，之后不再发送。某一路模型报错只会让那一路失败，其他方案照常产出。不传模型时，用默认模型的两种风格（低温度稳健版 + 高温度、视觉更大胆的创意版）比较。Race 只在新建或推倒重做时生效（小修改没必要比较），每个参赛模型消耗 1 次额度——第 1 次由接口扣，其余由流水线在确定要 Race 时才扣，Mike 判断为"修改"时不会多扣；额度不够时自动退回单方案并提示。
13. **发布的是快照，不是实时同步。** 分享链接指向某个具体版本，继续修改不会影响已发布的应用，需要手动"更新到最新版本"，和 Atoms / Vercel 的发布语义一致。
14. **可观测性自建，不接第三方。** 多智能体 + 多模型的产品，最需要回答的是"这一轮慢在哪、花了多少 token、哪个模型最容易失败、服务现在是否可用"。实现分三层，见下方"可观测性与运营"一节。没有接 Langfuse 之类的平台，是为了不增加外部依赖和部署成本；表结构按 trace（`runs`）/ generation（`llm_calls`）组织，和这类平台的概念一致，之后要迁移也只需要在 `TracedLLM` 里多上报一份。
15. **演示模式是一个"假模型"，不是一条假流程。** `MockLLM` 实现和真实客户端相同的 `LLM` 接口，按系统提示词识别角色，回放预置内容：Emma / Bob 是对应应用的 PRD 和架构，Alex 按真实的 `<file>` 协议分块流式输出完整的多文件 React 项目。因此解析器、QA、版本、Race、追踪都真实运行，测试里也校验了预置应用能通过 QA。主题色集中在 `/lib/theme.js`，Race 每一路用不同的强调色和明暗风格，迭代时"把主色调换成蓝色"只改这一个文件。线上用 `FallbackLLM` 包住真实客户端：调用在产出任何内容之前就失败（连接错误、401 / 403、限流或额度不足、5xx）时，本轮剩余步骤改走演示模式，并通过 `notice` 事件告诉用户；已经开始输出后再失败则照常报错，因为半截回答没法由另一个模型接着写。这样演示能否跑完不再取决于第三方网关和额度。

## 可观测性与运营

参考了 Atoms 文档里的 [积分和使用情况](https://help.atoms.dev/zh/articles/12129588-credits-and-usage)（余额常驻、使用历史）、[分析概览](https://help.atoms.dev/zh/articles/12129580-analytics-overview)（已发布站点的访问、来源、设备，7 / 30 天）。

```
run_pipeline ──tracer.wrap(llm, agent, step, lane)──▶ TracedLLM ──▶ OpenAICompatLLM
     │                                                    │
     ▼                                                    ▼
   runs（每轮：模式、状态、QA、版本、token、耗时）      llm_calls（每次调用：prompt、思考、输出、
                                                          输入 / 输出 token、首字延迟、耗时、成败）
```

- **追踪**：`TracedLLM` 包住任意 LLM（测试里的假 LLM 也一样），记录每次调用；格式重试记为 `alex-retry`，QA 修复轮记为 `alex-fix`，Race 每路带 `lane`。客户端中途断开时，这一轮和进行中的调用记为"中断"，不算作失败。追踪数据交给单个后台线程按顺序写入：线上数据库每次往返有几百毫秒，同步写入会拖慢下一个智能体，还会阻塞事件循环、卡住其他用户的请求；写入失败只记日志，不影响生成，进程退出前会把队列写完。单个文本字段超过 10 万字符会截断。
- **用户层**：工作台每轮结束显示耗时、token 和各角色的 token，点"查看明细"打开时间线抽屉（每次调用的起止时间、首字延迟、输入 / 输出 token，可展开思考过程和输出）。顶栏常驻剩余额度，点进 `/usage` 看 7 / 30 天的运行、成功率、token 趋势、按模型 / 按角色拆分和最近运行。发布弹窗里有近 7 天访问量、来源和设备占比。
- **管理员层**（`ADMIN_USERNAMES` 指定）：`/admin` 展示用户 / 项目 / 运行量、成功率、耗时 P50 / P95、token；模型健康度（调用数、失败率、平均和 P95 首字延迟）；各角色 token 占比；生成质量（QA 最终通过率、需要修复轮的比例、Race 次数和被采用次数；采用次数只统计追踪上线之后，和 Race 次数口径一致）；活跃用户、额度预警、邀请码使用、热门分享；运行记录可按状态、模型、用户筛选，打开后能看到完整的 system / user prompt。
- **公开状态页** `/status`：应用、数据库（`SELECT 1` 延迟）、模型网关（`models.list` 探测，缓存 60 秒）三个组件的状态，近 24 小时生成成功率和每小时分布、各模型的调用成功率与首字延迟、版本号和运行时长。数据库不可用为"服务中断"；网关不可用，或近 24 小时成功率低于 80%（至少 5 轮）时为"性能下降"。不返回任何用户数据。`/healthz` 保持轻量，仍用于部署和容器健康检查。
- **隐私边界**：prompt 原文只有管理员能看；普通用户的明细里只有自己这一轮的思考过程和输出，不含系统提示词。

线上实测（2026-10-11，deepseek-flash）：追踪数据暴露了一个此前没注意到的瓶颈。最初一轮"番茄钟"新建 22.6 秒，三次模型调用只占约 12.5 秒，其余时间都花在数据库往返上：应用部署在香港，Neon 数据库却在 `us-east-2`，`/status` 显示 `SELECT 1` 稳定在约 650 ms。分两步解决：

| 阶段 | 一轮新建总耗时 | 模型调用以外的耗时 | 数据库 `SELECT 1` |
| --- | --- | --- | --- |
| 追踪同步写库，数据库在美国 | 22.6 秒 | 约 10 秒 | 约 650 ms |
| 追踪改为后台线程写入 | 21.2 秒 | 约 6.4 秒 | 约 650 ms |
| 数据库迁到新加坡（`aws-ap-southeast-1`） | 14.8 秒 | 约 1.5 秒 | 约 120 ms |

迁移方式：新建新加坡区域的 Neon 项目，在服务器上演练一次 `pg_dump` / `pg_restore` 并核对 9 张表行数；正式切换时先停应用、再导出导入、核对一致后改 `DATABASE_URL` 启动，停机 55 秒，登录态和数据都不受影响。美国区域的旧项目保留为备份（不再写入），服务器上也留有切换时的导出文件。

## 完成度

已完成：

- 邀请码注册与账号登录、项目管理、多智能体流水线、流式过程展示
- Sandpack 预览、代码编辑、版本历史、回滚、运行报错一键修复
- Race 多方案并行与对比采用、发布分享（公开链接 + 浏览量）、导出 zip、桌面 / 手机预览、移动端工作台、耗时与 token 展示
- 可观测性与运营：模型调用追踪、每轮明细、用户用量页、管理员运营后台、公开状态页、分享访问分析
- 演示模式：无 Key 时完整可用，网关故障时自动降级
- 后端 65 个测试，覆盖解析器、QA（含图标名和导入导出一致性）、鉴权、额度、流水线、Race（含多模型选择、协议切换和参数降级）、发布分享、表结构补列、调用追踪（含修复轮、Race 分路、失败、写库失败不影响生成）、Race 采用统计口径、用量与运营接口权限、状态页、演示模式（预置应用通过 QA、生成与迭代、Race 分路差异、网关故障降级）
- CI（后端、前端、Docker 构建）与合并到 main 后自动部署；每 30 分钟的线上巡检（`/healthz`、`/api/status`、首页和分享页，失败时 GitHub 邮件提醒）

未完成 / 已知限制：

- 生成的应用只能是纯前端应用，数据存在 localStorage，没有后端和数据库
- 预览依赖 codesandbox.io 的打包服务，网络受限时可能加载慢（Tailwind 运行时已改为本站托管，不再依赖外部 CDN）
- 单个生成请求在 HTTP 连接内完成；中途刷新页面会中断当前生成（已生成的阶段性结果会保留）。Race 期间刷新会丢失对比面板，但两个候选版本已入库，可以在版本列表里查看和采用
- 分享页同样依赖 codesandbox.io 打包服务，分享出去的是"源码 + 浏览器内编译"，不是预构建的静态产物
- token 用量依赖模型服务在流式响应里返回 usage；不支持的服务只显示耗时
- 不支持图片 / 截图输入（当前使用的 deepseek 模型没有视觉能力）
- 演示模式只预置了看板、番茄钟、记账本三个应用（按关键词匹配，匹配不到时用看板），迭代只支持改主题色和明暗风格；网关故障时要等客户端重试完（约 10 秒）才会切换

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
5. **成本与告警**：在已落库的 token 基础上配置各模型单价，折算成金额并按用户设预算；状态页降级或模型失败率升高时推送告警（企业微信 / 邮件）
6. **提示词迭代闭环**：基于 `llm_calls` 对比同一角色不同提示词版本的 token、耗时和 QA 通过率

## 本地开发

```bash
# 后端
uv sync
cp .env.example .env   # 填写 LLM_API_KEY；留空则以演示模式运行
uv run uvicorn app.main:app --reload

# 前端（另开终端，/api 会代理到 8000 端口）
cd web
npm install
npm run dev
```

打开 http://localhost:5173，用 `.env` 里 `INVITE_CODES` 配置的邀请码注册账号（默认 `DEMO`），之后用账号登录。没有模型 Key 也可以直接体验：页面右上角会显示"演示模式"，选择"看板""番茄钟""记账本"示例即可走完整流程。

## 检查

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
cd web && npm run lint && npm run typecheck && npm run build
```

## 部署

```
feature 分支 -> PR -> CI（后端检查、前端检查、Docker 构建）-> squash merge 到 main
  -> main 上 CI 通过 -> Deploy：构建并推送 ghcr.io 镜像 -> SSH 到服务器
  -> docker compose pull && up -d -> 通过 HTTPS 做健康检查（/healthz、SPA 首页、未登录 /api/auth/me 返回 401、/api/status 的版本号等于本次部署的 commit）
```

- 线上地址：https://43-161-240-115.sslip.io 。[sslip.io](https://sslip.io) 把 IP 形式的子域名解析回这个 IP，从而不用买域名也能申请证书。直接用 IP 的 HTTP 访问仍然可用，作为兜底。
- `docker-compose.yml` 包含两个服务：`web`（应用，只在内部网络暴露 8000 端口）和 `caddy`（监听 80/443 的反向代理）。Caddy 会为 `SITE_ADDRESS` 自动申请并续期 Let's Encrypt 证书，证书保存在 `caddy_data` 卷里。
- 必须用 HTTPS 的原因：浏览器只在安全上下文（HTTPS 或 localhost）里提供 `crypto.subtle` 等 API，Sandpack 依赖这些 API；前端对 HTTP 环境也做了兼容补丁。
- `Dockerfile` 是多阶段构建：先用 Node 构建前端，再把 `web/dist` 拷贝进 Python 镜像，由 FastAPI 托管。
- 运行时配置在 GitHub `production` 环境中管理，每次部署写入服务器的 `/opt/mini-atoms/.env`（权限 600）。任何一项缺失，部署都会在重启服务之前失败。
  - secrets：`DATABASE_URL`（Neon 项目 `mini-atoms-sg`，`aws-ap-southeast-1`，使用 pooler 地址）、`LLM_API_KEY`、`SECRET_KEY`、`INVITE_CODES`
  - variables：`LLM_BASE_URL`、`LLM_MODEL`、`SITE_ADDRESS`（HTTPS 域名，如 `43-161-240-115.sslip.io`）
  - 可选 variable：`ADMIN_USERNAMES`（可访问 `/admin` 的用户名，逗号分隔），不配置时没有管理员
  - 镜像构建时把 commit SHA 作为 `GIT_SHA` 注入，显示在 `/status` 页
  - 可选：`LLM_RACE_MODELS`（Race 可选模型白名单）不在部署流程里，使用代码中的默认值 `glm-5.3-flashx,glm-5.3,grok-4.7`；要修改时把它加到 deploy 工作流
  - 修改方式：在 *Settings → Environments → production* 中更新，然后重新运行 *Deploy*。新增配置项时，还需要加到 deploy 工作流的 *Upload runtime config* 步骤。
- 服务器防火墙需要放行 TCP 80、443（Caddy 申请证书和提供 HTTPS 都需要）。
- 部署权限：仓库 variable `DEPLOY_HOST`；仓库 secrets `DEPLOY_USER`、`DEPLOY_SSH_KEY`、`DEPLOY_KNOWN_HOSTS`。
- 回滚：*Actions → Deploy → Run workflow*，填入旧的 commit SHA。只能部署已经在 `main` 上的提交。
- `production` 环境及其 secrets 只对 `main` 分支开放，第三方 Action 都固定到 commit SHA。
