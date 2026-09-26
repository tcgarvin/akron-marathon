"""Compact every data/splits-<race>.json into web/runners.json for the viewer.

Usage: python tools/build_runners.py

Each runner becomes {race, course, bib, name, sex, age, division, splits: [[arc_m, seconds_of_day], ...]}
using the mat arc lengths of their course in web/courses.json.  ChipStart is the start mat;
GunStart is dropped.  Runners with fewer than two usable splits are skipped.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# MTEC race id -> (race label, course id)
RACES = {
    "20551": ("marathon", "marathon"),
    "20552": ("half", "half"),
    "20554": ("relay", "marathon"),
}


def seconds_of_day(hms: str) -> int:
    parts = [int(p) for p in hms.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def main() -> None:
    courses = json.loads((ROOT / "web" / "courses.json").read_text())
    runners: list[dict] = []
    for race_id, (race, course_id) in RACES.items():
        path = ROOT / "data" / f"splits-{race_id}.json"
        if not path.exists():
            print(f"no {path.name}, skipping {race}", file=sys.stderr)
            continue
        mats = dict(courses[course_id]["mats"])
        mats["ChipStart"] = mats["Start"]
        for r in json.loads(path.read_text())["runners"]:
            compact(r, race, course_id, mats, runners)
    write(runners, courses)


def compact(r: dict, race: str, course_id: str, mats: dict, runners: list) -> None:
    """Append one runner with strictly increasing (arc, time) splits, or skip them."""
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
        print(
            f"skipping {race} bib {r['bib']} ({r['name']}): fewer than two chip reads",
            file=sys.stderr,
        )
        return
    runners.append(
        {
            "race": race,
            "course": course_id,
            "bib": r["bib"],
            "name": r["name"],
            "sex": r["sex"],
            "age": r["age"],
            "division": r.get("division", ""),
            "city": r["city"],
            "state": r["state"],
            "time": r["time"],
            "splits": clean,
        }
    )


def write(runners: list, courses: dict) -> None:
    first = min(r["splits"][0][1] for r in runners)
    last = max(r["splits"][-1][1] for r in runners)
    counts = {
        race: sum(1 for r in runners if r["race"] == race)
        for race in ("marathon", "half", "relay")
    }
    out = {
        "name": "2026 FirstEnergy Akron Marathon, Half Marathon & Team Relay",
        "t_start": first,
        "t_end": last,
        "counts": counts,
        "runners": runners,
    }
    (ROOT / "web" / "runners.json").write_text(json.dumps(out, separators=(",", ":")))
    print(
        f"wrote web/runners.json: {counts}, "
        f"clock {first // 3600}:{first % 3600 // 60:02d} to {last // 3600}:{last % 3600 // 60:02d}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
