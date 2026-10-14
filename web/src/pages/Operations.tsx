import { useEffect, useMemo, useState } from "react";
import {
  MagnifyingGlass,
  Plus,
  ShieldCheck,
  TerminalWindow,
  WarningCircle,
} from "@phosphor-icons/react";
import { api } from "../api";
import { parseArguments } from "../lib/format";
import {
  argumentDefaults,
  describeOperation,
  placeholderFor,
} from "../lib/operations";
import type { Capability, Task } from "../lib/types";
import { PageHeader, Segmented } from "../components/ui";
import { useWorkspace } from "../workspace";

type Kind = "read" | "write";
type Product = "ALL" | "SP" | "SB" | "SD";

export function Operations() {
  const { catalog, accountId, busy, action, setNotice, openTask, navigate } =
    useWorkspace();
  const [kind, setKind] = useState<Kind>("read");
  const [product, setProduct] = useState<Product>("ALL");
  const [query, setQuery] = useState("");
  const [operation, setOperation] = useState("");
  const [argumentsText, setArgumentsText] = useState("{}");
  const selectedOp = catalog.find((c) => c.operation === operation);
  const info = selectedOp ? describeOperation(selectedOp.operation) : null;
  const parsed = parseArguments(argumentsText);
  const missing = (selectedOp?.inputSchema.required || []).filter(
    (name) => parsed.value && !(name in parsed.value),
  );

  function select(c?: Capability) {
    if (!c) return;
    setOperation(c.operation);
    setArgumentsText(argumentDefaults(c));
  }
  useEffect(() => {
    if (operation || !catalog.length) return;
    select(
      catalog.find((c) => c.operation === "campaigns.list") ||
        catalog.find((c) => c.kind === "read"),
    );
  }, [catalog.length]);

  const counts = useMemo(
    () => ({
      read: catalog.filter((c) => c.kind === "read").length,
      write: catalog.filter((c) => c.kind === "write").length,
    }),
    [catalog],
  );
  const groups = useMemo(() => {
    const q = query.trim().toLowerCase();
    const result = new Map<string, { label: string; items: Capability[] }>();
    for (const c of catalog) {
      if (c.kind !== kind) continue;
      const d = describeOperation(c.operation);
      if (product !== "ALL" && d.product !== product) continue;
      if (
        q &&
        !c.operation.toLowerCase().includes(q) &&
        !d.title.toLowerCase().includes(q)
      )
        continue;
      const key = d.product + " · " + d.resource;
      if (!result.has(key)) result.set(key, { label: key, items: [] });
      result.get(key)!.items.push(c);
    }
    return Array.from(result.values());
  }, [catalog, kind, product, query]);

  function insertField(name: string) {
    if (!parsed.value || !selectedOp) return;
    const schema = selectedOp.inputSchema.properties[name];
    setArgumentsText(
      JSON.stringify(
        { ...parsed.value, [name]: placeholderFor(schema) },
        null,
        2,
      ),
    );
  }

  const isWrite = selectedOp?.kind === "write";
  return (
    <>
      <PageHeader
        title="广告操作"
        description="查询直接执行；变更只生成待确认计划。复用 CLI 的操作契约，不开放任意命令执行。"
      />
      <section className="panel operation-layout">
        <aside className="operation-picker" aria-label="操作目录">
          <Segmented
            label="操作类型"
            value={kind}
            options={[
              { value: "read", label: `查询 · ${counts.read}` },
              { value: "write", label: `变更计划 · ${counts.write}` },
            ]}
            onChange={(v) => {
              setKind(v);
              select(
                catalog.find(
                  (c) =>
                    c.kind === v &&
                    (product === "ALL" ||
                      describeOperation(c.operation).product === product),
                ),
              );
            }}
          />
          <Segmented
            label="广告类型"
            value={product}
            options={(["ALL", "SP", "SB", "SD"] as Product[]).map((p) => ({
              value: p,
              label: p === "ALL" ? "全部" : p,
            }))}
            onChange={setProduct}
          />
          <label className="search">
            <span className="visually-hidden">搜索操作</span>
            <MagnifyingGlass size={16} aria-hidden="true" />
            <input
              type="search"
              placeholder="搜索名称或操作，如 budget"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <div className="operation-list">
            {groups.length ? (
              groups.map((g) => (
                <div key={g.label} className="operation-group">
                  <h3>{g.label}</h3>
                  {g.items.map((c) => (
                    <button
                      type="button"
                      key={c.operation}
                      aria-pressed={c.operation === operation}
                      onClick={() => select(c)}
                    >
                      {describeOperation(c.operation).title}
                      <small className="mono">{c.operation}</small>
                    </button>
                  ))}
                </div>
              ))
            ) : (
              <p className="hint">没有匹配的操作，换个关键词试试。</p>
            )}
          </div>
        </aside>
        <div className="operation-editor">
          {selectedOp && info ? (
            <>
              <header className="operation-head">
                <div>
                  <h2>{info.title}</h2>
                  <p className="mono">{selectedOp.operation}</p>
                </div>
                <span className={isWrite ? "status awaiting_confirmation" : "status queued"}>
                  {info.product} · {isWrite ? "变更计划" : "查询"}
                </span>
              </header>
              {isWrite && (
                <p className="callout warning">
                  <ShieldCheck size={18} weight="fill" />
                  提交后只生成待确认计划，不会修改广告；需在“待确认操作”中输入“确认”后才会执行。
                </p>
              )}
              <div className="operation-columns">
                <div className="editor-column">
                  <label>
                    <span className="label-row">
                      操作参数（JSON）
                      <span className={parsed.error ? "json-state error" : "json-state"}>
                        {parsed.error ? "格式有误" : "格式正确"}
                      </span>
                    </span>
                    <textarea
                      className="code-editor"
                      rows={14}
                      spellCheck={false}
                      aria-invalid={!!parsed.error}
                      value={argumentsText}
                      onChange={(e) => setArgumentsText(e.target.value)}
                    />
                  </label>
                  {parsed.error ? (
                    <p className="field-note error">{parsed.error}</p>
                  ) : missing.length ? (
                    <p className="field-note warning">
                      <WarningCircle size={15} />
                      缺少必填参数：{missing.join("、")}
                    </p>
                  ) : null}
                  <div className="button-row">
                    <button
                      className="primary"
                      disabled={!accountId || !!busy || !!parsed.error}
                      onClick={() =>
                        action("operation", async () => {
                          const { value, error } = parseArguments(argumentsText);
                          if (!value) throw new Error(error);
                          const t = await api<Task>(
                            isWrite ? "/plans" : "/queries",
                            "POST",
                            {
                              account_id: accountId,
                              operation,
                              arguments: value,
                              idempotency_key: crypto.randomUUID(),
                            },
                          );
                          setNotice(
                            isWrite
                              ? "已生成待确认清单，尚未执行广告变更"
                              : "查询已入队",
                          );
                          await openTask(t.id);
                        })
                      }
                    >
                      {isWrite ? (
                        <ShieldCheck size={17} />
                      ) : (
                        <TerminalWindow size={17} />
                      )}
                      {busy === "operation"
                        ? "正在提交…"
                        : isWrite
                          ? "生成待确认计划"
                          : "提交查询"}
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => setArgumentsText(argumentDefaults(selectedOp))}
                    >
                      恢复默认参数
                    </button>
                    {!accountId && (
                      <button
                        type="button"
                        className="text-button"
                        onClick={() => navigate("/accounts")}
                      >
                        先连接广告账户
                      </button>
                    )}
                  </div>
                </div>
                <div className="schema">
                  <h3>参数说明</h3>
                  {Object.entries(selectedOp.inputSchema.properties).length ? (
                    Object.entries(selectedOp.inputSchema.properties).map(
                      ([name, s]) => {
                        const present = !!parsed.value && name in parsed.value;
                        return (
                          <div key={name} className="schema-field">
                            <div className="schema-name">
                              <strong className="mono">{name}</strong>
                              {selectedOp.inputSchema.required.includes(name) && (
                                <b>必填</b>
                              )}
                              <button
                                type="button"
                                className="text-button"
                                disabled={present || !parsed.value}
                                onClick={() => insertField(name)}
                                aria-label={
                                  present ? `${name} 已填写` : `添加参数 ${name}`
                                }
                              >
                                {present ? "已填写" : (
                                  <>
                                    <Plus size={13} />
                                    添加
                                  </>
                                )}
                              </button>
                            </div>
                            {s.description && s.description !== name && (
                              <p>{s.description}</p>
                            )}
                            <small>
                              {s.enum ? s.enum.join(" / ") : s.type}
                              {s.default !== undefined &&
                                ` · 默认 ${JSON.stringify(s.default)}`}
                            </small>
                          </div>
                        );
                      },
                    )
                  ) : (
                    <p className="hint">此操作不需要参数。</p>
                  )}
                </div>
              </div>
            </>
          ) : (
            <p className="hint">正在加载操作目录…</p>
          )}
        </div>
      </section>
    </>
  );
}
