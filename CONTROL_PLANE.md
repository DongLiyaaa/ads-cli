# Amazon Ads MCP 控制台

保留原 CLI，并增加 PostgreSQL 持久化、后台任务、Streamable HTTP MCP 与中文管理页面。
不是把任意 shell 命令暴露给模型。请求使用账户绑定的操作契约，CLI 和服务共用参数构造及执行分发。

## 页面与能力

| 页面 | 功能 |
| --- | --- |
| 工作概览 | 已连接账户、任务状态、保存数据行数、待确认操作 |
| 广告账户 | 加密保存已有 Amazon OAuth 凭证，验证 Profile/站点归属 |
| 报表与数据 | 创建每日报表任务、查看状态和导出 JSON |
| 数据表格 | 按报表以表格查看已保存数据，中文列名，每页 50 / 100 / 200 条（最多 200） |
| AMC 洞察 | 显示 AMC 实例和可用数据表；用内置模板或自定义 SQL 运行查询，结果在数据表格查看 |
| 广告操作 | 从现有操作契约选择查询或生成变更计划 |
| 待确认操作 | 查看精确请求，输入“确认”后执行；支持取消尚未执行的本地任务。也可通过 MCP 在对话中确认（见下文） |
| MCP Token | 独立令牌、账户范围、权限、过期与撤销；明文只返回一次 |
| 执行日志 | 账户、Token、任务、审批、远端执行与异常记录 |

提供 139 个可服务化的操作契约：34 个查询、85 个待确认写操作、20 个报表类型（SP 10 个、SB 5 个、SD 4 个、AMC 查询 1 个）。
Amazon 报表只保留最近约 95 天的数据（以 Amazon 返回为准），更早的开始日期会被 Amazon 拒绝。
展示份额：Reporting v3 只提供“搜索结果顶部展示份额”（`topOfSearchImpressionShare`，广告活动、广告位和关键词/投放级别）。Amazon 后台的“搜索词展示份额报告”没有对应的 API 字段，无法通过本系统获取。
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

`init-env` 使用排他创建，已存在 `.env` 时不会覆盖。文件权限 0600，包含随机生成的数据库密码和加密密钥。不要将此文件提交到 Git 或粘贴到日志。

### 首次创建管理员账号

数据库里还没有任何用户时，打开管理页面会进入“创建管理员账号”页，由你自己设置用户名和密码，创建后直接进入工作台。

- 用户名 3–64 位字母、数字或 `. _ @ -`；密码至少 12 位，且不能与用户名相同。
- 只能创建一次。多个页面同时提交时只有第一个成功，其余提示“已完成初始化，请直接登录”。
- 本机部署（`ADS_PUBLIC_ORIGIN` 是 `127.0.0.1` / `localhost`）可以直接创建。
- 远程部署必须先在 `.env` 设置 `ADS_SETUP_TOKEN`（例如 `python3 -c "import secrets;print(secrets.token_urlsafe(32))"`）并重启 api，页面会要求填写这个初始化口令，防止别人抢先注册。未设置时远程页面不允许创建。
- 兼容旧方式：如果 `.env` 里设置了 `ADS_ADMIN_PASSWORD`（用户名取 `ADS_ADMIN_USERNAME`，默认 `admin`），`migrate` 会在空库里直接创建这个账号，此时不再显示创建页。数据库里已有用户时，这两个变量不会再新增账号。
- 修改 `.env` 不会改变已存在用户的密码；不能把改配置误当成完成凭证轮换。

### 修改与重置密码

- **修改密码**：登录后点侧栏底部的锁形按钮，进入“修改密码”页。保存后当前页面保持登录，其他设备上的登录全部退出。
- **忘记密码**：登录页点“忘记密码？”进入 `/reset-password`，填写用户名和新密码即可重置，不需要邮箱或验证码。重置后所有设备上的登录都会退出，需用新密码重新登录。
- 重置和首次创建使用同一条安全规则：本机部署可直接操作；远程部署必须填写 `.env` 里的 `ADS_SETUP_TOKEN`，未设置时不允许重置。这意味着本机部署下，能打开这个页面的人都能重置密码，请不要把 16666/6666 端口暴露到本机以外。
- 每个来源 IP 15 分钟内最多失败 10 次（如用户名不存在），超过后需等待。
- MCP Token 不受密码修改影响；如怀疑泄露，请在“MCP Token”页单独撤销。

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
| ads_confirm_change | 用户在对话里回复“确认”后提交执行（需 `changes:approve`） |
| ads_task_status | 查看任务状态和结果摘要 |
| ads_task_rows | 分页读取已保存的数据 |
| ads_tasks | 列出有权访问的任务 |

每次提交任务须提供稳定的 `idempotency_key`，同一操作的网络重试应复用该键。
### 确认执行变更

| 方式 | 条件 | 优势 | 劣势 |
| --- | --- | --- | --- |
| 页面确认（默认） | 用户登录页面，核对请求后输入“确认” | 人亲眼核对精确请求，最安全 | 要切换到浏览器操作 |
| MCP 对话确认（可选） | Token 勾选 `changes:approve`（在对话中确认执行变更）；用户在对话里回复“确认”后，AI 调用 `ads_confirm_change` | 不离开对话即可执行 | 依赖 AI 如实转达用户回复；服务端无法区分“用户说的确认”和“模型自己填的确认” |

MCP 对话确认的限制：
- 生成 Token 时该权限默认不勾选，需要显式开启；已有 Token 不受影响，要用此功能请新建 Token。
- 只能确认该 Token 自己通过 `ads_plan_change` 提交的计划；页面或其他 Token 提交的计划仍需页面确认。
- `confirm_text` 必须是“确认”，`payload_hash` 必须与计划一致，每个计划只能确认一次，24 小时过期。
- 执行日志里 `task.approved` 会记录 `via: mcp` 和 Token ID，便于审计；撤销 Token 立即失效。

## AMC（Amazon Marketing Cloud）

AMC 用隐私安全的 SQL 查询事件级广告数据（谁看到了哪些广告、之后有没有购买），能做常规报表做不到的分析。

- **实例识别**：通过账户管理接口找到站点对应的广告实体 ID（`ENTITY…`），再调用 `GET /amc/instances` 取得实例；结果缓存 30 分钟。卖家首次使用需用该 Amazon 账号登录 AMC 控制台接受条款。
- **运行查询**：报表任务 `reports.create-amc-query`，参数为内置模板 `template` 或自定义 `sql`，加起止日期（最长 366 天）。worker 提交 `workflowExecutions`、轮询状态、下载 CSV 结果并写入数据库，数据表格和 `ads_task_rows` 都能读取。
- **只读查询**：`amc.templates`、`amc.instances`、`amc.data-sources`、`amc.executions`，可通过 MCP `ads_query` 调用。
- **限制**：数据约有 48 小时延迟；不支持 `LIMIT`、顶层 `ORDER BY` 和 `SELECT *`，必须是汇总查询；覆盖人数过少的结果行会被 Amazon 按隐私阈值过滤，小账户、短时间范围或细分组可能返回空结果；多次运行高度相似的查询可能被 Amazon 拒绝。
- **不包含**：受众创建（需 Amazon DSP）、第一方数据上传（需 AWS S3）和定时计划，本版未实现。

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
