# Amazon Ads MCP 控制台

保留原 CLI，并增加 PostgreSQL 持久化、后台任务、Streamable HTTP MCP 与中文管理页面。
不是把任意 shell 命令暴露给模型。请求使用账户绑定的操作契约，CLI 和服务共用参数构造及执行分发。

## 页面与能力

| 页面 | 功能 |
| --- | --- |
| 工作概览 | 已连接账户、任务状态、保存数据行数、待确认操作 |
| 广告账户 | 加密保存已有 Amazon OAuth 凭证，验证 Profile/站点归属 |
| 报表与数据 | 创建每日报表任务、查看状态、分页预览和导出 JSON |
| 广告操作 | 从现有操作契约选择查询或生成变更计划 |
| 待确认操作 | 查看精确请求，输入“确认”后执行；支持取消尚未执行的本地任务 |
| MCP Token | 独立令牌、账户范围、权限、过期与撤销；明文只返回一次 |
| 执行日志 | 账户、Token、任务、审批、远端执行与异常记录 |

初版提供 127 个可服务化的操作契约：30 个查询、85 个待确认写操作、12 个报表类型。
本地文件解析、任意输出路径、CLI 文件审批执行、凭证查看等命令不直接暴露给 MCP。
接口已封装不等于全部 Amazon SP/SB/SD 写接口已经实测。

## 端口与隔离

- API/MCP 保留 `127.0.0.1:6666`。
- 浏览器访问 `http://127.0.0.1:16666`，因为 Chromium 禁止网页使用 6666。
- MCP 地址：`http://127.0.0.1:16666/mcp/`；非浏览器客户端也可使用 `http://127.0.0.1:6666/mcp/`。
- PostgreSQL 在新容器内部监听 5432，**不发布任何宿主机数据库端口**。
- 三个容器全部 `linux/amd64`，独立网络和命名数据卷。详见 [影响清单](deploy/IMPACT.md)。
- 本项目不会自动启动容器。首次构建/启动必须先得到用户对影响清单的人工审核。

## 本地准备

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-server.lock
.venv/bin/python -m pip install --no-deps -e ./agent-harness
.venv/bin/ads-control init-env
cd web
npm ci
npm run build
```

`init-env` 使用排他创建，已存在 `.env` 时不会覆盖。文件权限 0600，包含随机生成的管理密码、数据库密码和加密密钥。
默认管理用户名为 `admin`，密码在 `.env` 的 `ADS_ADMIN_PASSWORD`。不要将此文件提交到 Git 或粘贴到日志。
修改 `.env` 不会自动改变已经存在的数据库用户密码；不能把改配置误当成完成凭证轮换。

## 人工审核通过后的 Docker 启动顺序

在仓库根目录执行；不要在其他 Compose 项目目录执行这些命令。

```sh
.venv/bin/python deploy/preflight.py
docker compose config --quiet
docker compose build api
docker compose up -d postgres api
```

第一次初始化后、导入真实账户和启动 worker **之前**，可在新数据库上运行隔离集成测试：

```sh
docker compose exec -T -e ADS_TEST_EMPTY_DATABASE=1 api python -m unittest \
  cli_anything.amazon_ads_ops_workbench.control_plane.tests.test_postgres -v
docker compose up -d worker
docker compose ps
```

测试要求该数据库没有账户或任务，使用测试用户和假上游响应，不会修改真实 Amazon 广告。
若已有业务数据，测试会拒绝运行，不能绕过这个检查。
初始化 SQL 为应用创建非超级用户 `ads_app`。API/worker 不接收 PostgreSQL 超级用户密码。
Docker 默认只绑定回环地址；远端部署请使用 HTTPS 反向代理，设置正确的 `ADS_PUBLIC_ORIGIN` 和 `ADS_SECURE_COOKIES=true`。

## MCP 接入

登录页面连接账户，在“MCP Token”页生成令牌。客户端选择 Streamable HTTP，设置：

```text
URL: http://127.0.0.1:16666/mcp/
Authorization: Bearer <页面生成的 Token>
```

这是自有 PAT/Bearer 模式，需要客户端支持自定义 Authorization 请求头；本版不提供 MCP 客户端 OAuth 动态注册。
MCP Token 与 Amazon OAuth 凭证是两套不同的认证，不要互换。

| 工具 | 用途 |
| --- | --- |
| ads_accounts | 查询此 Token 被授权的账户 |
| ads_capabilities | 获取操作列表及 JSON 参数 Schema |
| ads_query | 创建持久化查询任务 |
| ads_create_report | 创建后台报表任务 |
| ads_plan_change | 生成待用户确认的广告变更计划 |
| ads_task_status | 查看任务状态和结果摘要 |
| ads_task_rows | 分页读取已保存的数据 |
| ads_tasks | 列出有权访问的任务 |

每次提交任务须提供稳定的 `idempotency_key`，同一操作的网络重试应复用该键。
MCP 不提供“自己批准自己”的工具。模型得到计划后应把确认页面交给用户；用户登录并输入“确认”，后台才执行。
本版没有给各聊天客户端实现“用户在对话里回复确认”的可信回调，因此不能把模型自己提交的确认文本当作人类审批。

## 数据与状态

- 任务、提交参数、审批、远端 reportId、查询结果和日志存入 PostgreSQL。
- 报表原始行存入 `ads_report_rows`，以任务 ID 和行号为主键，分页读取；不依赖临时文件路径。
- `QUEUED` / `WAITING` 表示尚无完整结果，不能当作零数据。
- Amazon 返回 `COMPLETED` 且数据已写入数据库后，任务才会成为 `SUCCEEDED`；空数组单独显示为空报表。
- 单个报表任务最多 31 天。历史保留期由 Amazon 决定，不自动缩短用户请求范围或补零。
- 下载有 64 MiB 压缩/解压尺寸与 25 万行上限，大报告需拆分日期。
- 写操作部分失败标记 `PARTIAL`；提交断线或执行进程中断标记 `UNKNOWN`，不会自动重发。
- `UNKNOWN` 需要先通过查询核实远端状态。本版不自动推断未知写操作的最终结果。
- 取消任务仅停止本地排队/等待，不表示 Amazon 已取消远端报告生成。

## 安全与并发

Amazon 凭证使用 Fernet 加密；MCP Token 和会话令牌只保存摘要；密码采用 scrypt。
审批绑定用户、账户、Profile、操作和请求内容，24 小时过期，并以数据库行锁防止重复批准。
Web 审批只接受登录会话、同源请求和 CSRF Token，不接受 MCP Bearer Token。
PostgreSQL advisory lock 在 API/worker 间限制同时进行的 Amazon 调用，默认 3、最大 5。
运行模式是一个管理工作空间，可管理多个广告账户；不是带公开注册、计费和组织管理的 SaaS。

## 开发验证

```sh
.venv/bin/python -m pytest \
  agent-harness/cli_anything/amazon_ads_ops_workbench/tests/test_core.py \
  agent-harness/cli_anything/amazon_ads_ops_workbench/tests/test_full_e2e.py \
  agent-harness/cli_anything/amazon_ads_ops_workbench/control_plane/tests/test_contracts.py \
  agent-harness/cli_anything/amazon_ads_ops_workbench/control_plane/tests/test_http_mcp.py -q
```

当前本地测试记录见 [验证记录](VERIFICATION.md)。数据库和容器的实际验收状态必须以记录为准，不能由 Compose 配置检查代替。
