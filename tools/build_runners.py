"""Compact data/splits-<race>.json into web/runners.json for the viewer.

Usage: python tools/build_runners.py [--race 20551]

Each runner becomes {bib, name, sex, age, splits: [[arc_m, seconds_of_day], ...]}
using the mat arc lengths in web/course.json.  ChipStart is the start mat;
GunStart is dropped.  Runners with fewer than two usable splits are skipped.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def seconds_of_day(hms: str) -> int:
    parts = [int(p) for p in hms.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--race", default="20551")
    args = ap.parse_args()
    course = json.loads((ROOT / "web" / "course.json").read_text())
    mats = dict(course["mats"])
    mats["ChipStart"] = mats["Start"]
    data = json.loads((ROOT / "data" / f"splits-{args.race}.json").read_text())

    runners = []
    skipped = 0
    for r in data["runners"]:
        splits = []
        for s in r["splits"]:
            if s["location"] not in mats:
                continue
            splits.append([mats[s["location"]], seconds_of_day(s["time_of_day"])])
        # keep arc and time strictly increasing; a bad read is dropped rather than making a runner go backwards
        clean: list[list[float]] = []
        for arc, t in splits:
            if clean and (arc <= clean[-1][0] or t <= clean[-1][1]):
                continue
            clean.append([round(arc), t])
        if len(clean) < 2:
            skipped += 1
            continue
        runners.append({"bib": r["bib"], "name": r["name"], "sex": r["sex"], "age": r["age"],
                        "city": r["city"], "state": r["state"], "time": r["time"], "splits": clean})

    first = min(r["splits"][0][1] for r in runners)
    last = max(r["splits"][-1][1] for r in runners)
    out = {"race": data["race"], "name": course["name"], "t_start": first, "t_end": last, "runners": runners}
    (ROOT / "web" / "runners.json").write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote web/runners.json: {len(runners)} runners, {skipped} skipped, "
          f"clock {first // 3600}:{first % 3600 // 60:02d} to {last // 3600}:{last % 3600 // 60:02d}", file=sys.stderr)


if __name__ == "__main__":
    main()
