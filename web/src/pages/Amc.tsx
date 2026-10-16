import { useEffect, useMemo, useState } from "react";
import {
  ArrowClockwise,
  ArrowRight,
  Info,
  Play,
  WarningCircle,
} from "@phosphor-icons/react";
import { api } from "../api";
import { AMC_MAX_DAYS, AMC_OPERATION } from "../lib/constants";
import { shiftDays, todayIn } from "../lib/dates";
import { daySpan, stamp } from "../lib/format";
import type { AmcOverview, AmcSource, Task } from "../lib/types";
import { DateRangePicker } from "../components/DateRangePicker";
import { TaskTable } from "../components/TaskTable";
import { Empty, PageHeader, PanelHeading, Segmented } from "../components/ui";
import { useWorkspace } from "../workspace";

type Mode = "template" | "sql";

const SQL_HINT =
  "只支持汇总查询（SUM / COUNT 等）；不支持 LIMIT、顶层 ORDER BY 和 SELECT *；user_id 等个人字段只能用于 COUNT(DISTINCT …)。";

/** Sponsored-ads tables first; audience-only tables are for audience building, not reporting. */
function rank(source: AmcSource) {
  if (source.tags.includes("Sponsored Ads")) return 0;
  return source.audienceOnly ? 2 : 1;
}

