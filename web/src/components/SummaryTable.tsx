import { useMemo, useState } from "react";
import { CaretDown, CaretUp } from "@phosphor-icons/react";
import {
  columnLabel,
  derivedMetrics,
  formatCell,
  formatDerived,
  sortsByKey,
} from "../lib/reportColumns";
import type { SummaryBlock, SummaryResult } from "../lib/types";
import { Pagination } from "./ui";

type Sort = { key: string; desc: boolean };

/** Totals plus optional per-group rows; ratios are recomputed from the sums. */
export function SummaryTable({
  result,
  metrics,
  limit,
  loading,
}: {
  result: SummaryResult;
  metrics: string[];
  limit: number;
  loading: boolean;
}) {
  const derived = useMemo(() => derivedMetrics(metrics), [metrics]);
  const groupBy = result.group_by;
  const [sort, setSort] = useState<Sort | null>(null);
  const [offset, setOffset] = useState(0);
  const active: Sort =
    sort ||
    (groupBy && sortsByKey(groupBy)
      ? { key: "__key", desc: false }
      : {
          key: ["cost", "spend"].find((k) => metrics.includes(k)) || "__rows",
          desc: true,
        });

  const groups = useMemo(() => {
    const value = (g: SummaryBlock & { key: string | null }) => {
      if (active.key === "__key") return g.key ?? "";
      if (active.key === "__rows") return g.rows;
      const d = derived.find((x) => x.key === active.key);
      return d ? d.calc(g.sums) : g.sums[active.key];
    };
    return [...result.groups].sort((a, b) => {
      const x = value(a),
        y = value(b);
      if (x == null || y == null) return x == null ? 1 : -1;
      const order =
        typeof x === "number" && typeof y === "number"
          ? x - y
          : String(x).localeCompare(String(y), "zh-CN", { numeric: true });
      return active.desc ? -order : order;
    });
  }, [result, active.key, active.desc, derived]);

  function header(key: string, label: string, numeric = true) {
    const on = active.key === key;
    return (
      <th
        key={key}
        scope="col"
        className={numeric ? "numeric" : undefined}
        aria-sort={on ? (active.desc ? "descending" : "ascending") : "none"}
      >
        <button
          type="button"
          className="sort-button"
          onClick={() => {
            setSort({ key, desc: on ? !active.desc : numeric });
            setOffset(0);
          }}
        >
          {label}
          {on &&
            (active.desc ? <CaretDown size={12} /> : <CaretUp size={12} />)}
        </button>
      </th>
    );
  }

  function cells(block: SummaryBlock) {
    return (
      <>
        <td className="numeric">{block.rows.toLocaleString()}</td>
        {metrics.map((m) => (
          <td key={m} className="numeric">
            {formatCell(m, block.sums[m])}
          </td>
        ))}
        {derived.map((d) => (
          <td key={d.key} className="numeric">
            {formatDerived(d.format, d.calc(block.sums))}
          </td>
        ))}
      </>
    );
  }

  const page = groups.slice(offset, offset + limit);
  return (
    <>
      <div
        className="table-scroll data-table summary-table"
        aria-busy={loading}
        tabIndex={0}
        aria-label="汇总结果"
      >
        <table>
          <thead>
            <tr>
              {groupBy ? (
                header("__key", columnLabel(groupBy), false)
              ) : (
                <th scope="col">范围</th>
              )}
              {header("__rows", "行数")}
              {metrics.map((m) => header(m, columnLabel(m)))}
              {derived.map((d) => header(d.key, d.label))}
            </tr>
          </thead>
          <tbody>
            <tr className="total-row">
              <th scope="row">合计</th>
              {cells(result.total)}
            </tr>
            {page.map((g) => (
              <tr key={g.key ?? "\u0000"}>
                <th scope="row">
                  {g.key == null ? "（空）" : formatCell(groupBy || "", g.key)}
                </th>
                {cells(g)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {groupBy && (
        <Pagination
          label={`${groups.length.toLocaleString()} 组${result.truncated ? "（仅显示前 2,000 组）" : ""} · 第 ${
            Math.floor(offset / limit) + 1
          } / ${Math.max(1, Math.ceil(groups.length / limit))} 页`}
          canPrev={offset > 0}
          canNext={offset + limit < groups.length}
          onPrev={() => setOffset(Math.max(0, offset - limit))}
          onNext={() => setOffset(offset + limit)}
        />
      )}
    </>
  );
}
