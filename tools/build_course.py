"""Turn the race's Google My Maps KML into web/course.json.

Usage: python tools/build_course.py [data/<map>.kml]

The KML has one "Course" line plus Start, Finish, mile and 5k marker points.
Each marker is projected onto the line (monotonically, so out-and-back
stretches snap to the right pass) to get its arc length, which calibrates
nominal race miles against metres along the drawn line.  Timing mats are
placed by their nominal mile through that calibration.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KML = ROOT / "data" / "15Dqm-v7XlbEsAdfs61cgFL0dXrNvZLg.kml"
# MTEC split names and the nominal mile of each mat.
MATS = {"Start": 0.0, "3.1M": 3.1, "7.2M": 7.2, "10.7M": 10.7, "12.7M": 12.7, "13.1M": 13.1,
        "17.3M": 17.3, "21.7M": 21.7, "26M": 26.0, "Finish": 26.2}
MILE_M = 1609.344


def placemarks(kml: str) -> list[tuple[str, str, list[tuple[float, float]]]]:
    out = []
    for pm in re.findall(r"<Placemark>(.*?)</Placemark>", kml, flags=re.S):
        name = re.search(r"<name>([^<]*)</name>", pm)
        kind = "line" if "<LineString>" in pm else "point"
        raw = re.search(r"<coordinates>\s*([^<]*)</coordinates>", pm, flags=re.S).group(1).split()
        coords = [(float(c.split(",")[1]), float(c.split(",")[0])) for c in raw]  # lat, lon
        out.append((name.group(1) if name else "", kind, coords))
    return out


def haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    r = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def local_xy(origin: tuple[float, float]):
    """Flat-earth metres around origin; fine for a city-sized course."""
    k = math.cos(math.radians(origin[0]))
    def f(p):
        return ((p[1] - origin[1]) * 111320.0 * k, (p[0] - origin[0]) * 110540.0)
    return f


def project(xy, line_xy, arcs, min_arc: float) -> tuple[float, float]:
    """Arc length of the closest point on the polyline at or after min_arc, and its distance."""
    best = (math.inf, 0.0)
    for i in range(len(line_xy) - 1):
        if arcs[i + 1] < min_arc:
            continue
        (x1, y1), (x2, y2) = line_xy[i], line_xy[i + 1]
        dx, dy = x2 - x1, y2 - y1
        seg = dx * dx + dy * dy
        t = 0.0 if seg == 0 else max(0.0, min(1.0, ((xy[0] - x1) * dx + (xy[1] - y1) * dy) / seg))
        arc = arcs[i] + t * (arcs[i + 1] - arcs[i])
        if arc < min_arc:
            continue
        d = math.hypot(x1 + t * dx - xy[0], y1 + t * dy - xy[1])
        if d < best[0]:
            best = (d, arc)
    return best[1], best[0]


def interp(x: float, xs: list[float], ys: list[float]) -> float:
    if x <= xs[0]:
        return ys[0]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            f = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + f * (ys[i] - ys[i - 1])
    # extrapolate past the last marker at the last segment's rate
    f = (x - xs[-2]) / (xs[-1] - xs[-2])
    return ys[-2] + f * (ys[-1] - ys[-2])


def main() -> None:
    kml_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_KML
    marks = placemarks(kml_path.read_text())
    line = next(c for n, k, c in marks if k == "line")
    points = {n: c[0] for n, k, c in marks if k == "point"}

    arcs = [0.0]
    for a, b in zip(line, line[1:]):
        arcs.append(arcs[-1] + haversine(a, b))
    to_xy = local_xy(line[0])
    line_xy = [to_xy(p) for p in line]

    # nominal mile -> arc metres, from the drawn mile markers in course order
    calib = [(0.0, 0.0)]
    min_arc = 0.0
    markers = [(f"Mile {m}", float(m)) for m in range(1, 27)]
    for name, mile in markers:
        arc, err = project(to_xy(points[name]), line_xy, arcs, min_arc)
        if err > 60:
            print(f"warning: {name} is {err:.0f} m off the line", file=sys.stderr)
        calib.append((mile, arc))
        min_arc = arc
    calib.append((26.2, arcs[-1]))
    xs, ys = [c[0] for c in calib], [c[1] for c in calib]
    mats = {name: interp(mile, xs, ys) for name, mile in MATS.items()}

    drawn_miles = arcs[-1] / MILE_M
    print(f"line: {len(line)} points, {arcs[-1]:.0f} m ({drawn_miles:.2f} mi drawn)", file=sys.stderr)
    for name, arc in mats.items():
        print(f"  {name:7} {arc:8.0f} m", file=sys.stderr)

    out = {
        "name": "2026 FirstEnergy Akron Marathon",
        "points": [[round(p[0], 6), round(p[1], 6), round(a, 1)] for p, a in zip(line, arcs)],
        "length_m": round(arcs[-1], 1),
        "mats": {k: round(v, 1) for k, v in mats.items()},
        "mile_markers": {m: round(a, 1) for m, a in calib[1:-1]},
        "start": points["Start"],
        "finish": points["Finish"],
    }
    (ROOT / "web" / "course.json").write_text(json.dumps(out))
    print("wrote web/course.json", file=sys.stderr)


if __name__ == "__main__":
    main()
