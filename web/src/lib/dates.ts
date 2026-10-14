/** Calendar maths on plain YYYY-MM-DD strings, done in UTC so DST never shifts a day. */
const DAY = 86400000;

const ms = (d: string) => Date.parse(d + "T00:00:00Z");
const iso = (t: number) => new Date(t).toISOString().slice(0, 10);

export const shiftDays = (d: string, days: number) => iso(ms(d) + days * DAY);
export const monthStart = (d: string) => d.slice(0, 8) + "01";
export const daysInMonth = (d: string) =>
  new Date(Date.UTC(+d.slice(0, 4), +d.slice(5, 7), 0)).getUTCDate();
/** Monday-first weekday index, 0–6. */
export const weekday = (d: string) => (new Date(ms(d)).getUTCDay() + 6) % 7;
export const formatDay = (d: string) => d.split("-").join("/");

/** Same day-of-month n months away, clamped to the target month's length. */
export function shiftMonths(d: string, n: number) {
  const t = new Date(ms(monthStart(d)));
  t.setUTCMonth(t.getUTCMonth() + n);
  const month = iso(t.getTime());
  const day = Math.min(+d.slice(8, 10), daysInMonth(month));
  return month.slice(0, 8) + String(day).padStart(2, "0");
}

/** Today's date in an IANA time zone, e.g. the advertiser account's zone. */
export function todayIn(timeZone: string) {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}
