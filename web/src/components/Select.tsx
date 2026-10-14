import {
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { CaretDown, Check } from "@phosphor-icons/react";
import { Popover } from "./Popover";

export type SelectOption = {
  value: string;
  label: string;
  description?: string;
  group?: string;
  prefix?: ReactNode;
};

const isChar = (e: KeyboardEvent) =>
  e.key.length === 1 && e.key !== " " && !e.ctrlKey && !e.metaKey && !e.altKey;

/**
 * Select-only combobox (WAI-ARIA APG pattern) that replaces the native
 * <select>, whose OS-drawn menu ignores the console's type, colour and
 * placement. Pass `name` to submit through FormData like a native field.
 */
export function Select({
  options,
  value,
  defaultValue,
  onChange,
  name,
  label,
  ariaLabel,
  placeholder = "请选择",
  disabled,
  size,
  className = "",
  menuWidth,
}: {
  options: SelectOption[];
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  name?: string;
  label?: string;
  ariaLabel?: string;
  placeholder?: string;
  disabled?: boolean;
  size?: "sm";
  className?: string;
  menuWidth?: number;
}) {
  const id = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const typed = useRef({ text: "", at: 0 });
  const [inner, setInner] = useState(defaultValue ?? options[0]?.value ?? "");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const current = value ?? inner;
  const index = options.findIndex((o) => o.value === current);
  const selected = options[index];
  const last = options.length - 1;

  useEffect(() => {
    if (open && active >= 0)
      document
        .getElementById(`${id}-opt-${active}`)
        ?.scrollIntoView({ block: "nearest" });
  }, [open, active, id]);

  function show(at = index) {
    if (disabled || !options.length) return;
    setActive(Math.max(at, 0));
    setOpen(true);
  }
  function commit(i: number) {
    setOpen(false);
    trigger.current?.focus();
    const o = options[i];
    if (!o || o.value === current) return;
    if (value === undefined) setInner(o.value);
    onChange?.(o.value);
  }
  /** Type-ahead: jump to the next option whose label starts with the typed text. */
  function match(key: string) {
    const t = typed.current,
      now = Date.now();
    t.text = (now - t.at > 700 ? "" : t.text) + key.toLowerCase();
    t.at = now;
    const from = (open ? active : index) + (t.text.length === 1 ? 1 : 0);
    for (let k = 0; k < options.length; k++) {
      const i = (Math.max(from, 0) + k) % options.length;
      if (options[i].label.toLowerCase().startsWith(t.text)) return i;
    }
    return undefined;
  }
  function onKeyDown(e: KeyboardEvent<HTMLButtonElement>) {
    if (!open) {
      if (["ArrowDown", "ArrowUp", "Enter", " "].includes(e.key)) show();
      else if (e.key === "Home") show(0);
      else if (e.key === "End") show(last);
      else if (isChar(e)) show(match(e.key) ?? index);
      else return;
      e.preventDefault();
      return;
    }
    const step: Record<string, number> = {
      ArrowDown: 1,
      ArrowUp: -1,
      PageDown: 8,
      PageUp: -8,
    };
    if (e.key in step && !e.altKey)
      setActive(Math.min(Math.max(active + step[e.key], 0), last));
    else if (e.key === "Home") setActive(0);
    else if (e.key === "End") setActive(last);
    else if (["Enter", " ", "ArrowUp", "ArrowDown"].includes(e.key))
      commit(active);
    else if (e.key === "Escape") {
      e.stopPropagation(); // keep an enclosing modal open
      setOpen(false);
    } else if (e.key === "Tab") {
      setOpen(false);
      return;
    } else if (isChar(e)) {
      const i = match(e.key);
      if (i !== undefined) setActive(i);
    } else return;
    e.preventDefault();
  }

  const sections: { group?: string; items: number[] }[] = [];
  options.forEach((o, i) => {
    const tail = sections[sections.length - 1];
    if (!tail || tail.group !== o.group)
      sections.push({ group: o.group, items: [i] });
    else tail.items.push(i);
  });
  const renderOption = (i: number) => {
    const o = options[i];
    return (
      <div
        key={o.value}
        id={`${id}-opt-${i}`}
        role="option"
        aria-selected={i === index}
        className="select-option"
        data-active={i === active || undefined}
        onClick={() => commit(i)}
        onPointerMove={() => i !== active && setActive(i)}
      >
        {o.prefix}
        <span className="select-option-text">
          {o.label}
          {o.description && <small>{o.description}</small>}
        </span>
        {i === index && (
          <Check size={15} weight="bold" className="select-check" />
        )}
      </div>
    );
  };

  const control = (
    <>
      <button
        ref={trigger}
        type="button"
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? `${id}-list` : undefined}
        aria-activedescendant={open ? `${id}-opt-${active}` : undefined}
        aria-labelledby={label ? `${id}-label` : undefined}
        aria-label={label ? undefined : ariaLabel}
        className={`select-trigger ${size ?? ""} ${className}`}
        disabled={disabled}
        onClick={() => (open ? setOpen(false) : show())}
        onKeyDown={onKeyDown}
        onKeyUp={(e) => e.key === " " && e.preventDefault()}
      >
        <span className={selected ? "select-value" : "select-value placeholder"}>
          {selected?.prefix}
          {selected ? selected.label : placeholder}
        </span>
        <CaretDown size={14} weight="bold" className="select-caret" />
      </button>
      {name && <input type="hidden" name={name} value={current} />}
      {open && (
        <Popover
          anchor={trigger}
          onDismiss={() => setOpen(false)}
          matchWidth
          minWidth={menuWidth}
          maxHeight={320}
          className="select-menu"
          id={`${id}-list`}
          role="listbox"
          aria-labelledby={label ? `${id}-label` : undefined}
          aria-label={label ? undefined : ariaLabel}
          onMouseDown={(e) => e.preventDefault()}
        >
          {sections.map((s, n) =>
            s.group ? (
              <div key={s.group} role="group" aria-labelledby={`${id}-g${n}`}>
                <div className="select-group" id={`${id}-g${n}`} role="presentation">
                  {s.group}
                </div>
                {s.items.map(renderOption)}
              </div>
            ) : (
              s.items.map(renderOption)
            ),
          )}
        </Popover>
      )}
    </>
  );
  if (!label) return control;
  return (
    <div className="field">
      <span
        className="field-label"
        id={`${id}-label`}
        onClick={() => trigger.current?.focus()}
      >
        {label}
      </span>
      {control}
    </div>
  );
}
