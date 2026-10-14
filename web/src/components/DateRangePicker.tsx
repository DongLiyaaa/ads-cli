import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import {
  CalendarBlank,
  CaretDown,
  CaretLeft,
  CaretRight,
} from "@phosphor-icons/react";
import {
  daysInMonth,
  formatDay,
  monthStart,
  shiftDays,
  shiftMonths,
  weekday,
} from "../lib/dates";
import { daySpan } from "../lib/format";
import { Popover } from "./Popover";

const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];
const ARROWS: Record<string, number> = {
  ArrowLeft: -1,
  ArrowRight: 1,
  ArrowUp: -7,
  ArrowDown: 7,
};

function presets(today: string) {
  const y = shiftDays(today, -1),
    month = monthStart(today);
  return [
    { label: "昨天", range: [y, y] },
    { label: "近 7 天", range: [shiftDays(y, -6), y] },
    { label: "近 14 天", range: [shiftDays(y, -13), y] },
    { label: "近 30 天", range: [shiftDays(y, -29), y] },
    { label: "本月", range: [month, y], disabled: y < month },
    { label: "上个月", range: [shiftMonths(month, -1), shiftDays(month, -1)] },
  ];
}

function monthCells(month: string) {
  const lead = weekday(month),
    days = daysInMonth(month);
  return Array.from({ length: 42 }, (_, i) => {
    const day = i - lead + 1;
    return day >= 1 && day <= days
      ? month.slice(0, 8) + String(day).padStart(2, "0")
      : null;
  });
}

/**
 * Report date range: presets for the common windows plus a two-month
 * calendar (one month on phones). Picking is two clicks — start, then end —
 * and days that would exceed `maxDays` are unreachable once a start is set.
 */
