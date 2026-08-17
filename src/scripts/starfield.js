/* Procedural starfield behind the whole page.

   Painted once and then left alone: the canvas is fixed to the viewport, so
   scrolling costs nothing and there is no animation loop at all. Positions
   are held in normalised coordinates, so a resize re-projects the same sky
   rather than dealing a new one under the reader. */

const DENSITY = 1 / 14000; // stars per square CSS pixel
const MAX = 220;

/* Ignore the small height changes a mobile URL bar produces: repainting the
   sky every time it slides would be wasted work. */
const SETTLE = 64;

export function initStarfield(canvas) {
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    canvas.remove();
    return;
  }

  let stars = [];
  let lastW = 0;
  let lastH = 0;

  const target = (area) => Math.min(MAX, Math.round(area * DENSITY));

  function seed(count) {
    stars = [];
    for (let i = 0; i < count; i++) {
      stars.push({
        x: Math.random(),
        y: Math.random(),
        r: 0.3 + Math.random() * 0.9,
        // Faint on purpose: this sits under body copy on every page.
        a: 0.1 + Math.random() * 0.42,
        warm: Math.random() < 0.15,
      });
    }
  }

  function paint() {
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    if (w < 1 || h < 1) return;

    const want = target(w * h);
    // Re-deal only when the viewport has changed enough that the old count
    // would read as the wrong density.
    if (!stars.length || Math.abs(want - stars.length) > 0.3 * want) seed(want);

    const dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    for (const s of stars) {
      ctx.fillStyle = s.warm
        ? `rgba(255,222,184,${s.a})`
        : `rgba(255,255,255,${s.a})`;
      ctx.beginPath();
      ctx.arc(s.x * w, s.y * h, s.r, 0, Math.PI * 2);
      ctx.fill();
    }

    lastW = w;
    lastH = h;
  }

  let rt;
  const ro = new ResizeObserver(() => {
    clearTimeout(rt);
    rt = setTimeout(() => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      if (w === lastW && Math.abs(h - lastH) < SETTLE) return;
      paint();
    }, 150);
  });
  ro.observe(canvas);

  paint();
}
