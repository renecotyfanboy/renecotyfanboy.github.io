import { SITE } from "../consts";

const dateFmt = new Intl.DateTimeFormat(SITE.locale, {
  day: "numeric",
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});

export function formatDate(date: Date): string {
  return dateFmt.format(date);
}

/**
 * Minutes at ~200 wpm, floored at 1. A hint, not a promise.
 *
 * Fenced code and raw HTML are removed first. Counting them made notebook
 * posts — the ones with the most code — read as roughly three times longer
 * than they are: the published sample post measured 1161 tokens (6 min)
 * against 447 words of actual prose (2 min).
 */
export function readingTime(body: string | undefined): number {
  const prose = (body ?? "")
    .replace(/^\s*(```|~~~)[\s\S]*?^\s*\1\s*$/gm, " ") // fenced code blocks
    .replace(/<[^>]+>/g, " ") // raw HTML (chart iframes, figures)
    .replace(/`[^`\n]*`/g, " "); // inline code

  const words = prose.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(words / 200));
}