export function Amc() {
  const { selected, accountId, busy, action, setNotice, openTask, setError } =
    useWorkspace();
  const [overview, setOverview] = useState<AmcOverview | null>(null);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<Mode>("template");
  const [templateId, setTemplateId] = useState("ad-product-combo");
  const [sql, setSql] = useState("");
  const [runs, setRuns] = useState<Task[]>([]);
  const [search, setSearch] = useState("");
  const [showAudience, setShowAudience] = useState(false);
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const timeZone = selected?.timezone || "America/Los_Angeles";
  const today = todayIn(timeZone);
  // AMC data lags about 48 hours; the default window stops before that.
  const [startDate, setStartDate] = useState(() => shiftDays(today, -91));
  const [endDate, setEndDate] = useState(() => shiftDays(today, -2));

  async function load(refresh = false) {
    if (!accountId) return;
    setLoading(true);
    try {
      setOverview(
        await api<AmcOverview>(
          `/accounts/${accountId}/amc${refresh ? "?refresh=true" : ""}`,
        ),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  async function loadRuns() {
    if (!accountId) return;
    setRuns(
      await api<Task[]>(
        `/tasks?kind=report&operation=${AMC_OPERATION}&account_id=${accountId}&limit=20`,
      ),
    );
  }
  useEffect(() => {
    setOverview(null);
    void load();
    void loadRuns().catch(() => {});
    const id = setInterval(() => void loadRuns().catch(() => {}), 10000);
    return () => clearInterval(id);
  }, [accountId]);

  const template = overview?.templates.find((t) => t.id === templateId);
  const span = daySpan(startDate, endDate);
  const rangeError =
    span === null
      ? ""
      : span < 1
        ? "结束日期不能早于开始日期"
        : span > AMC_MAX_DAYS
          ? `AMC 单次查询最多 ${AMC_MAX_DAYS} 天`
          : "";
  const sources = useMemo(() => {
    const term = search.trim().toLowerCase();
    return (overview?.dataSources || [])
      .filter((s) => showAudience || !s.audienceOnly)
      .filter(
        (s) =>
          !term ||
          s.id.includes(term) ||
          s.columns.some((c) => c.name.includes(term)),
      )
      .sort((a, b) => rank(a) - rank(b) || a.id.localeCompare(b.id));
  }, [overview, search, showAudience]);

  function run() {
    if (rangeError || !span) return;
    void action("amc", async () => {
      const t = await api<Task>("/reports", "POST", {
        account_id: accountId,
        operation: AMC_OPERATION,
        arguments: {
          ...(mode === "template" ? { template: templateId } : { sql }),
          start_date: startDate,
          end_date: endDate,
          time_zone: timeZone,
        },
        idempotency_key: crypto.randomUUID(),
      });
      setNotice("AMC 查询已提交，Amazon 处理通常需要几分钟到几十分钟");
      await loadRuns();
      await openTask(t.id);
    });
  }

  return (
    <>
      <PageHeader
        title="AMC 洞察"
        description="用 Amazon Marketing Cloud 的事件级数据分析转化路径、品牌新客、曝光频次和搜索词。查询在 Amazon 后台运行，完成后在数据表格中查看。"
        actions={
          <button
            className="secondary"
            disabled={!accountId || loading}
            onClick={() => load(true)}
          >
            <ArrowClockwise size={16} className={loading ? "spin" : undefined} />
            刷新实例
          </button>
        }
      />
      {!accountId ? (
        <section className="panel">
          <Empty
            title="先连接一个广告账户"
            detail="AMC 实例按广告账户和站点开通，连接账户后这里会自动识别。"
          />
        </section>
      ) : !overview ? (
        <section className="panel">
          <p className="table-status">正在读取 AMC 实例…</p>
        </section>
      ) : !overview.available ? (
        <section className="panel amc-unavailable">
          <p className="callout warning" role="alert">
            <WarningCircle size={18} />
            {overview.reason}
          </p>
          <ol>
            <li>用该广告账户的 Amazon 账号登录 AMC 控制台，接受 AMC 条款。</li>
            <li>卖家账户首次进入时 Amazon 会自动创建实例，一般几分钟内完成。</li>
            <li>回到这里点击“刷新实例”。</li>
          </ol>
        </section>
      ) : (
        <>
          <section className="panel amc-instance">
            <dl className="summary-grid">
              <div>
                <dt>AMC 实例</dt>
                <dd className="mono">{overview.instance?.instanceId}</dd>
              </div>
              <div>
                <dt>状态</dt>
                <dd>
                  <span className="status succeeded">可用</span>
                </dd>
              </div>
              <div>
                <dt>类型</dt>
                <dd>{overview.instance?.instanceType || "—"}</dd>
              </div>
              <div>
                <dt>开通时间</dt>
                <dd>
                  {overview.instance?.creationDatetime
                    ? stamp(overview.instance.creationDatetime)
                    : "—"}
                </dd>
              </div>
              <div>
                <dt>可查询数据表</dt>
                <dd>
                  {(overview.dataSources || []).filter((s) => !s.audienceOnly).length} 个
                </dd>
              </div>
            </dl>
            <p className="callout info">
              <Info size={18} />
              AMC 数据约有 48 小时延迟。为保护隐私，覆盖人数过少的结果行会被 Amazon
              自动过滤：时间范围越短、分组越细（如按广告活动、按小时），结果越可能为空。
            </p>
          </section>

          <section className="panel">
            <PanelHeading
              title="运行分析"
              description="选择内置模板，或用自定义 SQL 查询 AMC 数据表。"
            >
              <Segmented
                label="查询方式"
                value={mode}
                options={[
                  { value: "template", label: "分析模板" },
                  { value: "sql", label: "自定义 SQL" },
                ]}
                onChange={setMode}
              />
            </PanelHeading>
            <div className="amc-run">
              {mode === "template" ? (
                <>
                  <div className="amc-templates" role="radiogroup" aria-label="分析模板">
                    {overview.templates.map((t) => (
                      <button
                        type="button"
                        role="radio"
                        aria-checked={t.id === templateId}
                        key={t.id}
                        onClick={() => setTemplateId(t.id)}
                      >
                        <strong>{t.name}</strong>
                        <span>{t.description}</span>
                        <small className="mono">{t.sources.join(" · ")}</small>
                      </button>
                    ))}
                  </div>
                  {template && (
                    <details className="payload">
                      <summary>查看 SQL</summary>
                      <pre>{template.sqlText}</pre>
                      <button
                        type="button"
                        className="text-button"
                        onClick={() => {
                          setSql(template.sqlText);
                          setMode("sql");
                        }}
                      >
                        复制到自定义 SQL 修改
                        <ArrowRight size={15} />
                      </button>
                    </details>
                  )}
                </>
              ) : (
                <>
                  <label>
                    AMC SQL
                    <textarea
                      className="code-editor"
                      rows={12}
                      spellCheck={false}
                      value={sql}
                      onChange={(e) => setSql(e.target.value)}
                      placeholder="SELECT ad_product_type, SUM(impressions) AS impressions FROM sponsored_ads_traffic GROUP BY ad_product_type"
                      aria-describedby="amc-sql-note"
                    />
                  </label>
                  <p id="amc-sql-note" className="field-note amc-sql-note">
                    {SQL_HINT}
                  </p>
                </>
              )}
              <div className="amc-run-row">
                <DateRangePicker
                  label="时间范围"
                  start={startDate}
                  end={endDate}
                  today={today}
                  maxDays={AMC_MAX_DAYS}
                  onChange={(start, end) => {
                    setStartDate(start);
                    setEndDate(end);
                  }}
                />
                <button
                  className="primary"
                  disabled={
                    !!busy || !span || !!rangeError || (mode === "sql" && !sql.trim())
                  }
                  onClick={run}
                >
                  <Play size={16} weight="fill" />
                  {busy === "amc" ? "正在提交…" : "运行查询"}
                </button>
              </div>
              <p className={rangeError ? "field-note error" : "field-note"}>
                {rangeError ||
                  `按账户时区（${timeZone}）计算；建议结束日期早于今天 2 天，最长 ${AMC_MAX_DAYS} 天。`}
              </p>
            </div>
          </section>

          <section className="panel">
            <PanelHeading
              title="运行记录"
              description="每 10 秒自动刷新；完成后点击“查看”，再进入数据表格查看结果。"
            />
            <TaskTable
              items={runs}
              emptyTitle="还没有 AMC 查询"
              emptyDetail="选择上方的分析模板并运行，结果会出现在这里。"
            />
          </section>

          <section className="panel">
            <PanelHeading
              title="可用数据表"
              description="写自定义 SQL 时参考的表和字段；广告相关的表排在前面。"
            >
              <input
                type="search"
                className="amc-search"
                placeholder="搜索表名或字段"
                aria-label="搜索表名或字段"
                value={search}
                onChange={(e) => setSearch(e.target.value.toLowerCase())}
              />
              <label className="check inline">
                <input
                  type="checkbox"
                  checked={showAudience}
                  onChange={(e) => setShowAudience(e.target.checked)}
                />
                <span>显示受众专用表</span>
              </label>
            </PanelHeading>
            {sources.length ? (
              <div className="amc-sources">
                {sources.map((s) => (
                  <details
                    key={s.id}
                    onToggle={(e) =>
                      setOpen((o) => ({ ...o, [s.id]: (e.target as HTMLDetailsElement).open }))
                    }
                  >
                    <summary>
                      <code>{s.id}</code>
                      {s.tags.map((t) => (
                        <span className="tag" key={t}>
                          {t}
                        </span>
                      ))}
                      {s.premium && <span className="tag">付费数据集</span>}
                      <small>{s.columns.length} 个字段</small>
                    </summary>
                    {open[s.id] && (
                      <>
                        <p className="hint">{s.description}</p>
                        <div className="table-scroll">
                          <table>
                            <thead>
                              <tr>
                                <th scope="col">字段</th>
                                <th scope="col">类型</th>
                                <th scope="col">用途</th>
                                <th scope="col">说明</th>
                              </tr>
                            </thead>
                            <tbody>
                              {s.columns.map((c) => (
                                <tr key={c.name}>
                                  <td className="mono">{c.name}</td>
                                  <td>{c.type}</td>
                                  <td>{c.kind === "METRIC" ? "指标" : "维度"}</td>
                                  <td className="wrap">{c.description}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </>
                    )}
                  </details>
                ))}
              </div>
            ) : (
              <Empty title="没有匹配的数据表" detail="换一个关键词试试。" />
            )}
          </section>
        </>
      )}
    </>
  );
}