export function DateRangePicker({
  label,
  start,
  end,
  today,
  maxDays,
  onChange,
}: {
  label: string;
  start: string;
  end: string;
  today: string;
  maxDays: number;
  onChange: (start: string, end: string) => void;
}) {
  const id = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const days = useRef<HTMLDivElement>(null);
  const moveFocus = useRef(false);
  const [open, setOpen] = useState(false);
  const [count, setCount] = useState(2);
  const [view, setView] = useState(monthStart(today));
  const [focus, setFocus] = useState(today);
  const [anchor, setAnchor] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const months = Array.from({ length: count }, (_, i) => shiftMonths(view, i));
  const lastMonth = months[months.length - 1];
  const span = daySpan(start, end);

  useEffect(() => {
    if (!open || !moveFocus.current) return;
    moveFocus.current = false;
    days.current
      ?.querySelector<HTMLElement>(`[data-date="${focus}"]`)
      ?.focus({ preventScroll: true });
  });

  function show() {
    const single = window.matchMedia("(max-width: 640px)").matches;
    const target = end || shiftDays(today, -1);
    setCount(single ? 1 : 2);
    setView(shiftMonths(monthStart(target), single ? 0 : -1));
    setFocus(target);
    setAnchor(null);
    setHover(null);
    moveFocus.current = true;
    setOpen(true);
  }
  function hide(refocus = true) {
    setOpen(false);
    setAnchor(null);
    if (refocus) trigger.current?.focus();
  }
  function blocked(d: string) {
    return d > today || (anchor !== null && daySpan(...order(anchor, d))! > maxDays);
  }
  function pick(d: string) {
    if (blocked(d)) return;
    if (anchor === null) {
      setAnchor(d);
      setHover(d);
      setFocus(d);
      return;
    }
    onChange(...order(anchor, d));
    hide();
  }
  function goTo(d: string) {
    if (d < view) setView(monthStart(d));
    else if (monthStart(d) > lastMonth)
      setView(shiftMonths(monthStart(d), 1 - count));
    setFocus(d);
    if (anchor) setHover(d);
    moveFocus.current = true;
  }
  function onDaysKey(e: KeyboardEvent) {
    if (e.key in ARROWS) goTo(shiftDays(focus, ARROWS[e.key]));
    else if (e.key === "PageUp" || e.key === "PageDown")
      goTo(shiftMonths(focus, e.key === "PageUp" ? -1 : 1));
    else if (e.key === "Home") goTo(shiftDays(focus, -weekday(focus)));
    else if (e.key === "End") goTo(shiftDays(focus, 6 - weekday(focus)));
    else return;
    e.preventDefault();
  }
  function onPanelKey(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      hide();
    } else if (e.key === "Tab") {
      // The panel lives in <body>; keep Tab cycling inside it.
      const nodes = Array.from(
        e.currentTarget.querySelectorAll<HTMLElement>(
          'button:not(:disabled):not([tabindex="-1"])',
        ),
      );
      const at = nodes.indexOf(document.activeElement as HTMLElement);
      const next = (at + (e.shiftKey ? -1 : 1) + nodes.length) % nodes.length;
      e.preventDefault();
      nodes[next]?.focus();
    }
  }

  const preview = anchor && hover && !blocked(hover) ? hover : anchor;
  const [lo, hi] = anchor ? order(anchor, preview!) : [start, end];
  const tabDate =
    focus >= view && monthStart(focus) <= lastMonth ? focus : view;
  const renderDay = (d: string | null, i: number) => {
    if (!d) return <span key={i} className="date-empty" />;
    const off = blocked(d),
      first = d === lo,
      final = d === hi;
    const cls = [
      "date-day",
      lo && hi && d > lo && d < hi && "in-range",
      first && "range-start",
      final && "range-end",
      d === today && "today",
    ]
      .filter(Boolean)
      .join(" ");
    return (
      <button
        type="button"
        key={d}
        data-date={d}
        className={cls}
        tabIndex={d === tabDate ? 0 : -1}
        aria-disabled={off || undefined}
        aria-current={d === today ? "date" : undefined}
        aria-label={`${+d.slice(5, 7)}月${+d.slice(8)}日 星期${
          WEEKDAYS[weekday(d)]
        }${first ? "，开始日期" : ""}${final ? "，结束日期" : ""}`}
        onClick={() => pick(d)}
        onPointerEnter={() => anchor && setHover(d)}
        onFocus={() => setFocus(d)}
      >
        <span>{+d.slice(8)}</span>
      </button>
    );
  };

  return (
    <div className="field">
      <span
        className="field-label"
        id={`${id}-label`}
        onClick={() => trigger.current?.focus()}
      >
        {label}
      </span>
      <button
        ref={trigger}
        type="button"
        className="select-trigger date-trigger"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-labelledby={`${id}-label ${id}-value`}
        onClick={() => (open ? hide() : show())}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown" && !open) {
            e.preventDefault();
            show();
          }
        }}
      >
        <CalendarBlank size={16} className="date-icon" />
        <span className="select-value" id={`${id}-value`}>
          {start && end ? `${formatDay(start)} – ${formatDay(end)}` : "选择日期"}
        </span>
        {span !== null && span > 0 && (
          <span className="date-count">{span} 天</span>
        )}
        <CaretDown size={14} weight="bold" className="select-caret" />
      </button>
      {open && (
        <Popover
          anchor={trigger}
          onDismiss={() => hide(false)}
          maxHeight={640}
          className="date-popover"
          role="dialog"
          aria-label="选择日期范围"
          onKeyDown={onPanelKey}
        >
          <div className="date-presets" role="group" aria-label="快捷范围">
            {presets(today).map((p) => (
              <button
                type="button"
                key={p.label}
                disabled={p.disabled}
                aria-pressed={p.range[0] === start && p.range[1] === end}
                onClick={() => {
                  onChange(p.range[0], p.range[1]);
                  hide();
                }}
              >
                {p.label}
              </button>
            ))}
          </div>
          <div className="date-main">
            <button
              type="button"
              className="icon-button date-nav prev"
              aria-label="上个月"
              onClick={() => setView(shiftMonths(view, -1))}
            >
              <CaretLeft size={16} weight="bold" />
            </button>
            <button
              type="button"
              className="icon-button date-nav next"
              aria-label="下个月"
              disabled={lastMonth >= monthStart(today)}
              onClick={() => setView(shiftMonths(view, 1))}
            >
              <CaretRight size={16} weight="bold" />
            </button>
            <div
              className="date-months"
              ref={days}
              onKeyDown={onDaysKey}
              onPointerLeave={() => anchor && setHover(anchor)}
            >
              {months.map((m) => {
                const title = `${m.slice(0, 4)} 年 ${+m.slice(5, 7)} 月`;
                return (
                  <div className="date-month" key={m} role="group" aria-label={title}>
                    <h3>{title}</h3>
                    <div className="date-grid">
                      {WEEKDAYS.map((w) => (
                        <span className="date-weekday" key={w} aria-hidden="true">
                          {w}
                        </span>
                      ))}
                      {monthCells(m).map(renderDay)}
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="date-foot">
              <span aria-live="polite">
                {anchor ? (
                  <>
                    开始 <strong>{formatDay(anchor)}</strong>，再选结束日期
                  </>
                ) : start && end ? (
                  <>
                    <strong>
                      {formatDay(start)} – {formatDay(end)}
                    </strong>
                    {span ? ` · 共 ${span} 天` : ""}
                  </>
                ) : (
                  "先选开始日期"
                )}
              </span>
              <span>单次最多 {maxDays} 天</span>
            </div>
          </div>
        </Popover>
      )}
    </div>
  );
}

function order(a: string, b: string): [string, string] {
  return a <= b ? [a, b] : [b, a];
}
