/* Accretion disk around a Schwarzschild black hole.

   Nothing here is ray-traced at runtime. `scripts/build_blackhole.py` does
   the relativistic work offline (Luminet 1979) and ships two artefacts:

     - blackhole-disk.webp, the disk image itself, one ray per pixel, so the
       browser only ever blits a texture;
     - blackhole-isoradials.json, a table of b(r, alpha) giving where in the
       image a disk radius r shows up at image angle alpha. That is what
       places the orbiting motes.

   Because light bending is planar in Schwarzschild, the image angle alpha of
   an emitting point is fixed by plain projection; gravity only slides the
   image radially. So a mote orbiting at (r, phi) is placed by reading the
   table: phi gives alpha, the table gives b.

   Everything is in units of the Schwarzschild radius: the ISCO sits at
   r = 3, the shadow at b = sqrt(27)/2.

   Only the motes move, so only they get a canvas -- sized to the disk's
   bounding box, not the hero. The disk is a plain <img> the script merely
   positions, and the starfield behind it belongs to the whole page
   (Starfield.astro). Vanilla, no dependencies, respects
   prefers-reduced-motion, and pauses while the tab is hidden or the hero is
   scrolled out of view. */

const DATA_URL = "/data/blackhole-isoradials.json";

const TAU = Math.PI * 2;
const R_3M = 1.5; // 3M: the photon sphere, and the pole of the disk formula

/* The hole is a fixed-size object: SCALE pixels per Schwarzschild radius,
   whatever the window is doing. Resizing the browser must not inflate it.

   FILL_X and FILL_Y are only the escape hatch for windows too small to hold
   it at that size. They are deliberately generous, because they decide when
   the disk stops being invariant, not how big it is: at the sizes where
   SCALE wins they have no effect at all. The wings they would clip are the
   faintest part of the image anyway, and the hero already hides overflow. */
const SCALE = 20;
const FILL_X = 0.92;
const FILL_Y = 0.8;
const CENTRE_Y = 0.4;

const ORBIT_SPEED = 11.5; // r_s/c per second -- inner ring turns in ~4 s
const INFLOW = 0.02; // radial drift as a fraction of r per radian of orbit

/* Motes are overdense clumps, mapped generously so they read against the
   surface they ride on. */
const MOTE_GAMMA = 0.5;
const MOTE_GAIN = 1.25;
/* Comet tails, in points kept -- one point per frame, so this is also how
   long a tail lingers in seconds at 60 Hz. Randomised per mote so the disk
   does not read as a set of identical dashes. */
const TRAIL_MIN = 40;
const TRAIL_MAX = 96;

/* Site accent ramp, coldest to hottest. */
const RAMP = [
  [140, 47, 26], // --deep
  [212, 68, 31], // --ember
  [239, 125, 46], // --flare
  [232, 180, 92], // --gold
  [243, 210, 154], // --gold-soft
  [255, 246, 232],
];

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);

/* --- radiative quantities ------------------------------------------------ */

const S3 = Math.sqrt(3);
const S32 = Math.sqrt(1.5);
const K38 = Math.sqrt(3 / 8);
const CQ = (Math.SQRT2 - 1) / (Math.SQRT2 + 1);

/** Page-Thorne flux of a steady thin disk. Zero at the ISCO, peaks near 4.4. */
function emittedFlux(r) {
  const s = Math.sqrt(r);
  return (
    (Math.pow(r, -2.5) / (r - R_3M)) *
    (s - S3 + K38 * Math.log((CQ * (s + S32)) / (s - S32)))
  );
}

/** Keplerian angular velocity, in c/r_s (the hole has mass M = r_s / 2). */
const omega = (r) => Math.sqrt(0.5 / (r * r * r));

