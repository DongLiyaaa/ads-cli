import { useEffect, useEffectEvent, useState, useRef } from "react";
import {
  SquaresFour,
  ChartBar,
  ClockCounterClockwise,
  Key,
  ShieldCheck,
  TerminalWindow,
  Buildings,
  ArrowRight,
  ArrowClockwise,
  Plus,
  X,
  SignOut,
  Copy,
  CheckCircle,
  WarningCircle,
  DownloadSimple,
  PlugsConnected,
  CaretRight,
  Database,
  Eye,
  LockKey,
} from "@phosphor-icons/react";
import { api, setCsrf } from "./api";

type Account = {
  id: string;
  label: string;
  marketplace: string;
  profile_id: string;
  region: string;
  verified_at: string | null;
  currency?: string;
  timezone?: string;
};
type Task = {
  id: string;
  account_id: string;
  operation: string;
  kind: string;
  status: string;
  created_at: string;
  updated_at: string;
  row_count: number;
  remote_status?: string;
  remote_id?: string;
  error?: string;
  payload_hash: string;
  payload?: any;
  arguments?: any;
  result?: any;
  result_truncated?: boolean;
};
type Capability = {
  operation: string;
  kind: string;
  description: string;
  inputSchema: {
    properties: Record<
      string,
      { type: string; default?: any; enum?: string[]; description: string }
    >;
    required: string[];
  };
};
type MCPToken = {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  account_ids: string[];
  expires_at: string;
  revoked: boolean;
  last_used_at: string | null;
};
const navigation = [
  { path: "/", label: "工作概览", icon: SquaresFour },
  { path: "/accounts", label: "广告账户", icon: Buildings },
  { path: "/reports", label: "报表与数据", icon: ChartBar },
  { path: "/operations", label: "广告操作", icon: TerminalWindow },
  { path: "/approvals", label: "待确认操作", icon: ShieldCheck },
  { path: "/tokens", label: "MCP Token", icon: Key },
  { path: "/logs", label: "执行日志", icon: ClockCounterClockwise },
];
const statuses: Record<string, string> = {
  AWAITING_CONFIRMATION: "待用户确认",
  QUEUED: "已排队",
  PROCESSING: "处理中",
  EXECUTING: "正在执行",
  SUBMITTING: "提交报表中",
  WAITING: "等待 Amazon",
  SUCCEEDED: "已完成",
  FAILED: "失败",
  PARTIAL: "部分成功",
  UNKNOWN: "结果待核实",
  CANCELLED: "已取消",
};
const reportNames: Record<string, string> = {
  "reports.create-sp-campaign-placement": "SP · 活动广告位",
  "reports.create-sp-keywords": "SP · 关键词",
  "reports.create-search-terms": "SP · 搜索词",
  "reports.create-sb-campaigns": "SB · 广告活动",
  "reports.create-sb-ad-groups": "SB · 广告组",
  "reports.create-sb-targeting": "SB · 投放目标",
  "reports.create-sb-search-terms": "SB · 搜索词",
  "reports.create-sb-campaign-placement": "SB · 活动广告位",
  "reports.create-sd-campaigns": "SD · 广告活动",
  "reports.create-sd-ad-groups": "SD · 广告组",
  "reports.create-sd-product-ads": "SD · 商品广告",
  "reports.create-sd-targeting": "SD · 投放目标",
};
const scopeNames: Record<string, string> = {
  "ads:read": "查询广告数据",
  "reports:read": "读取已保存报表",
  "reports:create": "创建报表任务",
  "changes:plan": "提交变更计划（不能自行批准）",
};
function stamp(s?: string | null) {
  return s
    ? new Date(s).toLocaleString("zh-CN", { hour12: false })
    : "尚无记录";
}
function Status({ value }: { value: string }) {
  return (
    <span className={`status ${value.toLowerCase()}`}>
      {statuses[value] || value}
    </span>
  );
}
function Empty({
  title,
  detail,
  action,
}: {
  title: string;
  detail: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty">
      <Database size={30} weight="duotone" />
      <h3>{title}</h3>
      <p>{detail}</p>
      {action}
    </div>
  );
}
function Modal({
  title,
  children,
  close,
}: {
  title: string;
  children: React.ReactNode;
  close: () => void;
}) {
  const dialog = useRef<HTMLElement>(null);
  const onClose = useEffectEvent(close);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialog.current?.focus();
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab") {
        const nodes = Array.from(
          dialog.current?.querySelectorAll<HTMLElement>(
            "button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], summary",
          ) || [],
        );
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (!first) {
          e.preventDefault();
          return;
        }
        if (
          e.shiftKey &&
          (document.activeElement === first ||
            document.activeElement === dialog.current)
        ) {
          e.preventDefault();
          last.focus();
        } else if (
          !e.shiftKey &&
          (document.activeElement === last ||
            document.activeElement === dialog.current)
        ) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", handler);
    return () => {
      document.removeEventListener("keydown", handler);
      document.body.style.overflow = previousOverflow;
      previous?.focus();
    };
  }, []);
  return (
    <div className="modal-backdrop" onClick={close}>
      <section
        className="modal"
        ref={dialog}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <header>
          <h2>{title}</h2>
          <button className="icon-button" aria-label="关闭" onClick={close}>
            <X size={20} />
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState<string | null>(null),
    [booting, setBooting] = useState(true),
    [page, setPage] = useState(location.pathname);
  const [accounts, setAccounts] = useState<Account[]>([]),
    [accountId, setAccountId] = useState(""),
    [tasks, setTasks] = useState<Task[]>([]),
    [tokens, setTokens] = useState<MCPToken[]>([]),
    [logs, setLogs] = useState<any[]>([]),
    [catalog, setCatalog] = useState<Capability[]>([]),
    [overview, setOverview] = useState<any>({});
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(""),
    [synced, setSynced] = useState(""),
    [offset, setOffset] = useState(0),
    [filter, setFilter] = useState("");
  const [accountModal, setAccountModal] = useState(false),
    [tokenModal, setTokenModal] = useState(false),
    [oneTime, setOneTime] = useState(""),
    [detail, setDetail] = useState<Task | null>(null),
    [rows, setRows] = useState<any>(null),
    [rowOffset, setRowOffset] = useState(0),
    [confirmation, setConfirmation] = useState("");
  const [reportKind, setReportKind] = useState(
      "reports.create-sp-campaign-placement",
    ),
    [startDate, setStartDate] = useState(""),
    [endDate, setEndDate] = useState("");
  const [operation, setOperation] = useState("campaigns.list"),
    [argumentsText, setArgumentsText] = useState("{}");
  const navigationRef = useRef<HTMLElement>(null);
  const selected = accounts.find((a) => a.id === accountId),
    selectedOp = catalog.find((c) => c.operation === operation);
  function navigate(path: string) {
    history.pushState({}, "", path);
    setPage(path);
    setOffset(0);
    setFilter("");
    setOneTime("");
    setDetail(null);
    setRows(null);
    setNotice("");
    setError("");
  }
  function clearSession() {
    setUser(null);
    setCsrf("");
    setAccounts([]);
    setTasks([]);
    setTokens([]);
    setLogs([]);
    setOverview({});
    setAccountId("");
    setDetail(null);
    setOneTime("");
  }
  useEffect(() => {
    const reveal = () => {
      if (innerWidth <= 800)
        navigationRef.current
          ?.querySelector(".active")
          ?.scrollIntoView({ block: "nearest", inline: "nearest" });
    };
    reveal();
    addEventListener("resize", reveal);
    return () => removeEventListener("resize", reveal);
  }, [page, user]);
  useEffect(() => {
    const change = () => {
      setPage(location.pathname);
      setOffset(0);
    };
    addEventListener("popstate", change);
    return () => removeEventListener("popstate", change);
  }, []);
  useEffect(() => {
    api("/session")
      .then((s) => {
        setCsrf(s.csrf_token);
        setUser(s.username);
      })
      .catch(() => {})
      .finally(() => setBooting(false));
  }, []);
  async function refresh() {
    const [a, o, c, t] = await Promise.all([
      api<Account[]>("/accounts"),
      api("/overview"),
      api<Capability[]>("/capabilities"),
      api<Task[]>(
        `/tasks?offset=${offset}&limit=50${filter ? "&status=" + filter : ""}`,
      ),
    ]);
    setAccounts(a);
    setOverview(o);
    setCatalog(c);
    setTasks(t);
    setAccountId((old) => (a.some((v) => v.id === old) ? old : a[0]?.id || ""));
    setSynced(new Date().toLocaleTimeString("zh-CN"));
    if (page === "/tokens") setTokens(await api("/tokens"));
    if (page === "/logs") setLogs(await api(`/logs?offset=${offset}&limit=50`));
  }
  const tick = useEffectEvent(() =>
    refresh().catch((e) => {
      if (e.status === 401) {
        clearSession();
      } else setError(e.message);
    }),
  );
  useEffect(() => {
    if (!user) return;
    tick();
    const id = setInterval(() => tick(), 5000);
    return () => clearInterval(id);
  }, [user, page, offset, filter]);
  useEffect(() => {
    if (!selected) return;
    const today = new Intl.DateTimeFormat("en-CA", {
      timeZone: selected.timezone || "America/Los_Angeles",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date());
    const end = new Date(today + "T00:00:00Z");
    end.setUTCDate(end.getUTCDate() - 1);
    const start = new Date(end);
    start.setUTCDate(start.getUTCDate() - 6);
    setEndDate(end.toISOString().slice(0, 10));
    setStartDate(start.toISOString().slice(0, 10));
  }, [accountId, selected?.timezone]);
  async function action(name: string, fn: () => Promise<any>) {
    setBusy(name);
    setError("");
    setNotice("");
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function openTask(id: string) {
    setError("");
    try {
      setDetail(await api(`/tasks/${id}`));
      setRows(null);
      setRowOffset(0);
      setConfirmation("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function loadRows(id: string, offset = 0) {
    try {
      setRows(await api(`/tasks/${id}/rows?offset=${offset}&limit=50`));
      setRowOffset(offset);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    const id = new URLSearchParams(location.search).get("task");
    if (user && id) void openTask(id);
  }, [user]);
  async function copy(value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setNotice("已复制");
    } catch {
      setError("浏览器未允许复制，请手动选择复制");
    }
  }
  function taskTable(items: Task[]) {
    return items.length ? (
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>任务 / 操作</th>
              <th>账户</th>
              <th>状态</th>
              <th>数据行</th>
              <th>创建时间</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((t) => (
              <tr key={t.id}>
                <td>
                  <strong>{reportNames[t.operation] || t.operation}</strong>
                  <small className="mono">{t.id.slice(0, 8)}</small>
                </td>
                <td>
                  {accounts.find((a) => a.id === t.account_id)?.label ||
                    t.account_id.slice(0, 8)}
                </td>
                <td>
                  <Status value={t.status} />
                </td>
                <td>
                  {t.kind === "report" && t.status === "SUCCEEDED"
                    ? t.row_count.toLocaleString()
                    : "—"}
                </td>
                <td>{stamp(t.created_at)}</td>
                <td>
                  <button
                    className="text-button"
                    onClick={() => openTask(t.id)}
                  >
                    查看
                    <CaretRight size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    ) : (
      <Empty
        title="这里还没有任务"
        detail="创建报表或查询广告后，任务状态与结果会保存在这里。"
      />
    );
  }
  if (booting) return <div className="boot">正在连接 Ads Console…</div>;
  if (!user)
    return (
      <main className="login">
        <div className="login-intro">
          <div className="brand">
            <span className="brand-icon">
              <PlugsConnected size={26} weight="bold" />
            </span>
            Ads Console
          </div>
          <p className="eyebrow">AMAZON ADS · MCP WORKSPACE</p>
          <h1>
            让广告操作
            <br />
            有据可查。
          </h1>
          <p>
            连接账户、等待报表、确认变更。
            <br />
            把每一步交给一个可追踪的工作台。
          </p>
          <div className="login-features">
            <span>
              <ShieldCheck />
              人工确认
            </span>
            <span>
              <Database />
              数据留存
            </span>
            <span>
              <ClockCounterClockwise />
              执行记录
            </span>
          </div>
        </div>
        <form
          className="login-form"
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy("login");
            setError("");
            const f = new FormData(e.currentTarget);
            try {
              const s = await api("/login", "POST", {
                username: f.get("username"),
                password: f.get("password"),
              });
              setCsrf(s.csrf_token);
              setUser(s.username);
            } catch (err) {
              setError((err as Error).message);
            } finally {
              setBusy("");
            }
          }}
        >
          <span className="small-icon">
            <LockKey size={24} />
          </span>
          <h2>登录控制台</h2>
          <p>使用本地部署时配置的管理账户。</p>
          <label>
            用户名
            <input
              name="username"
              defaultValue="admin"
              autoComplete="username"
              required
            />
          </label>
          <label>
            密码
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
            />
          </label>
          {error && (
            <p role="alert" className="form-error">
              {error}
            </p>
          )}
          <button className="primary" disabled={!!busy}>
            {busy ? "正在登录…" : "进入工作台"}
            <ArrowRight size={18} />
          </button>
          <small>管理账户与 MCP Token 独立；Token 无法批准广告变更。</small>
        </form>
      </main>
    );
  return (
    <div className="shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="/"
          onClick={(e) => {
            e.preventDefault();
            navigate("/");
          }}
        >
          <span className="brand-icon">
            <PlugsConnected size={23} weight="bold" />
          </span>
          <span>
            Ads Console<small>MCP 控制台</small>
          </span>
        </a>
        <p className="nav-label">工作空间</p>
        <nav ref={navigationRef}>
          {navigation.map((n) => (
            <a
              key={n.path}
              href={n.path}
              className={page === n.path ? "active" : ""}
              onClick={(e) => {
                e.preventDefault();
                navigate(n.path);
              }}
            >
              <n.icon size={20} weight={page === n.path ? "fill" : "regular"} />
              {n.label}
              {n.path === "/approvals" &&
                overview.tasks_by_status?.AWAITING_CONFIRMATION > 0 && (
                  <b>{overview.tasks_by_status.AWAITING_CONFIRMATION}</b>
                )}
            </a>
          ))}
        </nav>
        <div className="sidebar-note">
          <ShieldCheck size={22} />
          <strong>计划先行，确认后执行</strong>
          <p>
            MCP 可以提出操作。
            <br />
            真正的执行由你确认。
          </p>
        </div>
        <footer>
          <span className="avatar">{user.slice(0, 1).toUpperCase()}</span>
          <span>
            {user}
            <small>工作空间管理员</small>
          </span>
          <button
            aria-label="退出登录"
            className="icon-button"
            onClick={() =>
              api("/logout", "POST", {})
                .then(() => {
                  clearSession();
                  setError("");
                })
                .catch((e) => setError(e.message))
            }
          >
            <SignOut size={20} />
          </button>
        </footer>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="breadcrumb">
            工作空间
            <CaretRight size={13} />
            <strong>
              {navigation.find((n) => n.path === page)?.label || "工作概览"}
            </strong>
          </div>
          <div className="top-actions">
            <span className="fresh">
              {synced ? "更新于 " + synced : "正在同步"}
            </span>
            <button
              className="icon-button"
              title="刷新"
              onClick={() => action("refresh", refresh)}
              disabled={!!busy}
            >
              <ArrowClockwise size={18} />
            </button>
            <select
              aria-label="当前广告账户"
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              disabled={!accounts.length}
            >
              {!accounts.length && <option>尚未连接账户</option>}
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.label} · {a.marketplace}
                </option>
              ))}
            </select>
          </div>
        </header>
        {error && (
          <div className="banner error" role="alert">
            <WarningCircle size={20} />
            <span>{error}</span>
            <button aria-label="关闭错误" onClick={() => setError("")}>
              <X />
            </button>
          </div>
        )}
        {notice && (
          <div className="banner success" role="status">
            <CheckCircle size={20} />
            <span>{notice}</span>
            <button aria-label="关闭提示" onClick={() => setNotice("")}>
              <X />
            </button>
          </div>
        )}
        {page === "/" && (
          <>
            <div className="page-heading">
              <div>
                <p className="eyebrow">WORKSPACE OVERVIEW</p>
                <h1>广告工作，有序进行。</h1>
                <p>从账户连接到数据回流，在这里掌握每一步。</p>
              </div>
              <button className="primary" onClick={() => navigate("/reports")}>
                <Plus size={18} />
                创建报表
              </button>
            </div>
            <section className="stats">
              <article>
                <span>
                  已连接账户
                  <Buildings />
                </span>
                <strong>{overview.accounts ?? 0}</strong>
                <small>独立凭证 · 按 Profile 隔离</small>
              </article>
              <article>
                <span>
                  进行中的任务
                  <ClockCounterClockwise />
                </span>
                <strong>
                  {[
                    "QUEUED",
                    "PROCESSING",
                    "EXECUTING",
                    "SUBMITTING",
                    "WAITING",
                  ].reduce(
                    (n, k) => n + (overview.tasks_by_status?.[k] || 0),
                    0,
                  )}
                </strong>
                <small>等待结果时可以离开页面</small>
              </article>
              <article>
                <span>
                  已保存报表数据
                  <Database />
                </span>
                <strong>
                  {(overview.report_rows || 0).toLocaleString()}
                  <em>行</em>
                </strong>
                <small>保存在 PostgreSQL 中</small>
              </article>
              <article>
                <span>
                  待用户确认
                  <ShieldCheck />
                </span>
                <strong>
                  {overview.tasks_by_status?.AWAITING_CONFIRMATION || 0}
                </strong>
                <small>尚未提交到 Amazon</small>
              </article>
            </section>
            <section className="connection-strip">
              <span className="small-icon">
                <PlugsConnected size={25} />
              </span>
              <div>
                <h3>一个入口，连接你的 AI 助手</h3>
                <p>
                  生成账户范围明确的 Token，让 MCP
                  读取数据、创建报表和提交变更计划。
                </p>
              </div>
              <button className="secondary" onClick={() => navigate("/tokens")}>
                管理 MCP Token
                <ArrowRight size={16} />
              </button>
            </section>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>最近任务</h2>
                  <p>真实任务状态，不以演示数据代替接口结果。</p>
                </div>
                <button
                  className="text-button"
                  onClick={() => navigate("/reports")}
                >
                  查看全部
                  <ArrowRight size={16} />
                </button>
              </div>
              {taskTable(tasks.slice(0, 8))}
            </section>
          </>
        )}
        {page === "/accounts" && (
          <>
            <div className="page-heading">
              <div>
                <p className="eyebrow">ACCOUNTS</p>
                <h1>广告账户</h1>
                <p>每个站点独立保存授权信息，敏感凭证加密存储。</p>
              </div>
              <button className="primary" onClick={() => setAccountModal(true)}>
                <Plus size={18} />
                连接账户
              </button>
            </div>
            {!accounts.length ? (
              <section className="panel">
                <Empty
                  title="连接你的第一个广告账户"
                  detail="准备 Client ID、Client Secret、Refresh Token 和站点 Profile ID。"
                  action={
                    <button
                      className="primary"
                      onClick={() => setAccountModal(true)}
                    >
                      连接账户
                      <ArrowRight size={16} />
                    </button>
                  }
                />
              </section>
            ) : (
              <div className="account-grid">
                {accounts.map((a) => (
                  <section className="panel account-card" key={a.id}>
                    <div className="account-card-head">
                      <span className="market">{a.marketplace}</span>
                      <span
                        className={
                          "status " + (a.verified_at ? "succeeded" : "waiting")
                        }
                      >
                        {a.verified_at ? "授权已验证" : "待验证"}
                      </span>
                    </div>
                    <h2>{a.label}</h2>
                    <dl>
                      <dt>Profile ID</dt>
                      <dd className="mono">{a.profile_id}</dd>
                      <dt>区域 / 币种</dt>
                      <dd>
                        {a.region} / {a.currency || "待验证"}
                      </dd>
                      <dt>最近验证</dt>
                      <dd>{stamp(a.verified_at)}</dd>
                    </dl>
                    <button
                      className="secondary"
                      disabled={!!busy}
                      onClick={() =>
                        action("verify", async () => {
                          await api(`/accounts/${a.id}/verify`, "POST", {});
                          setNotice("授权与站点 Profile 验证成功");
                        })
                      }
                    >
                      <ShieldCheck size={17} />
                      验证连接
                    </button>
                  </section>
                ))}
              </div>
            )}
          </>
        )}
        {page === "/reports" && (
          <>
            <div className="page-heading">
              <div>
                <p className="eyebrow">REPORTS & DATA</p>
                <h1>等待交给系统，结果留在这里。</h1>
                <p>后台持续查询 Amazon 报表状态，完成后保存原始数据。</p>
              </div>
            </div>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>创建报表任务</h2>
                  <p>单个任务最多 31 天；可查询历史范围以 Amazon 返回为准。</p>
                </div>
              </div>
              <form
                className="report-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  void action("report", async () => {
                    const t = await api<Task>("/reports", "POST", {
                      account_id: accountId,
                      operation: reportKind,
                      arguments: {
                        start_date: startDate,
                        end_date: endDate,
                        time_unit: "DAILY",
                      },
                      idempotency_key: crypto.randomUUID(),
                    });
                    setNotice("报表已入队，后台将自动等待并保存结果");
                    await openTask(t.id);
                  });
                }}
              >
                <label>
                  报表类型
                  <select
                    value={reportKind}
                    onChange={(e) => setReportKind(e.target.value)}
                  >
                    {Object.entries(reportNames).map(([id, name]) => (
                      <option key={id} value={id}>
                        {name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  开始日期
                  <input
                    type="date"
                    required
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </label>
                <label>
                  结束日期
                  <input
                    type="date"
                    required
                    min={startDate}
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </label>
                <button className="primary" disabled={!!busy || !accountId}>
                  <Plus size={18} />
                  {busy === "report" ? "正在创建…" : "创建任务"}
                </button>
              </form>
              {!accountId && (
                <p className="hint">先在“广告账户”连接并选择一个账户。</p>
              )}
            </section>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>任务记录</h2>
                  <p>
                    报表、查询与操作任务统一留存。空报表和失败任务会明确区分。
                  </p>
                </div>
                <select
                  aria-label="任务状态"
                  value={filter}
                  onChange={(e) => {
                    setFilter(e.target.value);
                    setOffset(0);
                  }}
                >
                  <option value="">全部状态</option>
                  {Object.entries(statuses).map(([k, v]) => (
                    <option value={k} key={k}>
                      {v}
                    </option>
                  ))}
                </select>
              </div>
              {taskTable(tasks)}
              <div className="pagination">
                <button
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - 50))}
                >
                  上一页
                </button>
                <span>第 {offset / 50 + 1} 页</span>
                <button
                  disabled={tasks.length < 50}
                  onClick={() => setOffset(offset + 50)}
                >
                  下一页
                </button>
              </div>
            </section>
          </>
        )}
        {page === "/operations" && (
          <>
            <div className="page-heading">
              <div>
                <p className="eyebrow">ADS OPERATIONS</p>
                <h1>查询直接进行，变更先看清单。</h1>
                <p>复用 CLI 的操作契约，不开放任意命令执行。</p>
              </div>
            </div>
            <section className="panel operation-panel">
              <label>
                选择操作
                <select
                  value={operation}
                  onChange={(e) => {
                    setOperation(e.target.value);
                    const c = catalog.find(
                      (v) => v.operation === e.target.value,
                    );
                    setArgumentsText(
                      JSON.stringify(
                        Object.fromEntries(
                          Object.entries(c?.inputSchema.properties || {})
                            .filter(([, v]) => v.default !== undefined)
                            .map(([k, v]) => [k, v.default]),
                        ),
                        null,
                        2,
                      ),
                    );
                  }}
                >
                  {catalog
                    .filter((c) => c.kind !== "report")
                    .map((c) => (
                      <option key={c.operation} value={c.operation}>
                        {c.kind === "write" ? "[待确认]" : "[查询]"}{" "}
                        {c.operation}
                      </option>
                    ))}
                </select>
              </label>
              <p>{selectedOp?.description}</p>
              <div className="operation-columns">
                <div>
                  <label>
                    操作参数（JSON）
                    <textarea
                      className="code-editor"
                      rows={13}
                      spellCheck={false}
                      value={argumentsText}
                      onChange={(e) => setArgumentsText(e.target.value)}
                    />
                  </label>
                  <button
                    className="primary"
                    disabled={!accountId || !!busy}
                    onClick={() =>
                      action("operation", async () => {
                        const args = JSON.parse(argumentsText);
                        if (
                          !args ||
                          Array.isArray(args) ||
                          typeof args !== "object"
                        )
                          throw new Error("参数必须是 JSON 对象");
                        const t = await api<Task>(
                          selectedOp?.kind === "write" ? "/plans" : "/queries",
                          "POST",
                          {
                            account_id: accountId,
                            operation,
                            arguments: args,
                            idempotency_key: crypto.randomUUID(),
                          },
                        );
                        setNotice(
                          selectedOp?.kind === "write"
                            ? "已生成待确认清单，尚未执行广告变更"
                            : "查询已入队",
                        );
                        await openTask(t.id);
                      })
                    }
                  >
                    {selectedOp?.kind === "write" ? (
                      <ShieldCheck size={18} />
                    ) : (
                      <TerminalWindow size={18} />
                    )}{" "}
                    {selectedOp?.kind === "write"
                      ? "生成待确认计划"
                      : "提交查询"}
                  </button>
                </div>
                <div className="schema">
                  <h3>参数说明</h3>
                  {Object.entries(selectedOp?.inputSchema.properties || {}).map(
                    ([name, s]) => (
                      <div key={name}>
                        <strong className="mono">
                          {name}
                          {selectedOp?.inputSchema.required.includes(name) && (
                            <b>必填</b>
                          )}
                        </strong>
                        <p>{s.description}</p>
                        <small>{s.enum ? s.enum.join(" / ") : s.type}</small>
                      </div>
                    ),
                  )}
                </div>
              </div>
            </section>
          </>
        )}
        {page === "/approvals" && (
          <>
            <div className="page-heading">
              <div>
                <p className="eyebrow">HUMAN IN CONTROL</p>
                <h1>由你确认，才会执行。</h1>
                <p>
                  核对账户、对象和具体数值后，输入“确认”。每个计划只能提交一次。
                </p>
              </div>
            </div>
            <div className="info-strip">
              <ShieldCheck size={23} />
              <p>
                MCP Token 只能提出变更计划，不能批准自己的操作。计划 24
                小时后过期。
              </p>
            </div>
            <section className="panel">
              <div className="panel-heading">
                <h2>待确认清单</h2>
                <button
                  className="secondary"
                  onClick={() => {
                    setFilter("AWAITING_CONFIRMATION");
                    setOffset(0);
                  }}
                >
                  仅看待确认
                </button>
              </div>
              {taskTable(tasks.filter((t) => t.kind === "write"))}
            </section>
          </>
        )}
        {page === "/tokens" && (
          <>
            <div className="page-heading">
              <div>
                <p className="eyebrow">MCP ACCESS</p>
                <h1>给 AI 一把有边界的钥匙。</h1>
                <p>独立生成访问令牌，限定账户、权限和有效期。</p>
              </div>
              <button
                className="primary"
                disabled={!accounts.length}
                onClick={() => setTokenModal(true)}
              >
                <Plus size={18} />
                生成 Token
              </button>
            </div>
            <section className="endpoint-card">
              <div>
                <span className="eyebrow">STREAMABLE HTTP</span>
                <h2>MCP 接入地址</h2>
                <code>
                  {(overview.mcp_endpoint || location.origin + "/mcp").replace(
                    /\/?$/,
                    "/",
                  )}
                </code>
              </div>
              <button
                className="secondary"
                onClick={() =>
                  copy(
                    (overview.mcp_endpoint || location.origin + "/mcp").replace(
                      /\/?$/,
                      "/",
                    ),
                  )
                }
              >
                <Copy size={16} />
                复制地址
              </button>
            </section>
            {oneTime && (
              <section className="panel token-secret">
                <h3>
                  <Key size={20} />
                  Token 已生成，仅此一次展示
                </h3>
                <p>
                  请保存到客户端的 Authorization
                  请求头；离开此页后不能再次查看明文。
                </p>
                <pre>{oneTime}</pre>
                <div className="button-row">
                  <button className="primary" onClick={() => copy(oneTime)}>
                    <Copy size={16} />
                    复制 Token
                  </button>
                  <button className="secondary" onClick={() => setOneTime("")}>
                    已保存，隐藏
                  </button>
                </div>
              </section>
            )}
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>访问令牌</h2>
                  <p>数据库仅保存 Token 摘要，撤销后立即拒绝新的请求。</p>
                </div>
              </div>
              {tokens.length ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>名称 / 前缀</th>
                        <th>权限</th>
                        <th>有效期</th>
                        <th>最近使用</th>
                        <th>状态</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {tokens.map((t) => (
                        <tr key={t.id}>
                          <td>
                            <strong>{t.name}</strong>
                            <small className="mono">{t.prefix}…</small>
                          </td>
                          <td>
                            {t.scopes.map((s) => (
                              <span className="tag" key={s}>
                                {scopeNames[s]}
                              </span>
                            ))}
                          </td>
                          <td>{stamp(t.expires_at)}</td>
                          <td>{stamp(t.last_used_at)}</td>
                          <td>
                            <span
                              className={
                                "status " +
                                (t.revoked
                                  ? "cancelled"
                                  : new Date(t.expires_at) < new Date()
                                    ? "failed"
                                    : "succeeded")
                              }
                            >
                              {t.revoked
                                ? "已撤销"
                                : new Date(t.expires_at) < new Date()
                                  ? "已过期"
                                  : "有效"}
                            </span>
                          </td>
                          <td>
                            <button
                              className="text-button danger"
                              disabled={t.revoked || !!busy}
                              onClick={() =>
                                action("revoke", async () => {
                                  await api(
                                    `/tokens/${t.id}/revoke`,
                                    "POST",
                                    {},
                                  );
                                  setNotice("Token 已撤销");
                                })
                              }
                            >
                              撤销
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <Empty
                  title="还没有 MCP Token"
                  detail={
                    accounts.length
                      ? "为你的 AI 客户端生成一个独立令牌。"
                      : "先连接一个广告账户，再为它分配 Token。"
                  }
                />
              )}
            </section>
            <section className="panel integration-help">
              <h3>客户端连接方式</h3>
              <p>
                选择 Streamable HTTP，并设置以下请求头。使用支持自定义
                Authorization 请求头的 MCP 客户端。
              </p>
              <pre>Authorization: Bearer &lt;你的 MCP Token&gt;</pre>
              <p>
                工具提供账户、能力查询、报表任务、变更计划和结果读取。真实广告变更需要到“待确认操作”完成用户确认。
              </p>
            </section>
          </>
        )}
        {page === "/logs" && (
          <>
            <div className="page-heading">
              <div>
                <p className="eyebrow">AUDIT TRAIL</p>
                <h1>每一次操作，都有记录。</h1>
                <p>
                  记录请求、审批、排队、Amazon
                  响应及异常，不记录密钥或签名下载地址。
                </p>
              </div>
            </div>
            <section className="panel">
              {logs.length ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>时间</th>
                        <th>动作</th>
                        <th>状态</th>
                        <th>任务</th>
                        <th>详细信息</th>
                      </tr>
                    </thead>
                    <tbody>
                      {logs.map((l) => (
                        <tr key={l.id}>
                          <td>{stamp(l.created_at)}</td>
                          <td className="mono">{l.action}</td>
                          <td>
                            <Status value={l.status} />
                          </td>
                          <td>
                            {l.task_id ? (
                              <button
                                className="text-button mono"
                                onClick={() => openTask(l.task_id)}
                              >
                                {l.task_id.slice(0, 8)}
                              </button>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td>
                            <details>
                              <summary>查看记录</summary>
                              <pre>{JSON.stringify(l.detail, null, 2)}</pre>
                            </details>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <Empty
                  title="暂无执行日志"
                  detail="账户配置、Token 和任务执行的关键动作会自动记录。"
                />
              )}
              <div className="pagination">
                <button
                  disabled={!offset}
                  onClick={() => setOffset(Math.max(0, offset - 50))}
                >
                  上一页
                </button>
                <span>第 {offset / 50 + 1} 页</span>
                <button
                  disabled={logs.length < 50}
                  onClick={() => setOffset(offset + 50)}
                >
                  下一页
                </button>
              </div>
            </section>
          </>
        )}
        <footer className="main-footer">
          <span>Amazon Ads Ops Workbench</span>
          <span>
            PostgreSQL 持久化 · API 并发上限 {overview.max_api_concurrency || 3}
          </span>
        </footer>
      </main>
      {accountModal && (
        <Modal title="连接广告账户" close={() => setAccountModal(false)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const data = Object.fromEntries(new FormData(e.currentTarget));
              void action("account", async () => {
                await api("/accounts", "POST", data);
                setAccountModal(false);
                setNotice("账户已保存，点击“验证连接”检查授权");
              });
            }}
          >
            <p className="hint">
              使用已有 Amazon Ads 授权；本页面不会重新申请或扩大 Amazon 权限。
            </p>
            <div className="form-grid">
              <label>
                账户名称
                <input
                  name="label"
                  placeholder="例如：品牌 · 美国站"
                  maxLength={160}
                  required
                />
              </label>
              <label>
                站点
                <select name="marketplace">
                  <option>US</option>
                  <option>CA</option>
                  <option>MX</option>
                  <option>UK</option>
                  <option>DE</option>
                  <option>FR</option>
                  <option>IT</option>
                  <option>ES</option>
                  <option>JP</option>
                  <option>AU</option>
                </select>
              </label>
              <label>
                API 区域
                <select name="region">
                  <option value="NA">NA · 北美</option>
                  <option value="EU">EU · 欧洲</option>
                  <option value="FE">FE · 远东</option>
                </select>
              </label>
              <label>
                Profile ID
                <input
                  name="profile_id"
                  inputMode="numeric"
                  pattern="[0-9]+"
                  required
                />
              </label>
            </div>
            <label>
              Client ID
              <input name="client_id" autoComplete="off" required />
            </label>
            <label>
              Client Secret
              <input
                name="client_secret"
                type="password"
                autoComplete="new-password"
                required
              />
            </label>
            <label>
              Refresh Token
              <input
                name="refresh_token"
                type="password"
                autoComplete="new-password"
                required
              />
            </label>
            <div className="modal-actions">
              <button
                type="button"
                className="secondary"
                onClick={() => setAccountModal(false)}
              >
                取消
              </button>
              <button className="primary" disabled={!!busy}>
                加密保存账户
              </button>
            </div>
          </form>
        </Modal>
      )}
      {tokenModal && (
        <Modal title="生成 MCP Token" close={() => setTokenModal(false)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              void action("token", async () => {
                const result = await api("/tokens", "POST", {
                  name: f.get("name"),
                  scopes: f.getAll("scope"),
                  account_ids: f.getAll("account"),
                  expires_in_days: Number(f.get("days")),
                });
                setOneTime(result.token);
                setTokenModal(false);
                setNotice("Token 已生成，请立即保存");
              });
            }}
          >
            <label>
              令牌名称
              <input
                name="name"
                placeholder="例如：运营助手 / 测试客户端"
                required
              />
            </label>
            <label>
              有效期
              <select name="days">
                <option value="7">7 天</option>
                <option value="30">30 天</option>
                <option value="90">90 天</option>
              </select>
            </label>
            <fieldset>
              <legend>可访问账户</legend>
              {accounts.map((a) => (
                <label className="check" key={a.id}>
                  <input
                    type="checkbox"
                    name="account"
                    value={a.id}
                    defaultChecked={a.id === accountId}
                  />
                  {a.label} · {a.marketplace}
                </label>
              ))}
            </fieldset>
            <fieldset>
              <legend>操作权限</legend>
              {Object.entries(scopeNames).map(([s, label]) => (
                <label className="check" key={s}>
                  <input
                    type="checkbox"
                    name="scope"
                    value={s}
                    defaultChecked={s !== "changes:plan"}
                  />
                  {label}
                </label>
              ))}
            </fieldset>
            <div className="modal-actions">
              <button
                className="secondary"
                type="button"
                onClick={() => setTokenModal(false)}
              >
                取消
              </button>
              <button className="primary" disabled={!!busy}>
                生成令牌
              </button>
            </div>
          </form>
        </Modal>
      )}
      {detail && (
        <Modal
          title={reportNames[detail.operation] || detail.operation}
          close={() => {
            setDetail(null);
            setRows(null);
          }}
        >
          <div className="task-meta">
            <Status value={detail.status} />
            <code>{detail.id}</code>
            <button className="text-button" onClick={() => openTask(detail.id)}>
              刷新状态
            </button>
          </div>
          <p className="hint">
            账户：{accounts.find((a) => a.id === detail.account_id)?.label} /{" "}
            {accounts.find((a) => a.id === detail.account_id)?.profile_id}
          </p>
          {detail.error && <p className="form-error">{detail.error}</p>}
          <details open={!rows}>
            <summary>请求内容与执行结果</summary>
            <pre>
              {JSON.stringify(
                {
                  arguments: detail.arguments,
                  payload: detail.payload,
                  result: detail.result,
                },
                null,
                2,
              )}
            </pre>
            {detail.result_truncated && (
              <p>此处仅预览前 50 条；点击数据预览或导出读取完整数据。</p>
            )}
          </details>
          {detail.status === "AWAITING_CONFIRMATION" && (
            <div className="approval-box">
              <h3>
                <ShieldCheck size={21} />
                核对清单后确认执行
              </h3>
              <p>本操作会修改真实广告。确认与当前账户及以上请求内容绑定。</p>
              <label>
                是否执行？执行请输入“确认”，不执行则无需操作。
                <input
                  value={confirmation}
                  onChange={(e) => setConfirmation(e.target.value)}
                  placeholder="确认"
                  autoComplete="off"
                />
              </label>
              <button
                className="primary"
                disabled={confirmation !== "确认" || !!busy}
                onClick={() =>
                  action("approve", async () => {
                    const t = await api<Task>(
                      `/tasks/${detail.id}/approve`,
                      "POST",
                      {
                        confirm_text: confirmation,
                        payload_hash: detail.payload_hash,
                      },
                    );
                    setDetail(t);
                    setConfirmation("");
                    setNotice("已确认，后台正在排队执行");
                  })
                }
              >
                确认并提交执行
              </button>
            </div>
          )}
          <div className="button-row">
            {detail.status === "SUCCEEDED" && (
              <>
                <button
                  className="secondary"
                  onClick={() => loadRows(detail.id)}
                >
                  <Eye size={17} />
                  数据预览
                </button>
                <a
                  className="secondary"
                  href={`/api/tasks/${detail.id}/export`}
                >
                  <DownloadSimple size={17} />
                  导出 JSON
                </a>
              </>
            )}
            {["AWAITING_CONFIRMATION", "QUEUED", "WAITING"].includes(
              detail.status,
            ) && (
              <button
                className="text-button danger"
                disabled={!!busy}
                onClick={() =>
                  action("cancel", async () =>
                    setDetail(
                      await api(`/tasks/${detail.id}/cancel`, "POST", {}),
                    ),
                  )
                }
              >
                取消本地任务
              </button>
            )}
          </div>
          {rows && (
            <section className="row-preview">
              <h3>已保存数据 · {rows.total} 条</h3>
              {rows.rows.length ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        {Array.from(
                          new Set<string>(
                            rows.rows.flatMap((r: any) => Object.keys(r || {})),
                          ),
                        ).map((k) => (
                          <th key={k}>{k}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.rows.map((r: any, i: number) => (
                        <tr key={i}>
                          {Array.from(
                            new Set<string>(
                              rows.rows.flatMap((v: any) =>
                                Object.keys(v || {}),
                              ),
                            ),
                          ).map((k) => (
                            <td key={k}>
                              {typeof r[k] === "object"
                                ? JSON.stringify(r[k])
                                : String(r[k] ?? "")}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="hint">
                  任务已完成，但接口未返回数据记录。这不是仍在等待。
                </p>
              )}
              <div className="pagination">
                <button
                  disabled={!rowOffset}
                  onClick={() => loadRows(detail.id, rowOffset - 50)}
                >
                  上一页
                </button>
                <span>
                  {rowOffset + 1}–{Math.min(rowOffset + 50, rows.total)} /{" "}
                  {rows.total}
                </span>
                <button
                  disabled={rowOffset + 50 >= rows.total}
                  onClick={() => loadRows(detail.id, rowOffset + 50)}
                >
                  下一页
                </button>
              </div>
            </section>
          )}
        </Modal>
      )}
    </div>
  );
}
