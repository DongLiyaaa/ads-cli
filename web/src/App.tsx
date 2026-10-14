import { useEffect, useEffectEvent, useState, type ReactNode } from "react";
import { CheckCircle, WarningCircle, X } from "@phosphor-icons/react";
import { api, setCsrf } from "./api";
import { PAGE_SIZE } from "./lib/constants";
import type {
  Account,
  Capability,
  LogEntry,
  MCPToken,
  Overview as OverviewData,
  Task,
} from "./lib/types";
import { WorkspaceContext, type Workspace } from "./workspace";
import { Sidebar } from "./components/Sidebar";
import { Topbar } from "./components/Topbar";
import { TaskDetail } from "./components/TaskDetail";
import { AccountModal } from "./components/AccountModal";
import { TokenModal } from "./components/TokenModal";
import { Login } from "./pages/Login";
import { Overview } from "./pages/Overview";
import { Accounts } from "./pages/Accounts";
import { Reports } from "./pages/Reports";
import { Operations } from "./pages/Operations";
import { Approvals } from "./pages/Approvals";
import { Tokens } from "./pages/Tokens";
import { Logs } from "./pages/Logs";

const pages: Record<string, () => ReactNode> = {
  "/": Overview,
  "/accounts": Accounts,
  "/reports": Reports,
  "/operations": Operations,
  "/approvals": Approvals,
  "/tokens": Tokens,
  "/logs": Logs,
};

/** The approvals page opens on pending plans; every other page shows all statuses. */
function defaultFilter(path: string) {
  return path === "/approvals" ? "AWAITING_CONFIRMATION" : "";
}

export default function App() {
  const [user, setUser] = useState<string | null>(null),
    [booting, setBooting] = useState(true),
    [page, setPage] = useState(location.pathname);
  const [accounts, setAccounts] = useState<Account[]>([]),
    [accountId, setAccountId] = useState(""),
    [tasks, setTasks] = useState<Task[]>([]),
    [tokens, setTokens] = useState<MCPToken[]>([]),
    [logs, setLogs] = useState<LogEntry[]>([]),
    [catalog, setCatalog] = useState<Capability[]>([]),
    [overview, setOverview] = useState<OverviewData>({});
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(""),
    [synced, setSynced] = useState(""),
    [offset, setOffset] = useState(0),
    [filter, setFilter] = useState(() => defaultFilter(location.pathname));
  const [accountModal, setAccountModal] = useState(false),
    [tokenModal, setTokenModal] = useState(false),
    [oneTime, setOneTime] = useState(""),
    [detail, setDetail] = useState<Task | null>(null);
  const selected = accounts.find((a) => a.id === accountId);

  function navigate(path: string) {
    history.pushState({}, "", path);
    setPage(path);
    setOffset(0);
    setFilter(defaultFilter(path));
    setOneTime("");
    setDetail(null);
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
    const change = () => {
      setPage(location.pathname);
      setOffset(0);
      setFilter(defaultFilter(location.pathname));
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
  useEffect(() => {
    if (!notice) return;
    const id = setTimeout(() => setNotice(""), 4000);
    return () => clearTimeout(id);
  }, [notice]);
  async function refresh() {
    const [a, o, c, t] = await Promise.all([
      api<Account[]>("/accounts"),
      api<OverviewData>("/overview"),
      api<Capability[]>("/capabilities"),
      api<Task[]>(
        `/tasks?offset=${offset}&limit=${PAGE_SIZE}${filter ? "&status=" + filter : ""}`,
      ),
    ]);
    setAccounts(a);
    setOverview(o);
    setCatalog(c);
    setTasks(t);
    setAccountId((old) => (a.some((v) => v.id === old) ? old : a[0]?.id || ""));
    setSynced(new Date().toLocaleTimeString("zh-CN", { hour12: false }));
    if (page === "/tokens") setTokens(await api("/tokens"));
    if (page === "/logs")
      setLogs(await api(`/logs?offset=${offset}&limit=${PAGE_SIZE}`));
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
  async function action(name: string, fn: () => Promise<unknown>) {
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
      setDetail(await api<Task>(`/tasks/${id}`));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  function closeTask() {
    setDetail(null);
    if (new URLSearchParams(location.search).has("task"))
      history.replaceState({}, "", location.pathname);
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
  function logout() {
    api("/logout", "POST", {})
      .then(() => {
        clearSession();
        setError("");
      })
      .catch((e) => setError(e.message));
  }

  if (booting) return <div className="boot">正在连接 Ads Console…</div>;
  if (!user) return <Login onLogin={setUser} />;

  const workspace: Workspace = {
    user,
    page,
    navigate,
    accounts,
    accountId,
    setAccountId,
    selected,
    tasks,
    tokens,
    logs,
    catalog,
    overview,
    busy,
    action,
    openTask,
    copy,
    setNotice,
    setError,
    offset,
    setOffset,
    filter,
    setFilter,
    openAccountModal: () => setAccountModal(true),
    openTokenModal: () => setTokenModal(true),
    oneTime,
    setOneTime,
  };
  const Page = pages[page] || Overview;
  return (
    <WorkspaceContext.Provider value={workspace}>
      <div className="shell">
        <Sidebar onLogout={logout} />
        <main className="main">
          <Topbar synced={synced} onRefresh={() => action("refresh", refresh)} />
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
          <div className="page" key={page}>
            <Page />
          </div>
          <footer className="main-footer">
            <span>Amazon Ads Ops Workbench</span>
            <span>
              PostgreSQL 持久化 · API 并发上限{" "}
              {overview.max_api_concurrency || 3}
            </span>
          </footer>
        </main>
        {accountModal && <AccountModal close={() => setAccountModal(false)} />}
        {tokenModal && <TokenModal close={() => setTokenModal(false)} />}
        {detail && (
          <TaskDetail
            key={detail.id}
            task={detail}
            setTask={setDetail}
            close={closeTask}
          />
        )}
      </div>
    </WorkspaceContext.Provider>
  );
}
