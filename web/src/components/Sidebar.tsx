import { useEffect, useRef } from "react";
import { PlugsConnected, SignOut } from "@phosphor-icons/react";
import { navigation } from "../lib/constants";
import { useWorkspace } from "../workspace";

export function Sidebar({ onLogout }: { onLogout: () => void }) {
  const { user, page, navigate, overview } = useWorkspace();
  const nav = useRef<HTMLElement>(null);
  const pending = overview.tasks_by_status?.AWAITING_CONFIRMATION || 0;
  useEffect(() => {
    const reveal = () => {
      if (innerWidth <= 800)
        nav.current
          ?.querySelector(".active")
          ?.scrollIntoView({ block: "nearest", inline: "nearest" });
    };
    reveal();
    addEventListener("resize", reveal);
    return () => removeEventListener("resize", reveal);
  }, [page]);
  return (
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
          <PlugsConnected size={21} weight="bold" />
        </span>
        <span>
          Ads Console<small>MCP 控制台</small>
        </span>
      </a>
      <p className="nav-label">工作空间</p>
      <nav ref={nav} aria-label="主导航">
        {navigation.map((n) => {
          const active = page === n.path;
          return (
            <a
              key={n.path}
              href={n.path}
              className={active ? "active" : ""}
              aria-current={active ? "page" : undefined}
              onClick={(e) => {
                e.preventDefault();
                navigate(n.path);
              }}
            >
              <n.icon size={19} weight={active ? "fill" : "regular"} />
              {n.label}
              {n.path === "/approvals" && pending > 0 && (
                <b className="nav-badge" aria-label={`${pending} 项待确认`}>
                  {pending}
                </b>
              )}
            </a>
          );
        })}
      </nav>
      <footer>
        <span className="avatar" aria-hidden="true">
          {user.slice(0, 1).toUpperCase()}
        </span>
        <span className="user">
          {user}
          <small>工作空间管理员</small>
        </span>
        <button
          aria-label="退出登录"
          data-tip="退出登录"
          data-tip-align="end"
          data-tip-side="top"
          className="icon-button"
          onClick={onLogout}
        >
          <SignOut size={19} />
        </button>
      </footer>
    </aside>
  );
}