/** Catmull-Rom through four samples of a uniform grid, `t` in [0, 1]. */
function catmull(p0, p1, p2, p3, t) {
  return (
    0.5 *
    (2 * p1 +
      (p2 - p0) * t +
      (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
      (3 * p1 - 3 * p2 + p3 - p0) * t * t * t)
  );
}

/** Ramp lookup as an "r,g,b" fragment, `t` in [0, 1]. */
function ramp(t) {
  const x = clamp(t, 0, 1) * (RAMP.length - 1);
  const i = Math.min(RAMP.length - 2, Math.floor(x));
  const w = x - i;
  const a = RAMP[i];
  const b = RAMP[i + 1];
  return `${Math.round(a[0] + (b[0] - a[0]) * w)},${Math.round(
    a[1] + (b[1] - a[1]) * w,
  )},${Math.round(a[2] + (b[2] - a[2]) * w)}`;
}

/* --- the precomputed isoradials ------------------------------------------ */

/** Wraps the raw table into the samplers the mote layer needs. */
function makeModel(data) {
  const { nRadii, nAlpha, rIn, rOut, inclination, image } = data;
  const primary = Float32Array.from(data.primary);

  // The radii are laid out uniformly in sqrt(r), the angles uniformly over
  // [-pi, pi), so both indices are closed-form -- no abscissae to ship.
  const q0 = Math.sqrt(rIn);
  const dq = (Math.sqrt(rOut) - q0) / (nRadii - 1);
  const dA = TAU / nAlpha;

  /* Catmull-Rom along alpha (periodic, and the underlying curve is analytic,
     so this is far smoother than the 1.5-degree sampling suggests). */
  function row(k, x) {
    const j = Math.floor(x);
    const p0 = primary[k * nAlpha + ((j - 1 + nAlpha) % nAlpha)];
    const p1 = primary[k * nAlpha + (j % nAlpha)];
    const p2 = primary[k * nAlpha + ((j + 1) % nAlpha)];
    const p3 = primary[k * nAlpha + ((j + 2) % nAlpha)];
    if (p0 <= 0 || p1 <= 0 || p2 <= 0 || p3 <= 0) return 0; // no image here
    return catmull(p0, p1, p2, p3, x - j);
  }

  /** Impact parameter at which radius `r` is seen, at image angle `alpha`.

      Cubic in the radial direction too: interpolating linearly between the
      tabulated radii leaves a slope break on every one of them, and a mote
      crossing one would visibly kink. */
  function bAt(r, alpha) {
    const y = (Math.sqrt(clamp(r, rIn, rOut)) - q0) / dq;
    const k = clamp(Math.floor(y), 0, nRadii - 2);
    let x = (alpha + Math.PI) / dA;
    x -= Math.floor(x / nAlpha) * nAlpha;
    const p0 = row(Math.max(k - 1, 0), x);
    const p1 = row(k, x);
    const p2 = row(k + 1, x);
    const p3 = row(Math.min(k + 2, nRadii - 1), x);
    if (p0 <= 0 || p1 <= 0 || p2 <= 0 || p3 <= 0) return 0;
    return catmull(p0, p1, p2, p3, y - k);
  }

  const sinI = Math.sin(inclination);

  /* Smooth fade of the outermost radii, matching the texture's own rim. */
  const rimTaper = (r) => {
    const q = (Math.sqrt(r) - q0) / (Math.sqrt(rOut) - q0);
    const u = clamp((1 - q) / 0.24, 0, 1);
    return u * u * (3 - 2 * u);
  };

  // Emitted power per unit radius, for drawing mote radii from the disk's own
  // emissivity, plus the peak that normalises their brightness.
  let weightMax = 0;
  let emitMax = 0;
  for (let k = 0; k <= 400; k++) {
    const r = rIn + ((rOut - rIn) * k) / 400;
    weightMax = Math.max(weightMax, r * emittedFlux(r));
    emitMax = Math.max(emitMax, rimTaper(r) * emittedFlux(r));
  }

  return {
    rIn,
    rOut,
    image,
    bAt,

    /** Image angle at which disk azimuth `phi` is seen. */
    imageAngle: (phi) => Math.atan2(-sinI * Math.cos(phi), Math.sin(phi)),

    /* Rest-frame emission only. Deliberately unshifted: the (1+z)^-4 beaming
       is what makes the baked surface asymmetric, and letting it swallow half
       the motes as well costs more than the realism is worth. */
    emitted: (r) => (rimTaper(r) * emittedFlux(r)) / emitMax,

    /** A radius drawn from r * F(r), by rejection. */
    randomRadius() {
      for (let k = 0; k < 64; k++) {
        const r = rIn + Math.random() * (rOut - rIn);
        if (Math.random() * weightMax < r * emittedFlux(r)) return r;
      }
      return rIn + Math.random() * (rOut - rIn);
    },
  };
}

/* --- main ---------------------------------------------------------------- */

export function initBlackHole(root) {
  if (!root) return;

  const disk = root.querySelector('[data-bh="disk"]');
  const fg = root.querySelector('[data-bh="motes"]');
  const ctx = fg && fg.getContext("2d");
  if (!disk || !ctx) {
    root.remove();
    return;
  }

  const reduceMotion = !!(
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );

  let W = 0;
  let H = 0;
  let dpr = 1;
  let scale = 0; // pixels per Schwarzschild radius
  let ox = 0; // hole centre, in the mote canvas's own coordinates
  let oy = 0;

  let model = null;
  let motes = [];
  let rafId = null;
  let last = 0;
  let visible = true;

  const rand = (a, b) => a + Math.random() * (b - a);

  /* --- geometry ---------------------------------------------------------- */

  /** Places the disk box and sizes the mote canvas to it.

      That canvas covers only the box, not the whole hero: motes never leave
      the direct image, and a smaller surface to clear and composite every
      frame is most of why the loop is cheap. */
  function place() {
    if (!model) return;
    const { x0, x1, y0, y1 } = model.image;
    scale = Math.min(
      SCALE,
      (W * FILL_X) / (x1 - x0),
      (H * FILL_Y) / (y1 - y0),
    );

    const cx = W * 0.5;
    const cy = H * CENTRE_Y + 0.5 * (y0 + y1) * scale;
    const box = {
      left: cx + x0 * scale,
      top: cy - y1 * scale,
      w: (x1 - x0) * scale,
      h: (y1 - y0) * scale,
    };
    ox = cx - box.left;
    oy = cy - box.top;

    // The texture covers exactly the same box, so both get the same rect.
    for (const el of [disk, fg]) {
      el.style.left = `${box.left}px`;
      el.style.top = `${box.top}px`;
      el.style.width = `${box.w}px`;
      el.style.height = `${box.h}px`;
    }
    disk.dataset.placed = "";

    fg.width = Math.max(1, Math.round(box.w * dpr));
    fg.height = Math.max(1, Math.round(box.h * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  /* --- motes -------------------------------------------------------------- */

  function spawnMote(m, fresh) {
    m.r = model.randomRadius();
    m.phi = rand(0, TAU);
    m.size = rand(0.55, 1.7);
    m.tail = Math.round(rand(TRAIL_MIN, TRAIL_MAX));
    m.span = rand(7, 16); // seconds before it is recycled
    m.age = fresh ? rand(0, m.span) : 0;
    m.trail = [];
    return m;
  }

  function build() {
    if (!model) return;
    motes = [];
    const count = Math.min(150, Math.round((W * H) / 13000));
    for (let i = 0; i < count; i++) motes.push(spawnMote({}, true));
  }

  /** Fade envelope so recycling a mote never pops. */
  function envelope(m) {
    const u = m.age / m.span;
    return clamp(Math.min(u, 1 - u) * 6, 0, 1);
  }

  function draw() {
    ctx.clearRect(0, 0, fg.width, fg.height);
    if (!model) return;

    ctx.globalCompositeOperation = "lighter";
    ctx.lineCap = "round";

    for (const m of motes) {
      const alpha = model.imageAngle(m.phi);
      const b = model.bAt(m.r, alpha);
      if (b <= 0) continue;

      const tone = Math.pow(model.emitted(m.r), MOTE_GAMMA);
      const a = clamp(tone * MOTE_GAIN, 0, 1) * envelope(m);
      if (a <= 0.004) continue;

      const colour = `rgb(${ramp(tone)})`;
      const tr = m.trail;
      const pts = tr.length / 2;

      if (pts > 1) {
        ctx.strokeStyle = colour;
        for (let k = 1; k < pts; k++) {
          const f = k / pts; // older -> newer
          ctx.globalAlpha = a * f * f * 0.55;
          ctx.lineWidth = Math.max(0.4, m.size * 1.5 * f);
          ctx.beginPath();
          ctx.moveTo(tr[(k - 1) * 2], tr[(k - 1) * 2 + 1]);
          ctx.lineTo(tr[k * 2], tr[k * 2 + 1]);
          ctx.stroke();
        }
      }

      ctx.globalAlpha = a;
      ctx.fillStyle = colour;
      ctx.beginPath();
      ctx.arc(
        ox + b * Math.cos(alpha) * scale,
        oy - b * Math.sin(alpha) * scale,
        m.size,
        0,
        TAU,
      );
      ctx.fill();
    }

    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";
  }

  function step(dt) {
    for (const m of motes) {
      const dphi = omega(m.r) * ORBIT_SPEED * dt;
      m.phi += dphi;
      // A thin disk drifts inward at a small fraction of its orbital speed.
      m.r -= INFLOW * m.r * dphi;
      m.age += dt;
      if (m.age >= m.span || m.r <= model.rIn) {
        spawnMote(m, false);
        continue;
      }
      const alpha = model.imageAngle(m.phi);
      const b = model.bAt(m.r, alpha);
      if (b > 0) {
        m.trail.push(
          ox + b * Math.cos(alpha) * scale,
          oy - b * Math.sin(alpha) * scale,
        );
        if (m.trail.length > m.tail * 2) {
          m.trail.splice(0, m.trail.length - m.tail * 2);
        }
      }
    }
  }

  function loop(now) {
    const dt = last ? Math.min((now - last) / 1000, 0.05) : 0.016;
    last = now;
    step(dt);
    draw();
    rafId = requestAnimationFrame(loop);
  }

  function start() {
    if (!W || !model) return;
    draw(); // paint one frame immediately (rAF is paused on load / hidden tabs)
    if (reduceMotion) return; // static: no loop
    if (rafId == null && visible && !document.hidden) {
      last = 0;
      rafId = requestAnimationFrame(loop);
    }
  }

  function stop() {
    if (rafId != null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
  }

  function resize() {
    const rect = root.getBoundingClientRect();
    if (rect.width < 1 || rect.height < 1) return false;

    dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));
    W = rect.width;
    H = rect.height;

    place();
    build();
    return true;
  }

  let rt;
  const ro = new ResizeObserver(() => {
    clearTimeout(rt);
    rt = setTimeout(() => {
      // Also the path that gets things going when the element has no layout
      // yet at import time; start() is idempotent.
      if (resize()) start();
    }, 150);
  });
  ro.observe(root);

  // Don't burn frames on a hero that has scrolled off screen.
  new IntersectionObserver(
    ([entry]) => {
      visible = entry.isIntersecting;
      if (visible) start();
      else stop();
    },
    { threshold: 0 },
  ).observe(root);

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop();
    else start();
  });

  /* The table carries the box the texture covers, so the image stays hidden
     until it lands. Decoration either way: if the fetch fails the hero simply
     keeps the site starfield. */
  fetch(DATA_URL)
    .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
    .then((data) => {
      model = makeModel(data);
      if (resize()) start();
    })
    .catch(() => {});
}
