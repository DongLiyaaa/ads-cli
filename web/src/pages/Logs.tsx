import { PAGE_SIZE } from "../lib/constants";
import { accountName, stamp } from "../lib/format";
import { Empty, PageHeader, Pagination, Status } from "../components/ui";
import { useWorkspace } from "../workspace";

export function Logs() {
  const { logs, accounts, offset, setOffset, openTask } = useWorkspace();
  return (
    <>
      <PageHeader
        title="执行日志"
        description="记录请求、审批、排队、Amazon 响应及异常，不记录密钥或签名下载地址。"
      />
      <section className="panel">
        {logs.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>时间</th>
                  <th>动作</th>
                  <th>状态</th>
                  <th>账户</th>
                  <th>Token 名称</th>
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
                    <td>{l.account_id ? accountName(accounts, l.account_id) : "—"}</td>
                    <td>
                      {l.token_name ? (
                        <>
                          <strong>{l.token_name}</strong>
                          <small className="mono">{l.token_prefix}…</small>
                        </>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>
                      {l.task_id ? (
                        <button
                          className="text-button mono"
                          onClick={() => openTask(l.task_id!)}
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
        <Pagination
          label={`第 ${offset / PAGE_SIZE + 1} 页`}
          canPrev={offset > 0}
          canNext={logs.length >= PAGE_SIZE}
          onPrev={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          onNext={() => setOffset(offset + PAGE_SIZE)}
        />
      </section>
    </>
  );
}
