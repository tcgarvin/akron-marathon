# Akron Marathon replay

Interactive animation of the Akron Marathon: every bib moving around the
course, driven by chip split times, with a time slider and a "find my bib"
highlight.

**Live:** https://www.tcgarvin.com/vibe/akron-marathon/

The race results aren't in this repo. The live copy has runners' names and
ages removed; relay team names stay.

## How it works (plan)

1. **Course line** — a GPX/GeoJSON of the route, resampled to a polyline with
   cumulative distance so any distance-along-course maps to a lat/lon.
2. **Timing mats** — each mat is a known distance along the course
   (start, 5K, 10K, half, 30K, 35K, finish or whatever Akron publishes).
3. **Chip splits** — per bib, the clock time at each mat. Position at time
   `t` is the linear interpolation of distance between the two mats that
   bracket `t`. Missing splits are skipped (interpolate across the gap).
   Before the start mat and after the finish mat the runner is parked.
   Impossible reads (backwards in time, or a segment far faster than the
   runner) are dropped by the builder; docs/DATA.md explains the rule.
4. **Viewer** — a static page: the two course lines on a canvas, one dot
   per bib coloured by race, a race-clock slider, play / pause / speed, race
   filter chips, and a bib search that highlights one runner and shows their
   splits. Drag to pan, wheel to zoom, double-click to refit.

## Layout

    data/       course KML (race results are kept out of git)
    tools/      Python: build the course and the compact runner JSON
    web/        the static viewer

## Data sources

- **Splits**: the race's official chip results, with time of day at each
  timing mat.
- **Course**: the organiser's Google My Maps, exported as KML
  (`data/15Dqm...kml`, marathon; `data/1rTa...kml`, half). One line plus
  Start, Finish, mile and 5k marker points.

## Pipeline

    python tools/build_course.py                  # -> web/courses.json (marathon and half)
    python tools/build_runners.py [--report]      # -> web/runners.json (all races, tagged, bad reads cleaned)
          [--public PATH]                         # also a copy without runners' names or ages, for publishing
    (cd web && python -m http.server 8787)        # http://localhost:8787/?bib=2&t=30600

`t` in the URL is seconds of day. Stdlib only, no dependencies. The viewer is
a single canvas page with no map tiles, so it runs anywhere static files do,
including as a claude.ai artifact (`web/` published as page plus two files).

## Status

2026-09-26: built during the race. v2 has race, sex and division filters,
search by bib, name or team, overall and division placings computed from the
loaded field, a linear course strip, and a phone layout. Bad chip reads are
cleaned by the builder (`python -m pytest tools/tests` covers the rule).
