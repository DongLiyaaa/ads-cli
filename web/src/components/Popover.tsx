import {
  useEffect,
  useEffectEvent,
  useLayoutEffect,
  useRef,
  type HTMLAttributes,
  type RefObject,
} from "react";
import { createPortal } from "react-dom";

const GAP = 6;
const EDGE = 8;

/**
 * Floating panel anchored to a trigger. Rendered into <body> with fixed
 * positioning so modal and table overflow never clip it; flips above the
 * trigger when there is more room there. Positions are written through
 * CSSOM, which the console's strict CSP allows.
 */
export function Popover({
  anchor,
  onDismiss,
  matchWidth,
  minWidth = 0,
  maxHeight = 360,
  className = "",
  children,
  ...rest
}: {
  anchor: RefObject<HTMLElement | null>;
  onDismiss: () => void;
  matchWidth?: boolean;
  minWidth?: number;
  maxHeight?: number;
} & HTMLAttributes<HTMLDivElement>) {
  const panel = useRef<HTMLDivElement>(null);
  const dismiss = useEffectEvent(onDismiss);
  const place = useEffectEvent(() => {
    const a = anchor.current,
      p = panel.current;
    if (!a || !p) return;
    const r = a.getBoundingClientRect();
    const vw = document.documentElement.clientWidth,
      vh = window.innerHeight;
    if (matchWidth) p.style.width = Math.max(r.width, minWidth) + "px";
    else if (minWidth) p.style.minWidth = minWidth + "px";
    p.style.maxWidth = vw - EDGE * 2 + "px";
    const width = p.offsetWidth;
    const below = vh - r.bottom - GAP - EDGE,
      above = r.top - GAP - EDGE;
    // scrollHeight is the full content height even while capped, so the
    // panel never has to be uncapped (which would reset its scroll offset).
    const natural = Math.min(
      p.scrollHeight + p.offsetHeight - p.clientHeight,
      maxHeight,
    );
    const up = natural > below && above > below;
    const height = Math.min(natural, up ? above : below);
    p.style.maxHeight = Math.max(height, 120) + "px";
    // Start-align with the trigger; if that overflows, end-align instead.
    const left = r.left + width > vw - EDGE ? r.right - width : r.left;
    p.style.left = Math.min(Math.max(left, EDGE), vw - width - EDGE) + "px";
    p.style.top = (up ? r.top - GAP - p.offsetHeight : r.bottom + GAP) + "px";
    p.dataset.side = up ? "top" : "bottom";
  });
  useLayoutEffect(() => {
    place();
  });
  useEffect(() => {
    const onPointer = (e: PointerEvent) => {
      const t = e.target as Node;
      if (!panel.current?.contains(t) && !anchor.current?.contains(t))
        dismiss();
    };
    const onMove = (e?: Event) => {
      if (e?.target instanceof Node && panel.current?.contains(e.target))
        return;
      place();
    };
    const resize = new ResizeObserver(() => place());
    if (panel.current) resize.observe(panel.current);
    document.addEventListener("pointerdown", onPointer, true);
    window.addEventListener("resize", onMove);
    window.addEventListener("scroll", onMove, true);
    return () => {
      resize.disconnect();
      document.removeEventListener("pointerdown", onPointer, true);
      window.removeEventListener("resize", onMove);
      window.removeEventListener("scroll", onMove, true);
    };
  }, [anchor]);
  return createPortal(
    <div ref={panel} className={`popover ${className}`} {...rest}>
      {children}
    </div>,
    document.body,
  );
}
