"""Compact every data/splits-<race>.json into web/runners.json for the viewer.

Usage: python tools/build_runners.py [--only relay,half,marathon]

Each runner becomes {race, course, bib, name, sex, age, division, splits: [[arc_m, seconds_of_day], ...]}
using the mat arc lengths of their course in web/courses.json.  ChipStart is the start mat;
GunStart is dropped.

Bad chip reads are removed before the runner is written (see clean_reads): a read
is bad when it puts the runner backwards in time, or makes a segment faster than
any human (under MIN_PACE min/mile) or far faster than the runner's own median
segment (under FAST_RATIO of it). The read whose removal leaves the fewest
problems goes; a runner who needs more than MAX_DROPS removals, loses their
finish read, or is listed in data/exclude.json is left out. Every drop is printed,
and --report writes them to data/cleaning.json.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
METRES_PER_MILE = 1609.344
# nobody runs a segment under this pace (min/mile); the fastest real one is the
# half's 12.9M-to-finish sprint at about 3.7
MIN_PACE = 3.0
# a segment under this fraction of the runner's median pace is a bad read
# (real fields bottom out near 0.4; the mat-to-mat bad reads sit under 0.25)
FAST_RATIO = 0.3
# a runner needing more removals than this has data we cannot trust
MAX_DROPS = 2
# MTEC race id -> (race label, course id)
RACES = {
    "20551": ("marathon", "marathon"),
    "20552": ("half", "half"),
    "20554": ("relay", "marathon"),
}


Read = tuple[str, float, int]  # (mat name, arc metres, seconds of day)


def violations(reads: list[Read]) -> list[int]:
    """Indexes i of segments reads[i] -> reads[i+1] that no runner could produce."""
    paces = []
    for (_, arc0, t0), (_, arc1, t1) in zip(reads, reads[1:]):
        miles = (arc1 - arc0) / METRES_PER_MILE
        paces.append((t1 - t0) / 60 / miles if t1 > t0 else -1.0)
    median = statistics.median(p for p in paces if p > 0) if any(p > 0 for p in paces) else 0
    return [
        i
        for i, pace in enumerate(paces)
        if pace <= 0 or pace < MIN_PACE or pace < FAST_RATIO * median
    ]


def clean_reads(reads: list[Read]) -> tuple[list[Read], list[str]]:
    """Drop bad chip reads one at a time until every segment is plausible.

    `reads` are in mat order along the course. For the first bad segment, whichever
    of its two reads leaves fewer bad segments is dropped (ties go to the one that
    leaves the slowest remaining segment fastest, so a read that would strand the
    runner for an hour loses). Returns the kept reads and one note per drop."""
    reads = list(reads)
    notes: list[str] = []
    while len(reads) >= 2:
        bad = violations(reads)
        if not bad:
            break
        i = bad[0]
        options = []
        for drop in (i, i + 1):
            rest = reads[:drop] + reads[drop + 1 :]
            slowest = max(
                (
                    (t1 - t0) / max(arc1 - arc0, 1)
                    for (_, arc0, t0), (_, arc1, t1) in zip(rest, rest[1:])
                ),
                default=0,
            )
            options.append((len(violations(rest)), slowest, drop))
        _, _, drop = min(options)
        name, _, t = reads[drop]
        notes.append(f"dropped {name} at {hms(t)}")
        del reads[drop]
    return reads, notes


def hms(sec: int) -> str:
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def seconds_of_day(hms: str) -> int:
    parts = [int(p) for p in hms.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--only", default="", help="comma-separated race labels to include; default all"
    )
    ap.add_argument(
        "--report",
        action="store_true",
        help="also write every cleaning decision to data/cleaning.json",
    )
    ap.add_argument(
        "--public",
        type=Path,
        help="also write a copy for publishing to this path, without runners' names or ages",
    )
    args = ap.parse_args()
    only = {r.strip() for r in args.only.split(",") if r.strip()}
    courses = json.loads((ROOT / "web" / "courses.json").read_text())
    exclude_path = ROOT / "data" / "exclude.json"
    excluded = (
        {(e["race"], e["bib"]): e["reason"] for e in json.loads(exclude_path.read_text())}
        if exclude_path.exists()
        else {}
    )
    runners: list[dict] = []
    report: list[dict] = []
    for race_id, (race, course_id) in RACES.items():
        if only and race not in only:
            continue
        path = ROOT / "data" / f"splits-{race_id}.json"
        if not path.exists():
            print(f"no {path.name}, skipping {race}", file=sys.stderr)
            continue
        mats = dict(courses[course_id]["mats"])
        mats["ChipStart"] = mats["Start"]
        for r in json.loads(path.read_text())["runners"]:
            reason = excluded.get((race, r["bib"]))
            if reason:
                note(report, race, r, [], f"excluded: {reason}")
                continue
            compact(r, race, course_id, mats, runners, report)
    write(runners, courses, args.public)
    if args.report:
        (ROOT / "data" / "cleaning.json").write_text(json.dumps(report, indent=1))


def note(report: list, race: str, r: dict, drops: list[str], outcome: str) -> None:
    report.append(
        {"race": race, "bib": r["bib"], "name": r["name"], "drops": drops, "outcome": outcome}
    )
    print(f"{race} bib {r['bib']} ({r['name']}): {'; '.join(drops + [outcome])}", file=sys.stderr)


def compact(
    r: dict, race: str, course_id: str, mats: dict, runners: list, report: list
) -> None:
    """Append one runner with cleaned, strictly increasing (arc, time) splits, or skip them."""
    course_length = mats["Finish"]
    reads: list[Read] = []
    for s in r["splits"]:
        if s["location"] not in mats:
            continue
        arc = mats[s["location"]]
        if reads and arc <= reads[-1][1]:
            continue  # the same mat listed twice
        reads.append((s["location"], arc, seconds_of_day(s["time_of_day"])))
    had_finish = any(name == "Finish" for name, _, _ in reads)
    reads, drops = clean_reads(reads)
    clean = [[round(arc), t] for _, arc, t in reads]
    if len(clean) < 2:
        note(report, race, r, drops, "skipped: fewer than two chip reads")
        return
    if len(drops) > MAX_DROPS:
        note(report, race, r, drops, f"skipped: more than {MAX_DROPS} bad reads")
        return
    if had_finish and reads[-1][0] != "Finish":
        note(report, race, r, drops, "skipped: the finish read was the bad one")
        return
    if drops:
        note(report, race, r, drops, "kept")
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
            "finished": clean[-1][0] >= course_length - 1,
            "splits": clean,
        }
    )


def rank(runners: list) -> None:
    """Overall and division place among finishers of the same race, by elapsed chip time.

    Runners without a finish read get no place."""
    by_group: dict[tuple, list] = {}
    for r in runners:
        if not r["finished"]:
            continue
        by_group.setdefault((r["race"],), []).append(r)
        by_group.setdefault((r["race"], r["division"]), []).append(r)
    for key, group in by_group.items():
        group.sort(key=lambda r: r["splits"][-1][1] - r["splits"][0][1])
        field = "place" if len(key) == 1 else "div_place"
        for i, r in enumerate(group, 1):
            r[field] = i
            r[field.replace("place", "total")] = len(group)


def redact(runner: dict) -> dict:
    """A runner without their name or age. Relay names are team names, so those stay."""
    public = {k: v for k, v in runner.items() if k != "age"}
    if runner["race"] != "relay":
        public["name"] = ""
    return public


def write(runners: list, courses: dict, public_path: Path | None) -> None:
    rank(runners)
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
    if public_path:
        public = {**out, "names_removed": True, "runners": [redact(r) for r in runners]}
        public_path.write_text(json.dumps(public, separators=(",", ":")))
        print(f"wrote {public_path} without names or ages", file=sys.stderr)
    print(
        f"wrote web/runners.json: {counts}, "
        f"clock {first // 3600}:{first % 3600 // 60:02d} to {last // 3600}:{last % 3600 // 60:02d}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
