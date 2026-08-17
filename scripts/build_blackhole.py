#!/usr/bin/env python3
"""Precompute the isoradial curves that drive the hero black-hole animation.

Relativistic ray tracing around a Schwarzschild black hole, following
Luminet (1979). Everything is expressed in units of the Schwarzschild
radius r_s = 1, so the ISCO sits at r = 3 and the shadow at b = sqrt(27)/2.

The physics is the one from the JAX notebook this was ported from; only the
backend differs (NumPy, so the site build needs no extra dependency). A
photon parametrised by u = r_s / r obeys

    d^2u / dtheta^2 = 3/2 u^2 - u,

integrated with RK4 from the observer (u = 0, du/dtheta = 1/b) up to the
angle theta at which the ray crosses the disk plane.

Geometry conventions
--------------------
`inclination` is the elevation of the observer above the disk plane, so
i = 0 is edge-on and i = pi/2 is face-on. With the observer along
o = (cos i, 0, sin i) and a disk point at azimuth phi, the image-plane
coordinates are

    X = r sin(phi)              (horizontal, positive to the right)
    Y = -r sin(i) cos(phi)      (vertical, positive up)

so alpha = atan2(Y, X), and the angle swept by the photon satisfies
cos(theta_d) = cos(i) cos(phi) -- which is exactly the notebook's

    cos(theta_d) = -sin(alpha) cos(i) / sqrt(1 - cos^2(alpha) cos^2(i)).

Because light bending is planar, the *image angle* alpha is fixed by flat
projection; lensing only moves the image point radially. That is what makes
the precomputed b(r, alpha) tables enough to place a particle: the disk
azimuth gives alpha, the table gives b.

The ray crosses the disk plane again half a turn later, at theta_d + pi and
azimuth phi + pi: that second crossing is the secondary ("ghost") image.

Outputs, both into public/data/:

  blackhole-disk.webp   the disk as the observer sees it, ray-traced one ray
                        per pixel, so the browser only blits a texture;
  blackhole-isoradials  a JSON table of b(r, alpha) for the direct image, on
      .json             a grid uniform in alpha and in sqrt(r) so the
                        front-end can index it without shipping the
                        abscissae. This is what places the moving motes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

B_C = np.sqrt(27.0) / 2.0  # critical impact parameter = apparent shadow radius
R_ISCO = 3.0  # innermost stable circular orbit, in r_s
R_PHOTON = 1.5  # photon sphere, in r_s


# --------------------------------------------------------------------------
# photon trajectories
# --------------------------------------------------------------------------
def photon_orbits(b, theta_max, n_out, substeps):
    """Integrate u(theta) for every impact parameter in `b`.

    Returns (theta, u) with u of shape (n_out, b.size). A photon is dropped
    (NaN from then on) once it crosses the horizon (u >= 1) or escapes back
    to infinity (u <= 0); both are irreversible, so the mask only grows.
    """
    theta = np.linspace(0.0, theta_max, n_out)
    h = (theta[1] - theta[0]) / substeps

    def deriv(s):
        return np.stack((s[1], 1.5 * s[0] ** 2 - s[0]))

    state = np.stack((np.zeros_like(b), 1.0 / b))
    alive = np.ones(b.size, dtype=bool)
    # Parking spot for dead photons: keeps a diverging u from overflowing and
    # poisoning the vectorised step of the ones still in flight.
    parked = np.stack((np.full_like(b, 0.5), np.zeros_like(b)))

    u = np.empty((n_out, b.size))
    u[0] = state[0]

    for k in range(1, n_out):
        for _ in range(substeps):
            k1 = deriv(state)
            k2 = deriv(state + 0.5 * h * k1)
            k3 = deriv(state + 0.5 * h * k2)
            k4 = deriv(state + h * k3)
            state = state + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
            alive &= (state[0] > 0.0) & (state[0] < 1.0)
            state = np.where(alive, state, parked)
        u[k] = np.where(alive, state[0], np.nan)

    return theta, u


def theta_emission(alpha, inclination):
    """Angle swept between the observer and the first disk crossing."""
    ci = np.cos(inclination)
    denom = np.sqrt(np.maximum(1.0 - np.cos(alpha) ** 2 * ci**2, 1e-12))
    return np.arccos(np.clip(-np.sin(alpha) * ci / denom, -1.0, 1.0))


def invert_to_b(radii, r_of_b, b_grid):
    """Read the isoradial off one r(b) curve: b such that r(b) = radii.

    r(b) is increasing wherever the ray survives, so we keep the strictly
    increasing run and interpolate. Radii the curve never reaches get 0,
    the sentinel for "no image here".
    """
    ok = np.isfinite(r_of_b) & (r_of_b > 0.0)
    if ok.sum() < 2:
        return np.zeros_like(radii)

    r, b = r_of_b[ok], b_grid[ok]
    keep = r >= np.maximum.accumulate(r)  # drop any non-monotone excursion
    r, b = r[keep], b[keep]
    r, first = np.unique(r, return_index=True)
    b = b[first]
    if r.size < 2:
        return np.zeros_like(radii)

    out = np.interp(radii, r, b, left=0.0, right=0.0)
    return np.where((radii >= r[0]) & (radii <= r[-1]), out, 0.0)


def impact_grid(n_b, r_out):
    """The impact parameters the orbits are integrated on.

    Rays that reach the disk cluster just outside b_c (they are the ones bent
    by more than pi), so sample that side logarithmically.
    """
    n_inside = n_b // 4
    return np.concatenate(
        (
            np.linspace(1e-3, B_C, n_inside, endpoint=False),
            B_C + np.logspace(-9.0, np.log10(4.0 * r_out), n_b - n_inside),
        )
    )


def build_tables(inclination, r_in, r_out, n_radii, n_alpha, theta, u, b_grid):
    """b(r, alpha) for the direct image, flattened row-major.

    The secondary crossing at theta_d + pi is not tabulated: it is baked into
    the texture by render_disk, and the motes ride the direct image alone.
    """
    # Uniform in sqrt(r): more resolution where the disk is bright and the
    # lensing is strong, and still a closed-form index on the JS side.
    radii = np.linspace(np.sqrt(r_in), np.sqrt(r_out), n_radii) ** 2
    alpha = np.linspace(-np.pi, np.pi, n_alpha, endpoint=False)

    theta_d = theta_emission(alpha, inclination)
    primary = np.zeros((n_radii, n_alpha))

    for j in range(n_alpha):
        # u is sampled on a fine theta grid; linear interpolation between
        # neighbours is far below the RK4 error.
        pos = theta_d[j] / (theta[1] - theta[0])
        lo = int(np.floor(pos))
        w = pos - lo
        u_th = (1.0 - w) * u[lo] + w * u[lo + 1]
        with np.errstate(divide="ignore", invalid="ignore"):
            primary[:, j] = invert_to_b(radii, 1.0 / u_th, b_grid)

    return radii, alpha, primary


# --------------------------------------------------------------------------
# radiative quantities (baked into the texture; the front-end recomputes them)
# --------------------------------------------------------------------------
def page_thorne_flux(x):
    """Steady thin-disk emitted flux, zero at the ISCO, peaking near x = 4.4."""
    sx = np.sqrt(x)
    return (
        x ** (-2.5)
        / (x - 1.5)
        * (
            sx
            - np.sqrt(3.0)
            + np.sqrt(3.0 / 8.0)
            * np.log(
                (np.sqrt(2.0) - 1.0)
                / (np.sqrt(2.0) + 1.0)
                * (sx + np.sqrt(1.5))
                / (sx - np.sqrt(1.5))
            )
        )
    )


def one_plus_z(x, b, alpha, inclination):
    """Combined gravitational + Doppler shift for a circular Keplerian orbit."""
    return (
        1.0 + (1.5 / x) ** 1.5 * (b / B_C) * np.cos(inclination) * np.cos(alpha)
    ) / np.sqrt(1.0 - 1.5 / x)


# --------------------------------------------------------------------------
# the disk image itself
# --------------------------------------------------------------------------
# Site accent ramp, coldest to hottest. No page-ground stop at the bottom:
# the dimming rides on the alpha channel instead, so the faint reaches of the
# disk let the site starfield through rather than stamping a dark field on it.
RAMP = np.array(
    [
        [140, 47, 26],  # --deep
        [212, 68, 31],  # --ember
        [239, 125, 46],  # --flare
        [232, 180, 92],  # --gold
        [243, 210, 154],  # --gold-soft
        [255, 246, 232],
    ]
)

RING_RGB = np.array([255, 232, 200], dtype=float)


def _over(top_rgb, top_a, bot_rgb, bot_a):
    """Straight-alpha source-over of one layer on another."""
    a = top_a + bot_a * (1.0 - top_a)
    safe = np.maximum(a, 1e-6)[..., None]
    rgb = (
        top_rgb * top_a[..., None] + bot_rgb * (bot_a * (1.0 - top_a))[..., None]
    ) / safe
    return np.where(a[..., None] > 0, rgb, 0.0), a


def _bilinear_u(u, theta, b_grid, th, b):
    """u sampled at arbitrary (theta, b), NaN wherever the photon did not survive."""
    dt = theta[1] - theta[0]
    ti = np.clip(th / dt, 0.0, len(theta) - 1.001)
    t0 = ti.astype(np.int32)
    tw = ti - t0

    bi = np.clip(np.searchsorted(b_grid, b) - 1, 0, len(b_grid) - 2)
    bw = np.clip((b - b_grid[bi]) / (b_grid[bi + 1] - b_grid[bi]), 0.0, 1.0)

    lo = (1 - bw) * u[t0, bi] + bw * u[t0, bi + 1]
    hi = (1 - bw) * u[t0 + 1, bi] + bw * u[t0 + 1, bi + 1]
    return (1 - tw) * lo + tw * hi


def render_disk(path, inclination, r_in, r_out, box, width, gamma, level, rim,
                theta, u, b_grid, quality=90, alpha_quality=90, alpha_gamma=0.6):
    """Ray-trace the disk to an RGBA image, one ray per pixel.

    This is the notebook's final figure, rendered offline: for every pixel the
    ray is followed to its first crossing of the disk plane, and to the second
    one where the first misses. Doing it here rather than in the browser is
    what keeps the page free of the seams a vector reconstruction leaves, and
    leaves the client with a single texture to blit.
    """
    from PIL import Image

    x0, x1, y0, y1 = box
    height = int(round(width * (y1 - y0) / (x1 - x0)))
    # Pixel centres, image Y up.
    xs = x0 + (x1 - x0) * (np.arange(width) + 0.5) / width
    ys = y1 - (y1 - y0) * (np.arange(height) + 0.5) / height
    X, Y = np.meshgrid(xs, ys)
    b = np.hypot(X, Y)
    alpha = np.arctan2(Y, X)

    theta_d = theta_emission(alpha, inclination)

    def crossing(shift):
        with np.errstate(divide="ignore", invalid="ignore"):
            r = 1.0 / _bilinear_u(u, theta, b_grid, theta_d + shift, b)
        return np.where((r >= r_in) & (r <= r_out), r, np.nan)

    # First crossing wins; the disk is opaque, so the second only shows where
    # the first missed it.
    r1 = crossing(0.0)
    r2 = crossing(np.pi)
    hit1 = np.isfinite(r1)
    r = np.where(hit1, r1, r2)
    hit = np.isfinite(r)
    rr = np.where(hit, r, r_out)

    with np.errstate(divide="ignore", invalid="ignore"):
        q = (np.sqrt(rr) - np.sqrt(r_in)) / (np.sqrt(r_out) - np.sqrt(r_in))
        taper = np.clip((1.0 - q) / rim, 0.0, 1.0)
        taper = taper * taper * (3.0 - 2.0 * taper)
        obs = taper * page_thorne_flux(rr) / one_plus_z(rr, b, alpha, inclination) ** 4
    obs = np.where(hit, obs, 0.0)

    value = np.clip(obs / np.nanmax(obs), 0.0, 1.0) ** gamma
    idx = value * (len(RAMP) - 1)
    i0 = np.clip(idx.astype(np.int32), 0, len(RAMP) - 2)
    w = (idx - i0)[..., None]
    rgb = RAMP[i0] * (1 - w) + RAMP[i0 + 1] * w

    # The surface carries its dimming as transparency rather than as a blend
    # towards the page ground, so the faint reaches of the disk let the site
    # starfield through instead of stamping a disk-shaped hole in it.
    #
    # The exponent matters: alpha straight from the tone-mapped flux would
    # apply that mapping twice (once in the colour, once in the coverage) and
    # wash the whole disk out. Pulling it back towards linear keeps the body
    # of the disk as bright as it was, and only the tail fades to nothing.
    a_disk = np.where(hit, np.clip(value**alpha_gamma * level, 0.0, 1.0), 0.0)

    # Higher-order images pile up just outside the shadow; one soft rim stands
    # in for the whole infinite sequence. They sit behind the disk, so the near
    # side -- the part of the direct image that crosses in front of the hole --
    # cuts the rim off at the bottom, exactly as it cuts off everything else.
    ring = np.exp(-(((b - B_C * 1.03) / (B_C * 0.06)) ** 2))
    a_ring = np.where((b > B_C) & ~hit1, ring, 0.0) * 0.85
    rgb, a = _over(RING_RGB, a_ring, rgb, a_disk)

    # The shadow underneath stays fully opaque: the hole really does block the
    # sky, so no star may show through it.
    rgb, a = _over(rgb, a, np.zeros(3), (b < B_C).astype(float))

    # A dither of about one level: the surface is dim, so without it the
    # smooth gradients quantise into visible contour rings.
    # Only the colour: dithering alpha as well tripled the file for no
    # visible gain, since libwebp's own alpha coding already breaks up the
    # steps and the colour noise carries through the product.
    rng = np.random.default_rng(0)
    rgb = np.clip(rgb + rng.uniform(-0.6, 0.6, rgb.shape), 0, 255)
    a = np.clip(a * 255.0, 0, 255)

    out = np.dstack((rgb, a[..., None])).astype(np.uint8)
    img = Image.fromarray(out, "RGBA")
    if path.suffix == ".webp":
        # Lossy WebP with alpha: the dither noise makes this incompressible as
        # PNG (half a megabyte), and the disk is a smooth glow where a high
        # quality setting is visually indistinguishable at a fifth the weight.
        # The alpha channel now carries the disk's dimming, and libwebp
        # encodes alpha losslessly by default -- which the dither makes
        # incompressible. Let it be lossy too; it is a soft glow either way.
        img.save(path, quality=quality, alpha_quality=alpha_quality, method=6)
    else:
        img.save(path, optimize=True)
    print(f"{path.name}: {path.stat().st_size / 1024:.0f} kB, {width}x{height}")
    return width, height


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inclination", type=float, default=0.25,
                   help="observer elevation above the disk plane, in radians "
                        "(0 = edge-on, pi/2 = face-on)")
    p.add_argument("--r-in", type=float, default=R_ISCO)
    p.add_argument("--r-out", type=float, default=18.0)
    p.add_argument("--n-radii", type=int, default=22)
    p.add_argument("--n-alpha", type=int, default=240)
    p.add_argument("--n-b", type=int, default=2400)
    p.add_argument("--n-theta", type=int, default=1800)
    p.add_argument("--substeps", type=int, default=6)
    # Served as a static asset rather than bundled: the hero paints its
    # starfield immediately and the disk appears as soon as the fetch lands.
    p.add_argument("--out", type=Path,
                   default=Path(__file__).resolve().parents[1]
                   / "public/data/blackhole-isoradials.json")
    p.add_argument("--image-name", default="blackhole-disk.webp")
    p.add_argument("--image-quality", type=int, default=92)
    p.add_argument("--alpha-quality", type=int, default=95)
    p.add_argument("--alpha-gamma", type=float, default=0.6)
    p.add_argument("--image-width", type=int, default=1500,
                   help="width in pixels of the pre-rendered disk texture")
    p.add_argument("--gamma", type=float, default=1.35)
    p.add_argument("--level", type=float, default=0.8,
                   help="peak opacity of the disk surface, leaving the moving "
                        "motes as the brightest thing on screen")
    p.add_argument("--rim", type=float, default=0.24)
    args = p.parse_args()

    # The tables and the texture must describe the same geometry, so both read
    # one integration: theta_d spans [i, pi - i], and render_disk also needs
    # the crossing half a turn later, so 2 pi covers both.
    b_grid = impact_grid(args.n_b, args.r_out)
    theta, u = photon_orbits(b_grid, 2.0 * np.pi, args.n_theta, args.substeps)

    radii, alpha, primary = build_tables(
        args.inclination, args.r_in, args.r_out, args.n_radii,
        args.n_alpha, theta, u, b_grid,
    )

    # The texture spans the full extent of the direct image, with a little
    # margin so the faded rim is not clipped.
    aa = alpha[None, :]
    xs = primary * np.cos(aa)
    ys = primary * np.sin(aa)
    pad = 1.04
    box = (
        float(-np.abs(xs).max() * pad), float(np.abs(xs).max() * pad),
        float(ys.min() * pad), float(ys.max() * pad),
    )

    image_path = args.out.parent / args.image_name
    args.out.parent.mkdir(parents=True, exist_ok=True)
    iw, ih = render_disk(
        image_path, args.inclination, args.r_in, args.r_out, box,
        args.image_width, args.gamma, args.level, args.rim,
        theta, u, b_grid, args.image_quality,
        args.alpha_quality, args.alpha_gamma,
    )

    payload = {
        "_": "generated by scripts/build_blackhole.py -- do not edit",
        "inclination": round(args.inclination, 6),
        "shadowB": round(float(B_C), 6),
        "rIn": round(float(radii[0]), 6),
        "rOut": round(float(radii[-1]), 6),
        # radii are uniform in sqrt(r); alpha is uniform over [-pi, pi).
        "nRadii": int(args.n_radii),
        "nAlpha": int(args.n_alpha),
        # Pre-rendered disk: the box it covers, in r_s, image Y pointing up.
        "image": {
            "file": image_path.name,
            "x0": round(box[0], 4), "x1": round(box[1], 4),
            "y0": round(box[2], 4), "y1": round(box[3], 4),
            "w": iw, "h": ih,
        },
        # b in units of r_s, 0 meaning "this radius has no image at this angle".
        # Only the direct image is shipped: the secondary one is baked into the
        # texture, and the motes are placed on the direct image alone.
        "primary": [round(float(v), 3) for v in primary.ravel()],
    }

    args.out.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
    size = args.out.stat().st_size
    print(f"{args.out} ({size / 1024:.1f} kB)")
    print(f"  inclination {args.inclination:.3f} rad "
          f"({np.degrees(args.inclination):.1f} deg above the disk plane)")
    print(f"  radii  {radii[0]:.2f} -> {radii[-1]:.2f} r_s ({args.n_radii} values)")
    print(f"  primary b in [{primary[primary > 0].min():.3f}, "
          f"{primary.max():.3f}] r_s  (shadow at {B_C:.3f})")


if __name__ == "__main__":
    main()
